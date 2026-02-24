import tarfile
from datetime import timedelta

import yaml
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, F, FloatField, Q, Value, When
from django.db.models.functions import TruncDay
from django.http import FileResponse
from django.urls import reverse
from django.utils import timezone
from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from schema import Optional, SchemaError
from schema import Schema as ManifestSchema

from .auth import UploadTokenAuth
from .models import DownloadEvent, Package, PackageVersion

MANIFEST_SCHEMA = ManifestSchema(
    {
        "name": str,
        "version": str,
        "description": str,
        "author": str,
        Optional("deprecated"): bool,
        Optional("deploy"): {
            Optional("functionSpecs"): [str],
            Optional("workflows"): [str],
            Optional("executors"): [
                {
                    "name": str,
                    "img": str,
                }
            ],
            Optional("setup"): [str],
            Optional("teardown"): [str],
        },
    }
)


class UploadOK(Schema):
    url: str


class DownloadSeries(Schema):
    labels: list[str]
    data: list[int]
    total: int


def parse_package_archive(archive_file):
    archive_file.seek(0)

    try:
        with tarfile.open(fileobj=archive_file, mode="r:gz") as tar:
            file_members = [m for m in tar.getmembers() if m.isfile()]

            # Normalize member paths and do basic safety checks
            member_by_path: dict[str, tarfile.TarInfo] = {}
            for m in file_members:
                name = m.name

                # Reject absolute paths
                if name.startswith("/"):
                    raise HttpError(400, "archive contains invalid paths")

                # Reject path traversal
                parts = [p for p in name.split("/") if p not in ("", ".")]
                if any(p == ".." for p in parts):
                    raise HttpError(400, "archive contains invalid paths")

                key = name.lstrip("./")
                member_by_path[key] = m

            manifest_member = member_by_path.get("package.yaml")
            if manifest_member is None:
                raise HttpError(400, "package.yaml must be at the archive root")

            manifest_f = tar.extractfile(manifest_member)
            if manifest_f is None:
                raise HttpError(400, "could not read package.yaml from the archive")

            manifest_raw = manifest_f.read().decode("utf-8")

            try:
                manifest_data = yaml.safe_load(manifest_raw)
            except yaml.YAMLError as e:
                raise HttpError(400, f"package.yaml is not valid YAML: {e}")

            if not isinstance(manifest_data, dict):
                raise HttpError(400, "package.yaml must contain a mapping/object")

            try:
                manifest_content = MANIFEST_SCHEMA.validate(manifest_data)
            except SchemaError as e:
                raise HttpError(400, f"invalid package.yaml: {e}")

            readme_content = ""
            readme_member = member_by_path.get("readme.md")
            if readme_member is not None:
                readme_f = tar.extractfile(readme_member)
                if readme_f is not None:
                    readme_content = readme_f.read().decode("utf-8", errors="replace")

            return manifest_content, readme_content

    except (tarfile.ReadError, OSError):
        raise HttpError(400, "invalid archive format")


router = Router()


@router.post(
    "/upload",
    url_name="upload-package",
    auth=UploadTokenAuth(max_age=30),
    response=UploadOK,
)
def upload_package(request, archive: UploadedFile = File(...)):
    manifest_data, readme_text = parse_package_archive(archive.file)
    pkg_name = manifest_data["name"]
    version_str = str(manifest_data["version"])

    # since you only allow major.minor.patch:
    new_major, new_minor, new_patch = map(int, version_str.split("."))

    with transaction.atomic():
        package, created = Package.objects.get_or_create(
            name=pkg_name,
            defaults=dict(
                owner=request.auth,
                description=manifest_data["description"],
                author=str(manifest_data["author"]),
                deprecated=bool(manifest_data.get("deprecated", False)),
            ),
        )

        if not created and package.owner_id != request.auth.id:
            raise HttpError(403, "you do not own this package")

        # Lock to serialize uploads per package (prevents race conditions)
        Package.objects.select_for_update().get(pk=package.pk)

        # Reject anything <= latest (prevents 0.4.0 when 0.5.0 exists)
        latest = (
            PackageVersion.objects.filter(package=package)
            .order_by("-major", "-minor", "-patch")
            .first()
        )
        if latest is not None:
            if (new_major, new_minor, new_patch) <= (
                latest.major,
                latest.minor,
                latest.patch,
            ):
                raise HttpError(
                    409,
                    f'cannot upload "{version_str}": latest is "{latest.version}"',
                )

        # IMPORTANT: pass archive in defaults because get_or_create saves immediately
        archive.seek(0)
        try:
            pv, pv_created = PackageVersion.objects.get_or_create(
                package=package,
                version=version_str,
                defaults={
                    "readme": readme_text,
                    "archive": archive,  # <- fixes "archive cannot be blank"
                },
            )
        except ValidationError as e:
            # semver validator / full_clean errors -> nice API error
            raise HttpError(400, str(e))

        if not pv_created:
            raise HttpError(
                409, f'version "{version_str}" already exists for "{pkg_name}"'
            )

    relative_url = reverse("package-details", kwargs={"slug": package.slug})
    return {"url": request.build_absolute_uri(relative_url)}


def version_str_to_tuple(version_str: str):
    try:
        major, minor, patch = [int(x) for x in version_str.split(".")]
    except ValueError:
        raise HttpError(400, "invalid version string")
    return major, minor, patch


@router.get(
    "/{name}/download",
    url_name="package-download",
)
def download_package(request, name: str):
    # Expect "pkg@1.2.3" or "pkg@latest"
    try:
        pkg_name, version_str = name.split("@", 1)
    except ValueError:
        raise HttpError(400, 'expected "name@MAJOR.MINOR.PATCH" or "name@latest"')

    # Resolve the version
    if version_str == "latest":
        pv = (
            PackageVersion.objects.select_related("package")
            .filter(package__name=pkg_name)
            .order_by("-major", "-minor", "-patch")
            .first()
        )
        if pv is None:
            raise HttpError(404, "package has no versions")
    else:
        ver_major, ver_minor, ver_patch = version_str_to_tuple(version_str)
        try:
            pv = PackageVersion.objects.select_related("package").get(
                package__name=pkg_name,
                major=ver_major,
                minor=ver_minor,
                patch=ver_patch,
            )
        except PackageVersion.DoesNotExist:
            raise HttpError(404, "package version not found")

    if not pv.archive:
        raise HttpError(404, "package file missing")

    try:
        archive_file = pv.archive.open("rb")
    except FileNotFoundError:
        raise HttpError(404, "package file missing")

    pv.record_download()

    download_name = f"{pv.package.name}-{pv.version}.tar.gz"
    response = FileResponse(archive_file, content_type="application/gzip")
    response["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response


@router.get(
    "/{slug}/{version}/downloads",
    url_name="package-version-downloads",
    response=DownloadSeries,
)
def package_version_download_stats(request, slug: str, version: str):
    if not PackageVersion.objects.filter(package__slug=slug, version=version).exists():
        raise HttpError(404, "Package version not found")

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=29)
    end = today + timedelta(days=1)

    qs = (
        DownloadEvent.objects.filter(
            version__package__slug=slug,
            version__version=version,
            timestamp__gte=start,
            timestamp__lt=end,
        )
        .annotate(period=TruncDay("timestamp"))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )

    counts_by_day = {row["period"].date(): row["count"] for row in qs}

    labels: list[str] = []
    data: list[int] = []
    current = start
    for _ in range(30):
        labels.append(current.date().isoformat())
        data.append(counts_by_day.get(current.date(), 0))
        current += timedelta(days=1)

    return DownloadSeries(labels=labels, data=data, total=sum(data))


@router.get("/packages", response=list[str], url_name="package-search")
def list_packages(request, q: str):
    vector = (
        SearchVector("name", weight="A")
        + SearchVector("description", weight="B")
        + SearchVector("author", weight="C")
    )
    search_query = SearchQuery(q)

    packages = (
        Package.objects.annotate(
            rank=SearchRank(vector, search_query),
            substring_bonus=Case(
                When(name__icontains=q, then=Value(0.5)),
                default=Value(0.0),
                output_field=FloatField(),
            ),
        )
        .filter(Q(rank__gt=0) | Q(name__icontains=q))
        .annotate(final_score=F("rank") + F("substring_bonus"))
        .order_by("-final_score")
        .values_list("name", flat=True)
    )

    return list(packages[:10])

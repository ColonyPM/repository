import tarfile
from datetime import timedelta
from typing import List

import yaml
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db import IntegrityError
from django.db.models import Case, F, FloatField, Q, Value, When
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
from .models import Package

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
            roots = set()
            for member in file_members:
                name = member.name.lstrip("./")
                parts = [p for p in name.split("/") if p]
                if not parts:
                    continue
                if len(parts) < 2:
                    raise HttpError(400, "archive must contain a single root directory")
                roots.add(parts[0])
                if len(roots) > 1:
                    raise HttpError(400, "archive must contain a single root directory")

            if not roots:
                raise HttpError(400, "package.yaml is missing")

            root_dir = roots.pop()

            try:
                manifest_member = tar.getmember(f"{root_dir}/package.yaml")
            except KeyError:
                raise HttpError(400, "package.yaml is missing")

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
            try:
                readme_member = tar.getmember(f"{root_dir}/readme.md")
            except KeyError:
                readme_f = None
            else:
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
    if Package.objects.filter(name=pkg_name).exists():
        raise HttpError(400, f'package "{pkg_name}" already exists')

    package = Package(
        owner=request.auth,
        name=pkg_name,
        description=manifest_data["description"],
        version=str(manifest_data["version"]),
        author=str(manifest_data["author"]),
        deprecated=bool(manifest_data.get("deprecated", False)),
        readme=readme_text,
    )

    archive.seek(0)
    package.archive.save(archive.name, archive, save=False)

    try:
        package.save()
    except IntegrityError:
        raise HttpError(400, f'package "{pkg_name}" already exists')

    relative_url = reverse("package-details", kwargs={"slug": package.slug})
    absolute_url = request.build_absolute_uri(relative_url)

    return {"url": absolute_url}


@router.get(
    "/{name}/download",
    url_name="package-download",
)
def download_package(request, name: str):
    try:
        package = Package.objects.get(name=name)
    except Package.DoesNotExist:
        raise HttpError(404, "package not found")

    try:
        archive_file = package.archive.open("rb")
    except FileNotFoundError:
        raise HttpError(404, "package file missing")

    package.record_download()

    download_name = f"{package.name}.tar.gz"
    response = FileResponse(archive_file, content_type="application/gzip")
    response["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response


@router.get(
    "/{slug}/downloads",
    url_name="package-downloads",
    response=DownloadSeries,
)
def package_download_stats(request, slug: str):
    """
    Return daily downloads for the last 30 days (including today).
    """
    try:
        package = Package.objects.get(slug=slug)
    except Package.DoesNotExist:
        raise HttpError(404, "Package not found")

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=29)
    end = today + timedelta(days=1)

    qs = (
        package.downloads.filter(timestamp__gte=start, timestamp__lt=end)
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
    # 1. Setup Postgres Full-Text Search
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

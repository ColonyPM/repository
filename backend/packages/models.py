import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.text import slugify

SEMVER_SIMPLE_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def validate_semver(value: str):
    if not SEMVER_SIMPLE_RE.match(value):
        raise ValidationError("Version must be MAJOR.MINOR.PATCH (e.g. 1.2.3).")


def upload_to_package_version(instance, filename):
    return f"packages/{instance.package.slug}/{instance.version}/{filename}"


class Package(models.Model):
    name = models.CharField(unique=True, max_length=32)
    slug = models.SlugField(unique=True, editable=False)

    owner = models.ForeignKey(
        get_user_model(), related_name="packages", on_delete=models.CASCADE
    )

    description = models.TextField()
    author = models.CharField(max_length=16)
    deprecated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Package.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class PackageVersion(models.Model):
    package = models.ForeignKey(
        Package, related_name="versions", on_delete=models.CASCADE
    )

    version = models.CharField(max_length=32, validators=[validate_semver])

    major = models.PositiveIntegerField(editable=False)
    minor = models.PositiveIntegerField(editable=False)
    patch = models.PositiveIntegerField(editable=False)

    readme = models.TextField(blank=True)
    archive = models.FileField(upload_to=upload_to_package_version)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["package", "version"], name="uniq_package_version"
            ),
        ]
        indexes = [
            models.Index(fields=["package", "-major", "-minor", "-patch"]),
        ]

    def __str__(self):
        return f"{self.package.name}@{self.version}"

    def clean(self):
        m = SEMVER_SIMPLE_RE.match(self.version or "")
        if not m:
            raise ValidationError({"version": "Invalid version format."})
        self.major, self.minor, self.patch = map(int, m.groups())

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def download_count(self):
        return self.downloads.count()

    def record_download(self):
        DownloadEvent.objects.create(version=self)


class DownloadEvent(models.Model):
    version = models.ForeignKey(
        PackageVersion, related_name="downloads", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

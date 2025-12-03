from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify


class Package(models.Model):
    name = models.CharField(unique=True, max_length=32)
    slug = models.SlugField(unique=True, editable=False)

    owner = models.ForeignKey(
        get_user_model(), related_name="packages", on_delete=models.CASCADE
    )

    description = models.TextField()
    version = models.CharField(max_length=8)
    author = models.CharField(max_length=16)
    deprecated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    readme = models.TextField()
    archive = models.FileField(upload_to="packages")

    @property
    def download_count(self):
        return self.downloads.count()

    def record_download(self):
        DownloadEvent.objects.create(package=self)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            # Ensure uniqueness
            while Package.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug

        super().save(*args, **kwargs)


class DownloadEvent(models.Model):
    package = models.ForeignKey(
        Package, related_name="downloads", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

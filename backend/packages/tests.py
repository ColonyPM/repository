import io
import tarfile
import time
import uuid
from unittest import mock

import yaml
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.signing import BadSignature, SignatureExpired
from django.test import TestCase
from django.urls import reverse


class UploadPackageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234!",
        )

        self.client.force_login(self.user)

        token_url = reverse("api:generate-upload-token")
        self.valid_token = self.client.get(token_url).json()["token"]

        self.dummy_archive = SimpleUploadedFile(
            "dummy.tar.gz",
            b"not a real archive",
            content_type="application/gzip",
        )

        self.upload_url = reverse("api:upload-package")

    def make_archive(self, files, name="package.tar.gz", root_dir="package"):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path, content in files.items():
                data = content.encode("utf-8") if isinstance(content, str) else content
                arcname = path
                if root_dir:
                    arcname = f"{root_dir.rstrip('/')}/{path.lstrip('/')}"
                info = tarfile.TarInfo(arcname)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="application/gzip")

    def make_manifest(self, name="sample-package", deprecated=None, **overrides):
        manifest = {
            "name": name,
            "version": "1.0.0",
            "description": "A sample package",
            "author": "Test User",
        }
        if deprecated is not None:
            manifest["deprecated"] = deprecated
        manifest.update(overrides)
        return yaml.safe_dump(manifest)

    def test_refuse_no_token(self):
        """
        Absence of a token should return 401 and "invalid token".
        """
        response = self.client.post(
            self.upload_url,
            {"archive": self.dummy_archive},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())
        self.assertIn(
            "unauthorized",
            response.json()["detail"].lower(),
        )

    def test_refuse_bad_token(self):
        """
        An invalid token should return 401 and "invalid token".
        """
        dummy_archive = SimpleUploadedFile(
            "dummy.tar.gz",
            b"not a real archive",
            content_type="application/gzip",
        )

        response = self.client.post(
            reverse("api:upload-package"),
            {"archive": dummy_archive},
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())
        self.assertIn(
            "invalid upload token",
            response.json()["detail"],
        )

    def test_refuse_old_token(self):
        """
        Expired tokens should return 401 and "token expired".
        """
        expired_time = time.time() + 10000
        with mock.patch("django.core.signing.time.time", return_value=expired_time):
            response = self.client.post(
                self.upload_url,
                {"archive": self.dummy_archive},
                HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
            )

        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())
        self.assertEqual(response.json()["detail"], "upload token expired")

    def test_refuse_non_archive_files(self):
        """
        Trying to upload a non-archive file should return 400 and "invalid archive format".
        """
        response = self.client.post(
            self.upload_url,
            {"archive": self.dummy_archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
        self.assertEqual(response.json()["detail"], "invalid archive format")

    def test_refuse_no_manifest(self):
        """
        Trying to upload a package without a manifest should return 400 and "package.yml is missing".
        """
        archive_without_manifest = self.make_archive({"readme.md": "hello"})

        response = self.client.post(
            self.upload_url,
            {"archive": archive_without_manifest},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
        self.assertEqual(response.json()["detail"], "package.yml is missing")

    def test_refuse_invalid_manifest_yaml(self):
        """
        Invalid YAML should return 400 and a YAML error message.
        """
        bad_manifest_archive = self.make_archive({"package.yml": "name: ["})

        response = self.client.post(
            self.upload_url,
            {"archive": bad_manifest_archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
        self.assertIn("package.yml is not valid YAML", response.json()["detail"])

    def test_refuse_manifest_not_mapping(self):
        """
        Non-mapping manifests should return 400 and a clear error.
        """
        archive = self.make_archive({"package.yml": '"just a string"'})

        response = self.client.post(
            self.upload_url,
            {"archive": archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"], "package.yml must contain a mapping/object"
        )

    def test_refuse_manifest_schema_errors(self):
        """
        Schema violations should return 400 and mention invalid package.yml.
        """
        manifest_missing_fields = {
            "name": "pkg",
            "version": "1.0.0",
            "author": "someone",
        }
        archive = self.make_archive(
            {"package.yml": yaml.safe_dump(manifest_missing_fields)}
        )

        response = self.client.post(
            self.upload_url,
            {"archive": archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "invalid package.yml: Missing key: 'description'",
        )

    def test_refuse_manifest_schema_type_error(self):
        """
        Schema type errors should return 400 and include schema error detail.
        """
        manifest_with_type_error = self.make_manifest(deprecated="not-bool")
        archive = self.make_archive({"package.yml": manifest_with_type_error})

        response = self.client.post(
            self.upload_url,
            {"archive": archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertTrue(
            detail.startswith("invalid package.yml: Key 'deprecated' error"),
            detail,
        )
        self.assertIn("should be instance of 'bool'", detail)

    def test_refuse_manifest_schema_type_error_required_field(self):
        """
        Schema type errors on required fields should also bubble up.
        """
        manifest_with_type_error = yaml.safe_dump(
            {
                "name": "pkg",
                "version": 123,
                "description": "desc",
                "author": "someone",
            }
        )
        archive = self.make_archive({"package.yml": manifest_with_type_error})

        response = self.client.post(
            self.upload_url,
            {"archive": archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertTrue(
            detail.startswith("invalid package.yml: Key 'version' error"),
            detail,
        )
        self.assertIn("should be instance of 'str'", detail)

    def test_upload_success(self):
        """
        Valid archives should be accepted and stored, persisting manifest fields.
        """
        pkg_name = f"sample-package-{uuid.uuid4().hex[:8]}"
        manifest = self.make_manifest(name=pkg_name)
        archive = self.make_archive(
            {
                "package.yml": manifest,
                "readme.md": "# Hello\n",
            },
            name="sample.tar.gz",
        )

        response = self.client.post(
            self.upload_url,
            {"archive": archive},
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.assertIn("url", response.json())

        from .models import Package

        package = Package.objects.get(name=pkg_name)
        self.assertEqual(package.description, "A sample package")
        self.assertEqual(package.author, "Test User")
        self.assertEqual(package.readme, "# Hello\n")
        self.assertEqual(package.version, "1.0.0")
        self.assertFalse(package.deprecated)


class DownloadPackageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="downloaduser",
            password="test1234!",
        )

        self.client.force_login(self.user)

    def create_package(self, name="downloadable-package", content=b"archive-bytes"):
        from .models import Package

        pkg = Package.objects.create(
            owner=self.user,
            name=name,
            description="desc",
            version="1.0.0",
            author="Test User",
            deprecated=False,
            readme="readme",
        )
        pkg.archive.save("archive.tar.gz", ContentFile(content), save=True)
        return pkg

    def test_download_success(self):
        pkg = self.create_package()
        url = reverse("api:package-download", kwargs={"name": pkg.name})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        body = b"".join(response.streaming_content)
        self.assertEqual(body, b"archive-bytes")
        disposition = response["Content-Disposition"]
        self.assertIn("attachment;", disposition)
        self.assertEqual(disposition, f'attachment; filename="{pkg.name}.tar.gz"')
        self.assertEqual(pkg.downloads.count(), 1)

    def test_download_not_found(self):
        url = reverse("api:package-download", kwargs={"name": "missing"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "package not found")

from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired
from django.test import TestCase
from django.urls import reverse

from .api import TOKEN_MAX_AGE, signer


class UploadTokenTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234!",
        )

    def test_requires_authentication(self):
        """
        Unauthenticated users should get 401.
        """
        url = reverse("api:generate-upload-token")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_returns_valid_token_for_logged_in_user(self):
        """
        Logged-in user should get a valid timestamp-signed token
        whose payload is their user id.
        """
        self.client.force_login(self.user)

        url = reverse("api:generate-upload-token")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("token", data)

        token = data["token"]
        self.assertIsInstance(token, str)

        try:
            unsigned = signer.unsign(token, max_age=TOKEN_MAX_AGE)
        except SignatureExpired:
            self.fail("Token expired immediately, check TOKEN_MAX_AGE or clock skew.")
        except BadSignature:
            self.fail("Token is not valid for the configured signer.")

        self.assertEqual(str(self.user.id), unsigned)

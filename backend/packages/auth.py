# packages/auth.py
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from ninja.errors import HttpError
from ninja.security import HttpBearer

signer = TimestampSigner(salt="upload-token")


class UploadTokenAuth(HttpBearer):
    def __init__(self, *, max_age: int):
        super().__init__()
        self.max_age = max_age

    def authenticate(self, request, token: str):
        try:
            user_id = signer.unsign(token, max_age=self.max_age)

        except SignatureExpired:
            # Token expired (timestamp valid, signature ok)
            raise HttpError(401, "upload token expired")

        except BadSignature:
            # Token tampered with or malformed
            raise HttpError(401, "invalid upload token")

        # Look up the user
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise HttpError(401, "user does not exist")

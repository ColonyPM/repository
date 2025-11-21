from django.core.signing import TimestampSigner
from ninja import Router
from ninja.errors import HttpError
from ninja.schema import Schema
from ninja.security import django_auth

signer = TimestampSigner(salt="upload-token")
TOKEN_MAX_AGE = 30  # seconds

router = Router()


class UploadOK(Schema):
    token: str


@router.get(
    "/generate-upload-token", url_name="generate-upload-token", auth=django_auth
)
def get_upload_token(request):
    token = signer.sign(str(request.user.id))
    return {"token": token}

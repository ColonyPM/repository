from django.http import HttpRequest
from ninja import NinjaAPI, Schema


class PingResponse(Schema):
    message: str


def register_api(api: NinjaAPI) -> None:
    @api.get("/packages/ping/", response=PingResponse)
    def ping_endpoint(request: HttpRequest) -> PingResponse:
        return PingResponse(message="pong")

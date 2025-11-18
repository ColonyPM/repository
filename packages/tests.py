import json
from typing import cast

from django.http import HttpResponse
from django.test import TestCase


class PingEndpointTests(TestCase):
    def test_ping_returns_pong_message(self):
        response = cast(HttpResponse, self.client.get("/api/packages/ping/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"message": "pong"})

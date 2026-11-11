"""HTTP client for the content service. The practice service never reads the content
table directly; problem data (including answer keys) comes over this API."""

import os

import httpx


class ContentUnavailable(Exception):
    pass


class ContentClient:
    def __init__(self, base_url: str | None = None, transport: httpx.BaseTransport | None = None):
        self.http = httpx.Client(
            base_url=base_url or os.getenv("CONTENT_URL", "http://localhost:5001"),
            headers={"X-Service-Token": os.getenv("SERVICE_TOKEN", "dev-service-token")},
            timeout=httpx.Timeout(2.0),
            transport=transport or httpx.HTTPTransport(retries=2),  # retries connection failures only
        )

    def _get(self, path: str, **params):
        try:
            r = self.http.get(path, params=params)
        except httpx.HTTPError as e:
            raise ContentUnavailable(str(e)) from e
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ContentUnavailable(f"content service returned {r.status_code}")
        return r.json()

    def problem_with_answer(self, problem_id: str) -> dict | None:
        return self._get(f"/internal/problems/{problem_id}")

    def problems_near(self, topic: str, rating: int, exclude: list[str]) -> list[dict] | None:
        return self._get(f"/topics/{topic}/problems", near=rating, exclude=",".join(exclude), limit=1)

    def topic(self, slug: str) -> dict | None:
        return self._get(f"/topics/{slug}")

import os
import time
from typing import Any, Optional

import httpx


class TastyTradeClient:
    """
    OAuth2 client for the TastyTrade API.

    Authenticates with a client secret + refresh token (from a Personal OAuth
    Grant — see README) instead of an account username/password. Access
    tokens are short-lived (~15 minutes) and refreshed automatically; the
    refresh token itself does not expire unless revoked.
    """

    PRODUCTION_URL = "https://api.tastytrade.com"
    SANDBOX_URL = "https://api.cert.tastytrade.com"

    def __init__(self) -> None:
        self._client_secret = os.environ["TASTYTRADE_CLIENT_SECRET"]
        self._refresh_token = os.environ["TASTYTRADE_REFRESH_TOKEN"]
        sandbox = os.environ.get("TASTYTRADE_SANDBOX", "false").lower() == "true"
        base_url = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL

        self._access_token: Optional[str] = None
        self._access_token_expiry: float = 0.0
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    async def _refresh_access_token(self) -> None:
        resp = await self._http.post(
            "/oauth/token",
            json={
                "grant_type": "refresh_token",
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
            headers={"Authorization": ""},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._access_token_expiry = time.time() + data.get("expires_in", 900)
        self._http.headers["Authorization"] = f"Bearer {self._access_token}"

    def _token_expired(self) -> bool:
        # Refresh a little early to avoid racing the actual expiry.
        return not self._access_token or time.time() > self._access_token_expiry - 30

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._token_expired():
            await self._refresh_access_token()

        resp = await self._http.request(method, path, **kwargs)

        if resp.status_code == 401:
            await self._refresh_access_token()
            resp = await self._http.request(method, path, **kwargs)

        resp.raise_for_status()
        return resp.json() if resp.content else {}

    async def get(self, path: str, params: Optional[dict] = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: Optional[dict] = None) -> Any:
        return await self._request("POST", path, json=body)

    async def put(self, path: str, body: Optional[dict] = None) -> Any:
        return await self._request("PUT", path, json=body)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    async def close(self) -> None:
        await self._http.aclose()

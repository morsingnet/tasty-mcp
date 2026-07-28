import os
from typing import Any, Optional

import httpx


class TastyTradeClient:
    PRODUCTION_URL = "https://api.tastytrade.com"
    SANDBOX_URL = "https://api.cert.tastytrade.com"

    def __init__(self) -> None:
        self._username = os.environ["TASTYTRADE_USERNAME"]
        self._password = os.environ["TASTYTRADE_PASSWORD"]
        sandbox = os.environ.get("TASTYTRADE_SANDBOX", "false").lower() == "true"
        base_url = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL

        self._session_token: Optional[str] = None
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    async def _login(self) -> None:
        resp = await self._http.post(
            "/sessions",
            json={
                "login": self._username,
                "password": self._password,
                "remember-me": True,
            },
        )
        resp.raise_for_status()
        self._session_token = resp.json()["data"]["session-token"]
        self._http.headers["Authorization"] = self._session_token

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._session_token:
            await self._login()

        resp = await self._http.request(method, path, **kwargs)

        if resp.status_code == 401:
            self._session_token = None
            await self._login()
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
        if self._session_token:
            try:
                await self._http.delete("/sessions")
            except Exception:
                pass
        await self._http.aclose()

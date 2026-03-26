import time
from typing import Optional
import logging
import aiohttp

from ..settings import settings

logger = logging.getLogger(__name__)

class AuthManager:

    _instance: Optional["AuthManager"] = None

    def __init__(self):
        self.bearer_token: Optional[str] = None
        self.expires_at: float = 0.0

    async def get_token(self) -> str:
        if self._is_token_valid():
            return self.bearer_token
        await self._fetch_token()
        return self.bearer_token

    def invalidate(self) -> None:
        self.bearer_token = None
        self.expires_at = 0.0
        logger.debug("Bearer token invalidated.")


    def _is_token_valid(self) -> bool:
        return self.bearer_token is not None and time.monotonic() < self.expires_at - settings.auth.expiry_margin

    async def _fetch_token(self) -> None:
        logger.debug("Fetching new bearer token from %s", settings.auth.url)
        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.auth.client_id,
            "client_secret": settings.auth.client_secret,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    settings.auth.url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                resp.raise_for_status()
                body = await resp.json()

        self.bearer_token = body["access_token"]
        expires_in = int(body.get("expires_in", settings.auth.expiry_default))
        self.expires_at = time.monotonic() + expires_in
        logger.debug(
            "New token expires in %ds, at %.1f).",
            expires_in,
            self.expires_at,
        )
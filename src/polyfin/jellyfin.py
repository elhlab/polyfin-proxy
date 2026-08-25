from dataclasses import dataclass, field
from typing import Optional, Protocol
from urllib.parse import quote_plus, unquote_plus

import aiohttp
from starlette.datastructures import Headers

from polyfin.models import Item


@dataclass
class MediaBrowserAuth:

    # Token can possibly be None if other params are filled? (see https://gist.github.com/nielsvanvelzen/ea047d9028f676185832e51ffaf12a6f#examples)
    Token: Optional[str] = field(default=None)
    fields: dict[str, str] = field(default_factory=lambda: dict())

    def build(self):
        values = [("Token", self.Token)]

        values.extend(self.fields.items())

        return "MediaBrowser {}".format(
            ", ".join(f'{key}="{quote_plus(value)}"' for key, value in values if value)
        )

    @staticmethod
    def parse(value: str) -> "MediaBrowserAuth":
        if not value.startswith("MediaBrowser "):
            raise ValueError(f"Invalid MediaBrowser Authorization: '{value}'")

        raw_fields = value[13:].strip()

        fields: dict[str, str] = {}
        for raw_field in raw_fields.split(", "):
            k, v = raw_field.split("=")

            fields[k] = unquote_plus(v.strip('"'))

        return MediaBrowserAuth(fields.get("Token", None), fields)


def extract_mediabrowser_auth(headers: Headers) -> MediaBrowserAuth:
    value = headers.get("Authorization")

    if value is None:
        raise ValueError("Missing Authorization header")

    return MediaBrowserAuth.parse(value)


class ProviderIdCache(Protocol):

    async def set(self, item_id: str, data: dict[str, str]) -> None: ...
    async def get(self, item_id: str) -> Optional[dict[str, str]]: ...


class Api:

    _session: aiohttp.ClientSession
    _pid_cache: ProviderIdCache

    def __init__(self, base: str) -> None:
        self._base = base

    async def get_item(self, item_id: str, auth: MediaBrowserAuth) -> dict:
        res = await self._session.get(
            self._base.strip("/") + f"/Items/{item_id}",
            headers={"Authorization": auth.build()},
        )
        res.raise_for_status()

        return await res.json()

    async def get_current_user(self, auth: MediaBrowserAuth) -> dict:
        res = await self._session.get(
            self._base.strip("/") + "/Users/Me",
            headers={"Authorization": auth.build()},
        )
        res.raise_for_status()

        return await res.json()

    # TODO: this likely wont work for season or series items
    async def populate_provider_ids(self, item: Item, auth: MediaBrowserAuth):
        if item.Type not in ["Movie"]:
            raise ValueError(f"Unexpected item type: '{item.Type}'")

        if item.ProviderIds is None:
            ids = await self.fetch_provider_ids(item.Id, auth)
            item.ProviderIds = ids

    async def fetch_provider_ids(
        self, item_id: str, auth: MediaBrowserAuth
    ) -> dict[str, str]:
        """Resolves providerids from jellyfin"""

        ids = await self._pid_cache.get(item_id)
        if ids is not None:
            return ids

        item = await self.get_item(item_id, auth)

        ids = item["ProviderIds"]
        await self._pid_cache.set(item_id, ids)
        return ids

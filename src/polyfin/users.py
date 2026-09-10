from dataclasses import dataclass, field
from typing import Optional

from cashews import cache

from .jellyfin import JellyfinApi, MediaBrowserAuth

cache.setup("mem://")


@dataclass(slots=True, frozen=True)
class User:
    id: str
    locale_id: Optional[str] = field(default=None)


class UserManager:

    japi: JellyfinApi

    def __init__(self) -> None:
        pass

    @cache(ttl="5m", key="user_token:{auth.Token}")
    async def get_user_from_auth(self, auth: MediaBrowserAuth) -> User:
        juser = await self.japi.get_current_user(auth)
        return User(juser["Id"])

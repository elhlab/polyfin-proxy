from dataclasses import dataclass, field
from typing import Optional

from .cache import cache
from .jellyfin import JellyfinApi, MediaBrowserAuth


@dataclass(slots=True, frozen=True)
class User:
    id: str
    language_id: Optional[str] = field(default=None)


class UserManager:

    japi: JellyfinApi

    def __init__(self) -> None:
        pass

    @cache(ttl="5m", key="user_token:{auth.Token}", prefix=__name__)
    async def get_user_from_auth(self, auth: MediaBrowserAuth) -> User:
        juser = await self.japi.get_current_user(auth)
        return User(juser["Id"])

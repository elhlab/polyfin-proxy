from typing import Optional

from .jellyfin import MediaBrowserAuth
from .users import UserManager


class Localiser:

    user_manager: UserManager
    config: Any

    # { "en": { "*": <locale-id>, "us": <locale-id> } }
    tag_to_locale_id: dict[str, dict[str, str]]

    def __init__(self) -> None:
        self.tag_to_locale_id = {}

        for locale in self.config.list_locales():
            pass  # TODO:

    def is_valid_locale_id(self, locale_id: str) -> bool:
        pass  # TODO

    def resolve_locale_from_tag(self, tag: str):
        head, tail = tag.lower().split("-", maxsplit=1)

        if head not in self.tag_to_locale_id:
            return None

        tails = self.tag_to_locale_id[head]
        if tail not in tails:
            return tails.get("*", None)

        return tails[tail]

    async def resolve_locale(
        self, auth: MediaBrowserAuth, accepted_tags: Optional[list[str]] = None
    ) -> Optional[str]:
        """Resolves a user locale from the database falling back to accepted_tags which is a sorted list of preferred language tags (eg. En-US).
        Returns None if no locale found."""

        if accepted_tags is None:
            accepted_tags = []

        user = await self.user_manager.get_user_from_auth(auth)
        if user.locale_id and self.is_valid_locale_id(user.locale_id):
            return user.locale_id

        for tag in accepted_tags:
            locale_id = self.resolve_locale_from_tag(tag)
            if locale_id is not None:
                return locale_id

        return None

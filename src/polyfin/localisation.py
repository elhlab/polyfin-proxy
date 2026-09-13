import logging
import time
from typing import Optional

from polyfin.config import Config, Language

from .jellyfin import MediaBrowserAuth
from .users import UserManager

UNRESOLVED_TAGS_WARNING_TTL_SECONDS = 60 * 60

logger = logging.getLogger(__name__)


class Localiser:

    user_manager: UserManager
    config: Config

    # { "en": { "*": <locale-id>, "us": <locale-id> } }
    locale_map: dict[str, dict[str, str]]
    language_map: dict[str, Language]

    # tags_key -> last time (time.monotonic()) we logged a warning for it
    _last_warned_at: dict[str, float]

    def __init__(self, config: Config, user_manager: UserManager) -> None:
        self.config = config
        self.user_manager = user_manager

        self.locale_map = {}
        self.language_map = {}
        self._last_warned_at = {}
        for language in self.config.languages:
            self.language_map[language.id] = language

            for tag in language.locales:
                tag = tag.lower()
                head, tail = tag.split("-", maxsplit=1)

                if head not in self.locale_map:
                    self.locale_map[head] = {}

                if tail in self.locale_map[head]:
                    raise ValueError(
                        f"Duplicate locale tag: {tag} for language {language.id}"
                    )

                self.locale_map[head][tail] = language.id

    def is_valid_language(self, language_id: str) -> bool:
        return language_id in self.language_map

    def resolve_locale_from_tag(self, tag: str):
        head, _, tail = tag.lower().partition("-")

        if head not in self.locale_map:
            return None

        tails = self.locale_map[head]
        if tail in tails:
            return tails[tail]

        if "*" in tails:
            return tails["*"]

        # No exact or wildcard match for this region, but if every region
        # registered under this head resolves to the same language, there's
        # nothing actually ambiguous about picking it.
        distinct_language_ids = set(tails.values())
        if len(distinct_language_ids) == 1:
            return next(iter(distinct_language_ids))

        return None

    async def resolve_locale(
        self, auth: MediaBrowserAuth, accepted_tags: Optional[list[str]] = None
    ) -> Optional[str]:
        """Resolves a user locale from the database falling back to accepted_tags
        which is a sorted list of preferred language tags (eg. En-US).
        Returns None if no locale found."""

        if accepted_tags is None:
            accepted_tags = []

        user = await self.user_manager.get_user_from_auth(auth)
        if user.language_id and self.is_valid_language(user.language_id):
            return user.language_id

        for tag in accepted_tags:
            locale_id = self.resolve_locale_from_tag(tag)
            if locale_id is not None:
                return locale_id

        if accepted_tags:
            self._warn_unresolved_tags(",".join(accepted_tags))

        return None

    def _warn_unresolved_tags(self, tags_key: str) -> None:
        now = time.monotonic()
        last_warned_at = self._last_warned_at.get(tags_key)
        if (
            last_warned_at is not None
            and now - last_warned_at < UNRESOLVED_TAGS_WARNING_TTL_SECONDS
        ):
            return

        self._last_warned_at[tags_key] = now
        logger.warning("no configured language matches accepted tags: %s", tags_key)

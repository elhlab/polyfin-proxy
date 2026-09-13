import pytest

from polyfin.config import Config
from polyfin.jellyfin import MediaBrowserAuth
from polyfin.localisation import Localiser
from polyfin.users import User


def make_config(languages: list[dict]) -> Config:
    """Builds a Config with the given raw language dicts and a throwaway
    provider (Config requires at least one of each)."""

    return Config.model_validate(
        {
            "languages": languages,
            "providers": [
                {
                    "id": "provider1",
                    "languages": {languages[0]["id"]: languages[0]["locales"][0]},
                    "handles": ["MOVIE"],
                }
            ],
        }
    )


class FakeUserManager:
    """Stands in for UserManager so tests don't need a real Jellyfin API.
    Set `.user` to whatever get_user_from_auth should return."""

    def __init__(self, user: User) -> None:
        self.user = user

    async def get_user_from_auth(self, auth: MediaBrowserAuth) -> User:
        return self.user


def make_localiser(languages: list[dict], user: User) -> Localiser:
    return Localiser(make_config(languages), FakeUserManager(user))  # type: ignore


AUTH = MediaBrowserAuth(Token="tok")


def test_is_valid_language():
    localiser = make_localiser(
        [
            {
                "id": "english",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US", "en-UK"],
            },
            {
                "id": "german",
                "name": "German",
                "season_label": "Staffel {{season_num}}",
                "locales": ["de-DE"],
            },
        ],
        User(id="a" * 32),
    )

    assert localiser.is_valid_language("english")
    assert localiser.is_valid_language("german")
    assert not localiser.is_valid_language("french")


def test_ambiguous_choice():
    localiser = make_localiser(
        [
            {
                "id": "british",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-UK"],
            },
            {
                "id": "american",
                "name": "American English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US"],
            },
        ],
        User(id="a" * 32),
    )

    # test that a bare tag with multiple possible languages does not resolve
    assert localiser.resolve_locale_from_tag("en") is None


def test_multilocales():
    localiser = make_localiser(
        [
            {
                "id": "british",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-UK"],
            },
            {
                "id": "american",
                "name": "American English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US", "en-*"],
            },
        ],
        User(id="a" * 32),
    )

    # test that a bare tag with multiple possible languages does not resolve
    assert localiser.resolve_locale_from_tag("en-CA") == "american"


def test_resolve_locale_from_tag():
    localiser = make_localiser(
        [
            {
                "id": "lang_english",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US", "en-UK"],
            },
            {
                "id": "lang_german",
                "name": "German",
                "season_label": "Staffel {{season_num}}",
                "locales": ["de-DE"],
            },
            {
                "id": "lang_french",
                "name": "French",
                "season_label": "Saison {{season_num}}",
                "locales": ["fr-*"],
            },
        ],
        User(id="a" * 32),
    )

    # exact match
    assert localiser.resolve_locale_from_tag("en-US") == "lang_english"

    # wildcard fallback
    assert localiser.resolve_locale_from_tag("en-CA") == "lang_english"

    # bare tag with no region matches the wildcard
    assert localiser.resolve_locale_from_tag("en") == "lang_english"

    # bare tag matches when every region under that head is the same language
    assert localiser.resolve_locale_from_tag("de") == "lang_german"

    # bare tag stays unresolved when regions map to different languages
    assert localiser.resolve_locale_from_tag("xx") is None

    # unknown head returns None
    assert localiser.resolve_locale_from_tag("fi-FI") is None

    # test that the tag is case-insensitive
    assert localiser.resolve_locale_from_tag("EN-us") == "lang_english"

    # test that the glob tag resolves correctly
    assert localiser.resolve_locale_from_tag("fr-FR") == "lang_french"


@pytest.mark.asyncio
async def test_get_locale_from_auth_user_language():
    localiser = make_localiser(
        [
            {
                "id": "lang_english",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US", "en-UK"],
            },
            {
                "id": "lang_german",
                "name": "German",
                "season_label": "Staffel {{season_num}}",
                "locales": ["de-DE"],
            },
        ],
        User(id="a" * 32, language_id="lang_german"),
    )

    # user has a user selected language, so we return that even though the accepted tags prefer English
    assert (
        await localiser.resolve_locale(AUTH, accepted_tags=["en-US", "de-DE"])
        == "lang_german"
    )


@pytest.mark.asyncio
async def test_get_locale_from_auth_user_no_language():
    localiser = make_localiser(
        [
            {
                "id": "lang_english",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-US", "en-UK"],
            },
            {
                "id": "lang_german",
                "name": "German",
                "season_label": "Staffel {{season_num}}",
                "locales": ["de-DE"],
            },
        ],
        User(id="a" * 32, language_id=None),
    )

    # user has no selected language, so we fall back to the accepted tags
    assert (
        await localiser.resolve_locale(AUTH, accepted_tags=["en-US", "de-DE"])
        == "lang_english"
    )

    # test fall back with bare tag
    assert (
        await localiser.resolve_locale(AUTH, accepted_tags=["en", "de-DE"])
        == "lang_english"
    )

    # test fall back with unknown tag
    assert (
        await localiser.resolve_locale(AUTH, accepted_tags=["fr-FR", "de-DE"])
        == "lang_german"
    )

    # test fall back with accepted tags which don't match any configured language
    assert (
        await localiser.resolve_locale(AUTH, accepted_tags=["fr-FR", "es-ES"]) is None
    )


@pytest.mark.asyncio
async def test_resolve_locale_with_no_accepted_tags_arg():
    localiser = make_localiser(
        [
            {
                "id": "lang_german",
                "name": "German",
                "season_label": "Staffel {{season_num}}",
                "locales": ["de-DE"],
            },
        ],
        User(id="a" * 32, language_id="lang_german"),
    )

    # accepted_tags omitted entirely, not just an empty list
    assert await localiser.resolve_locale(AUTH) == "lang_german"


def test_duplicate_locale_tag_across_languages_rejected():
    with pytest.raises(ValueError, match="Duplicate locale tag"):
        make_localiser(
            [
                {
                    "id": "english",
                    "name": "English",
                    "season_label": "Season {{season_num}}",
                    "locales": ["en-US"],
                },
                {
                    "id": "australian-english",
                    "name": "Australian English",
                    "season_label": "Season {{season_num}}",
                    "locales": ["en-US"],
                },
            ],
            User(id="a" * 32),
        )

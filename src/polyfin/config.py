from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from polyfin.models import ItemType


class Language(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Unique identifier for this language, e.g. "german-language" or "english-language"
    id: str

    # Human-readable name for this language, e.g. "Deutsch" or "English"
    name: str

    # Label to use for seasons in this language,
    # e.g. "Staffel {{season_num}}" this is visible to the user
    season_label: str

    # List of language tags that match this language, e.g. de-*, en-US, etc.
    locales: list[str]

    @field_validator("locales")
    @classmethod
    def _check_locale_format(cls, value: list[str]) -> list[str]:
        for tag in value:
            head, sep, tail = tag.partition("-")
            if not sep or not head or not tail:
                raise ValueError(
                    f"invalid locale tag {tag!r}: expected '<lang>-<region>' or '<lang>-*'"
                )

        return value


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Jellyfin user id
    id: str = Field(pattern=r"^[0-9a-fA-F]{32}$")

    # Hardcoded locale id for this user, e.g. "german-language" or "english-language"
    locale_id: str


class Provider(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str

    # List of languages this provider supports, e.g. "german-language" or "english-language"
    # Used to restrict which providers are used for which languages.
    languages: dict[str, str]

    # List of item types this provider should handle, e.g. movie, show, season, episode.
    # Used to restrict which providers are used for which items.
    handles: list[ItemType]

    # List of arguments to pass to the provider, e.g. api_key, base_url, etc.
    # Secrets should use the following format: "secrets://<secret-name>"
    # to retrieve the value from an enviromental variable.
    arguments: dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class Config(BaseModel):
    users: list[User] = []
    languages: list[Language] = Field(min_length=1)
    providers: list[Provider] = Field(min_length=1)

    @field_validator("users", mode="before")
    @classmethod
    def _default_none_users_to_empty(cls, value: object) -> object:
        return [] if value is None else value

    @model_validator(mode="after")
    def _check_user_locale_references(self) -> "Config":
        language_ids = {language.id for language in self.languages}

        for user in self.users:
            if user.locale_id not in language_ids:
                raise ValueError(
                    f"user {user.id!r} references unknown locale_id {user.locale_id!r}"
                )

        return self

    @model_validator(mode="after")
    def _check_provider_language_references(self) -> "Config":
        language_ids = {language.id for language in self.languages}

        for provider in self.providers:
            for language_id in provider.languages:
                if language_id not in language_ids:
                    raise ValueError(
                        f"provider {provider.id!r} references unknown language_id {language_id!r}"
                    )

        return self

    @model_validator(mode="after")
    def _check_unique_language_ids(self) -> "Config":
        seen: set[str] = set()

        for language in self.languages:
            if language.id in seen:
                raise ValueError(f"duplicate language id {language.id!r}")
            seen.add(language.id)

        return self

    @model_validator(mode="after")
    def _check_unique_user_ids(self) -> "Config":
        seen: set[str] = set()

        for user in self.users:
            if user.id in seen:
                raise ValueError(f"duplicate user id {user.id!r}")
            seen.add(user.id)

        return self

    @model_validator(mode="after")
    def _check_unique_provider_ids(self) -> "Config":
        seen: set[str] = set()

        for provider in self.providers:
            if provider.id in seen:
                raise ValueError(f"duplicate provider id {provider.id!r}")
            seen.add(provider.id)

        return self

    @classmethod
    def load_yaml(cls, config_path: str | Path) -> "Config":
        """Load configuration from a YAML file."""
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        return cls.model_validate(data)

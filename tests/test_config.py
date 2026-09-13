import pytest
from pydantic import ValidationError

from polyfin.config import Config


def base_config_data() -> dict:
    return {
        "languages": [
            {
                "id": "english",
                "name": "English",
                "season_label": "Season {{season_num}}",
                "locales": ["en-*"],
            }
        ],
        "users": [{"id": "a" * 32, "locale_id": "english"}],
        "providers": [
            {"id": "provider1", "languages": {"english": "en-US"}, "handles": ["MOVIE"]}
        ],
    }


def test_valid_config_loads():
    Config.model_validate(base_config_data())


def test_duplicate_language_id_rejected():
    data = base_config_data()
    data["languages"].append(dict(data["languages"][0]))

    with pytest.raises(ValidationError, match="duplicate language id"):
        Config.model_validate(data)


def test_duplicate_user_id_rejected():
    data = base_config_data()
    data["users"].append(dict(data["users"][0]))

    with pytest.raises(ValidationError, match="duplicate user id"):
        Config.model_validate(data)


def test_duplicate_provider_id_rejected():
    data = base_config_data()
    data["providers"].append(dict(data["providers"][0]))

    with pytest.raises(ValidationError, match="duplicate provider id"):
        Config.model_validate(data)


def test_user_locale_id_mismatch_rejected():
    data = base_config_data()
    data["users"][0]["locale_id"] = "not-a-real-language"

    with pytest.raises(ValidationError, match="unknown locale_id"):
        Config.model_validate(data)


def test_provider_language_mismatch_rejected():
    data = base_config_data()
    data["providers"][0]["languages"] = {"not-a-real-language": "en-US"}

    with pytest.raises(ValidationError, match="unknown language_id"):
        Config.model_validate(data)


def test_load_yaml_reads_valid_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
languages:
  - id: english
    name: English
    season_label: "Season {{season_num}}"
    locales:
      - en-*

users:
  - id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    locale_id: english

providers:
  - id: provider1
    languages:
      english: en-US
    handles:
      - MOVIE
""")

    config = Config.load_yaml(config_path)

    assert [language.id for language in config.languages] == ["english"]
    assert config.users[0].locale_id == "english"
    assert config.providers[0].id == "provider1"


def test_load_yaml_rejects_invalid_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
languages:
  - id: english
    name: English
    season_label: "Season {{season_num}}"
    locales:
      - en-*

users:
  - id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    locale_id: not-a-real-language

providers:
  - id: provider1
    languages:
      english: en-US
    handles:
      - MOVIE
""")

    with pytest.raises(ValidationError, match="unknown locale_id"):
        Config.load_yaml(config_path)


def test_missing_users_key_defaults_to_empty():
    data = base_config_data()
    del data["users"]

    config = Config.model_validate(data)

    assert config.users == []


def test_null_users_key_defaults_to_empty():
    data = base_config_data()
    data["users"] = None

    config = Config.model_validate(data)

    assert config.users == []


def test_missing_providers_key_rejected():
    data = base_config_data()
    del data["providers"]

    with pytest.raises(ValidationError, match="[Ff]ield required"):
        Config.model_validate(data)


def test_empty_languages_list_rejected():
    data = base_config_data()
    data["languages"] = []
    data["users"] = []
    data["providers"] = []

    with pytest.raises(ValidationError):
        Config.model_validate(data)


def test_empty_providers_list_rejected():
    data = base_config_data()
    data["providers"] = []

    with pytest.raises(ValidationError):
        Config.model_validate(data)


def test_language_ids_are_case_sensitive():
    data = base_config_data()
    data["languages"].append(
        {
            "id": "English",
            "name": "English (alt case)",
            "season_label": "Season {{season_num}}",
            "locales": ["en-GB"],
        }
    )

    config = Config.model_validate(data)

    assert {language.id for language in config.languages} == {"english", "English"}


def test_user_locale_id_reference_is_case_sensitive():
    data = base_config_data()
    data["users"][0]["locale_id"] = "English"

    with pytest.raises(ValidationError, match="unknown locale_id"):
        Config.model_validate(data)


@pytest.mark.parametrize("bad_tag", ["en", "-us", "en-", ""])
def test_malformed_locale_tag_rejected(bad_tag):
    data = base_config_data()
    data["languages"][0]["locales"] = [bad_tag]

    with pytest.raises(ValidationError, match="invalid locale tag"):
        Config.model_validate(data)


def test_valid_locale_tag_shapes_accepted():
    data = base_config_data()
    data["languages"][0]["locales"] = ["en-*", "en-US", "zh-Hans-CN"]

    config = Config.model_validate(data)

    assert config.languages[0].locales == ["en-*", "en-US", "zh-Hans-CN"]

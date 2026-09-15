import pytest
from pydantic import ValidationError

from polyfin.models import MovieItem, SeriesItem


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (
            MovieItem,
            {
                "Id": "abc123",
                "Type": "Movie",
                "Name": "Some Movie",
                "Overview": "A movie about things.",
                "ProviderIds": {"Tmdb": "42"},
            },
        ),
        (
            SeriesItem,
            {
                "Id": "def456",
                "Type": "Series",
                "Name": "Some Series",
                "Overview": "A series about things.",
                "ProviderIds": {"Tmdb": "99"},
            },
        ),
    ],
)
def test_item_parses_known_fields(model, data):
    item = model.model_validate(data)

    assert item.Id == data["Id"]
    assert item.Type == data["Type"]
    assert item.Name == data["Name"]
    assert item.Overview == data["Overview"]
    assert item.ProviderIds == data["ProviderIds"]


@pytest.mark.parametrize(
    ("model", "type_value"), [(MovieItem, "Movie"), (SeriesItem, "Series")]
)
def test_item_optional_fields_default_to_none(model, type_value):
    item = model.model_validate({"Id": "abc123", "Type": type_value})

    assert item.Name is None
    assert item.Overview is None
    assert item.ProviderIds is None


@pytest.mark.parametrize(
    ("model", "type_value"), [(MovieItem, "Movie"), (SeriesItem, "Series")]
)
def test_item_requires_id(model, type_value):
    with pytest.raises(ValidationError):
        model.model_validate({"Type": type_value})


@pytest.mark.parametrize(
    ("model", "wrong_type"),
    [
        (MovieItem, "Series"),
        (MovieItem, "Episode"),
        (SeriesItem, "Movie"),
        (SeriesItem, "Season"),
    ],
)
def test_item_errors_out_on_mismatched_type(model, wrong_type):
    with pytest.raises(ValidationError):
        model.model_validate({"Id": "abc123", "Type": wrong_type})


@pytest.mark.parametrize(
    ("model", "type_value"), [(MovieItem, "Movie"), (SeriesItem, "Series")]
)
def test_item_preserves_extra_fields_on_dump(model: MovieItem, type_value):
    data = {
        "Id": "abc123",
        "Type": type_value,
        "RunTimeTicks": 123456789,
        "ImageTags": {"Primary": "somehash"},
    }

    item = model.model_validate(data)

    dump = item.model_dump()
    assert all(key in dump for key in data.keys())

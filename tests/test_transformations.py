import pytest
from pydantic import ValidationError

from polyfin.transformations import (
    ItemType,
    MovieItem,
    SeriesItem,
    canonicalize_path,
    deconstruct,
    determine_type,
    is_transformable_path,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "/Users/84c1e7a3f5d9026b8e4a1c7d3f6b9e25",
            "/Users/{id}",
        ),
        (
            "/Users/fedcba9876543210fedcba9876543210/Items/"
            "3d8e1f6a9b4c72e5d0f3a8c1b6e94725",
            "/Users/{id}/Items/{id}",
        ),
        (
            "/Items/c5773b1b745d6026a41f2f72c0b86b26/Images/Primary",
            "/Items/{id}/Images/Primary",
        ),
        (
            "/DisplayPreferences/usersettings",
            "/DisplayPreferences/usersettings",
        ),
        (
            "/web/MaterialIcons-Regular.2d8017489da689caedc1.woff2",
            "/web/MaterialIcons-Regular.2d8017489da689caedc1.woff2",
        ),
        (
            "/LiveTv/Programs/Recommended/",
            "/LiveTv/Programs/Recommended",
        ),
    ],
)
def test_normalize_path(path, expected):
    assert canonicalize_path(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "/Shows/NextUp",
        "/Users/c5773b1b745d6026a41f2f72c0b86b26/Items/Resume/",
        "/Items/a7f3c91e5b2d4a6089c1e7f3b5d2a846",
    ],
)
def test_is_transformable_path_returns_true_for_transformable_paths(path):
    assert is_transformable_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "/System/Info/Public",
        "/DisplayPreferences/usersettings",
        "/Items/a7f3c91e5b2d4a6089c1e7f3b5d2a846/something-unsupported",
    ],
)
def test_is_transformable_path_returns_false_for_generic_paths(path):
    assert not is_transformable_path(path)


SAMPLE_ITEM = {"Hello": "World", "How are you?": "..."}


@pytest.mark.parametrize(
    ("data", "expected_item_count", "equality_check"),
    [
        ({"Items": [SAMPLE_ITEM, SAMPLE_ITEM]}, 2, True),
        ([SAMPLE_ITEM, SAMPLE_ITEM], 2, True),
        ([{"Items": []}], 1, False),
        ({"Items": 9}, 1, False),
        ({"Items": []}, 0, True),
        (SAMPLE_ITEM, 1, True),
    ],
)
def test_deconstruct_returns_valid_items(data, expected_item_count, equality_check):
    items = list(deconstruct(data))

    assert len(items) == expected_item_count
    assert all(item is SAMPLE_ITEM for item in items) if equality_check else True


@pytest.mark.parametrize(
    "data",
    [None, [None]],
)
def test_deconstruct_errors_out(data):
    with pytest.raises(ValueError):
        items = list(deconstruct(data))

        pytest.fail(
            f"did not raise. Returned '{items}' of type '{type(items).__name__}'"
        )


@pytest.mark.parametrize(
    ("item", "item_type"),
    [
        ({"Type": "Movie"}, ItemType.Movie),
        ({"Type": "Series"}, ItemType.Series),
        ({"Type": "Season"}, ItemType.Season),
        ({"equals": "="}, None),
    ],
)
def test_determine_type_detects_correctly(item, item_type):
    assert determine_type(item) == item_type


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

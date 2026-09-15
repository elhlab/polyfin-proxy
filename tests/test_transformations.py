import pytest

from polyfin.models import ItemType, MovieMetadata, SeriesItem
from polyfin.transformations import (
    MovieItem,
    Transformer,
    canonicalize_path,
    deconstruct,
    is_transformable_path,
)
from polyfin.utils import determine_type


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
        "/Users/bf54da3305d84c629a94a7d443307508/Items",
        "/Users/9b92122c17a349feb29815bda7b10484/Items/91118c19079849a585b6d71c4ab3709a",
        "/Users/6bad36ab916e4c3db4c7cdf929c390c9/Items/Resume",
        "/Users/671267cfc269409daa4ec4a959d56367/Items/Latest",
        "/Items/b98660b5617a473299ddb504b2814624",
        "/Items/812f0fd4c7ca4429b56cdd8cd5e334d5/Similar",
    ],
)
def test_supported_paths(path):
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


def test_transform_movie_applies_fields_from_metadata():
    item = MovieItem.model_validate(
        {
            "Id": "abc123",
            "Type": "Movie",
            "Name": "Original Name",
            "Overview": "Original overview.",
            "ProviderIds": {"Tmdb": "42"},
            "RunTimeTicks": 123456789,
        }
    )
    metadata = MovieMetadata(name="Translated Name", overview="Translated overview.")
    before = item.model_dump()

    result = Transformer().transform_movie(item, metadata)

    assert result is True
    assert item.Name == metadata.name
    assert item.Overview == metadata.overview

    after = item.model_dump()
    unchanged_keys = [key for key in before if key not in ("Name", "Overview")]
    assert all(after[key] == before[key] for key in unchanged_keys)


@pytest.mark.asyncio
async def test_transform_raises_for_unsupported_item_type():
    item = SeriesItem.model_validate({"Id": "abc123", "Type": "Series"})
    metadata = MovieMetadata(name="Translated Name")

    with pytest.raises(ValueError):
        await Transformer().transform(item, metadata)


@pytest.mark.asyncio
async def test_transform_routes_movie_items_to_transform_movie(monkeypatch):
    item = MovieItem.model_validate({"Id": "abc123", "Type": "Movie"})
    metadata = MovieMetadata(name="Translated Name")
    transformer = Transformer()
    calls = []

    def fake_transform_movie(passed_item, passed_metadata):
        calls.append((passed_item, passed_metadata))
        return True

    monkeypatch.setattr(transformer, "transform_movie", fake_transform_movie)

    result = await transformer.transform(item, metadata)

    assert result is True
    assert calls == [(item, metadata)]


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

from urllib.parse import parse_qs

from starlette.datastructures import URL

from .models import ParsedItem, MovieItem, Metadata, MovieMetadata
from .jellyfin import JellyfinApi

TRANSFORMABLE_PATHS = {
    "/Users/{id}/Items",
    "/Users/{id}/Items/{id}",
    "/Users/{id}/Items/Resume",
    "/Users/{id}/Items/Latest",
    "/Items/{id}",
    "/Items/{id}/Similar",
    # "/Shows/{id}/Episodes",
    # "/Shows/{id}/Seasons",
    # "/Shows/NextUp",
}

HEX_CHARS = set("0123456789abcdef")


def canonicalize_path(path: str) -> str:
    """Replace 32-character hexadecimal path segments with ``{id}`` for easy comparation."""
    return "/" + "/".join(
        (
            "{id}"
            if (len(segment) == 32 and all(c in HEX_CHARS for c in segment.lower()))
            else segment
        )
        for segment in path.strip("/").split("/")
    )


def is_transformable_path(path: str) -> bool:
    return canonicalize_path(path) in TRANSFORMABLE_PATHS


def deconstruct(data: object) -> list[dict]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        raw_items = data.get("Items")
        items = raw_items if isinstance(raw_items, list) else [data]
    else:
        raise ValueError(f"Expected dict or list, got {type(data).__name__}")

    if not all(isinstance(item, dict) for item in items):
        raise ValueError("Expected items to be dictionaries")

    return items


class Transformer:

    def transform_movie(self, item: MovieItem, metadata: MovieMetadata) -> bool:
        """Modififies and `MovieIten` in place with the given metadata"""

        item.Name = metadata.name
        item.Overview = metadata.overview

        return True

    async def transform(self, item: ParsedItem, metadata: Metadata) -> bool:
        """Transforms items found within `value` in place. Caller is responsible for
        resolving `auth`/`locale_id` and for deciding whether to call this at all
        when no locale could be resolved. Returns whether anything was modified."""

        if item.Type == "Movie":
            return self.transform_movie(item, metadata)

        raise ValueError(f"Unexpected item type '{item.Type}'")

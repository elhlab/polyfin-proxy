from typing import Optional

from pydantic import TypeAdapter

from .models import ParsedItem, ItemType, ITEM_TYPES


def determine_type(item: dict) -> Optional[ItemType]:
    item_type = item.get("Type", None)
    if item_type is None:
        return None

    return ITEM_TYPES.get(item_type, None)


def parse_item(data: dict | str) -> ParsedItem:
    """Parses a raw Jellyfin item dict into its typed `Item` variant (`MovieItem`,, ...).
    Raises `pydantic.ValidationError` for unknown/malformed types."""

    if isinstance(data, dict):
        return TypeAdapter(ParsedItem).validate_python(data)

    return TypeAdapter(ParsedItem).validate_json(data)

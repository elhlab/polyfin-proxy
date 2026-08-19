from typing import Optional

from .models import ItemType, ITEM_TYPES


def determine_type(item: dict) -> Optional[ItemType]:
    item_type = item.get("Type", None)
    if item_type is None:
        return None

    return ITEM_TYPES.get(item_type, None)

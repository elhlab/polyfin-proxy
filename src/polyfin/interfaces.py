from dataclasses import dataclass
import enum
from typing import Mapping, Protocol


class ItemType(enum.Enum):
    movie = enum.auto()
    show = enum.auto()
    season = enum.auto()
    episode = enum.auto()


@dataclass(slots=True)
class MetadataLookup:
    item_type: ItemType
    external_ids: Mapping[str, str]


@dataclass(slots=True)
class ItemMetadata:
    name: str
    overview: str | None


class MetadataProvider(Protocol):

    @property
    def id(self) -> str: ...

    async def get_item_data(self, item: MetadataLookup, language: str) -> ItemMetadata:
        """
        Retrieves metadata for the given item.

        Args:
            item (MetadataLookup): Item data used to identify the item and retrieve its metadata.

        Returns:
            ItemMetadata: The item metadata, includes name and overview.
        """
        ...

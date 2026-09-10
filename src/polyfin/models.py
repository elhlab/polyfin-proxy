import enum

from dataclasses import dataclass
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ItemType(enum.Enum):
    Movie = enum.auto()
    Series = enum.auto()
    Season = enum.auto()
    Episode = enum.auto()


ITEM_TYPES = {
    "Movie": ItemType.Movie,
    "Series": ItemType.Series,
    "Season": ItemType.Season,
}


class BaseJellyfinItem(BaseModel):

    model_config = ConfigDict(extra="allow")

    Id: str
    Name: Optional[str] = None
    Overview: Optional[str] = None
    ProviderIds: Optional[dict[str, str]] = None


class MovieItem(BaseJellyfinItem):
    Type: Literal["Movie"]


class SeriesItem(BaseJellyfinItem):
    Type: Literal["Series"]


ParsedItem = Annotated[Union[MovieItem, SeriesItem], Field(discriminator="Type")]


@dataclass(slots=True)
class ResolveableItem:

    item: ParsedItem
    provider_ids: dict[str, str]


class MovieMetadata(BaseModel):
    """Normalized, translated metadata for a movie, as resolved by a MetadataProvider."""

    name: str
    overview: Optional[str] = None


Metadata = Union[MovieMetadata]

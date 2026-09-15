import enum

from dataclasses import dataclass
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ItemType(str, enum.Enum):
    Movie = "Movie"
    Series = "Series"
    Season = "Season"
    Episode = "Episode"


class BaseJellyfinItem(BaseModel):

    model_config = ConfigDict(extra="allow")

    Id: str
    Name: Optional[str] = None
    Overview: Optional[str] = None
    ProviderIds: Optional[dict[str, str]] = None


class MovieItem(BaseJellyfinItem):
    Type: Literal[ItemType.Movie]


class SeriesItem(BaseJellyfinItem):
    Type: Literal[ItemType.Series]


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

from dataclasses import dataclass
import enum
from typing import Generator, Optional
from urllib.parse import parse_qs

from starlette.datastructures import URL
from starlette.requests import Request

from localisation import Localiser

from .jellyfin import Api, MediaBrowserAuth, extract_mediabrowser_auth

TRANSFORMABLE_PATHS = {
    "/Users/{id}/Items",
    "/Users/{id}/Items/{id}",
    "/Users/{id}/Items/Resume",
    "/Users/{id}/Items/Latest",
    "/Items/{id}",
    "/Items/{id}/Similar",
    "/Shows/{id}/Episodes",
    "/Shows/{id}/Seasons",
    "/Shows/NextUp",
}

HEX_CHARS = set("0123456789abcdef")


def normalize_path(path: str) -> str:
    return "/" + "/".join(
        (
            "{id}"
            if (len(segment) == 32 and all(c in HEX_CHARS for c in segment.lower()))
            else segment
        )
        for segment in path.strip("/").split("/")
    )


def is_transformable_path(path: str) -> bool:
    return normalize_path(path) in TRANSFORMABLE_PATHS


def deconstruct(data) -> Generator[dict, None, None]:
    if isinstance(data, dict):
        items = data.get("Items", None)
        if items is not None:
            yield from deconstruct(items)
        else:
            yield data

    elif isinstance(data, list):
        for item in data:
            yield from deconstruct(item)

    else:
        raise ValueError(
            f"Unable to unpack items. Received invalid value '{data}' of type '{type(data)}'"
        )


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


def determine_type(item: dict) -> Optional[ItemType]:
    item_type = item.get("Type", None)
    if item_type is None:
        return None

    return ITEM_TYPES.get(item_type, None)


# def transform_movie(item: dict) -> bool:
#     # Fields to modify:
#     # Name, Overview (if item has Overview present)

#     # TODO: how do we detect the external id to query the data:
#     # ig name (prefer OriginalTitle for queries) and year should be enough but ig if multiple results query for the externals ids based on the jellyfinid
#     # ofcourse first try to resolve on local database via jellyfin id to get data

#     # best probably is to store a mapping in database for jellyfinid to providerids. This could be loaded initially or during loading
#     # the problem with loading them that when you dont have access to providerIds you are quering a list of items so that increases the amount quite heavily to request.

#     # we will just mdoify the fields to inlcude ProviderIds fields always.
#     pass

#     # def modify_fields_query()

#     # def modify_fields_query(params: dict) -> str:
#     pass


# def get_item_provider_ids(item: dict) -> dict[str, str]:
#     provider_ids = item.get("ProviderIds", None)
#     if provider_ids is not None:
#         return provider_ids

#     # title = item.get("OriginalTitle", item.get("Name", None))
#     # year = item.get("ProductionYear", None)

#     # we dont need to figure out the show from our apis. we can just resolve it internally from jellyfin...
#     # its not our problem if a show in jellyfin is missing provider ids that is users fault we will just ignore that item in that case.
#     # TODO: just resolve an item via the itemid where ProviderIds is filled
#     # also this should be called only after the database query fails.


def transform_url(url: URL) -> URL:
    if normalize_path(url.path) == "/Users/{id}/Items":
        parsed_qs = parse_qs(url.query)
        parsed_qs.get("Fields")

        # TODO: add ProviderIds to the fields param to force them to be presetn always
        # idk if this is the smartest way. Ofcourse default to using providerids but there should be a fallback aswell.
        # its probably better to just overwrite this on sepcific endpoints like we are doing right now and then fallback if there is no providerids present


# def transform(value: dict | list[dict]) -> bool:
#     """Modifies a value inplace, returns boolean indicating if modified. Expects a DICT or a LIST of DICT's. Raises ValueError on invalid value"""

#     modified = False
#     for item in deconstruct(value):
#         item_type = determine_type(item)

#         if item_type is None:
#             continue

#         # TODO: what if there are nested things, is the tranformer responsible for that?
#         # Yes it should just call the transform_episode handler yes.
#         item_modified = False
#         if item_type == ItemType.Movie:
#             item_modified = transform_movie(item)

#         if item_modified:
#             modified = True

#     # if isinstance(obj, list):
#     #     mod = False
#     #     for o in obj:
#     #         if transform(o):
#     #             mod = True

#     #     return mod

#     # # TODO: determine dynamically the shape of the item: Series, Season, Episode, Movie.
#     # # determine user locale
#     # # Fetch metadata and modify content

#     # if obj.get("Type") != "Series":
#     #     return False

#     # # obj["Name"] = "Impractical Jokers: Proof Of Consept"
#     return modified


@dataclass(slots=True)
class TransformerCtx:
    request: Request
    item_type: ItemType


class Transformer:

    japi: Api
    localiser: Localiser

    def __init__(self, japi: Api) -> None:
        self.japi = japi

    async def get_provider_ids(
        self, auth: MediaBrowserAuth, item: dict
    ) -> dict[str, str]:

        if "ProviderIds" in item:
            return item["ProviderIds"]

        return await self.japi.fetch_provider_ids(item["Id"], auth)

    def transform_movie(self, item: dict, ids: dict[str, str], locale_id: str) -> bool:
        # Fields to modify:
        # Name, Overview (if item has Overview present)

        # TODO: how do we detect the external id to query the data:
        # ig name (prefer OriginalTitle for queries) and year should be enough but ig if multiple results query for the externals ids based on the jellyfinid
        # ofcourse first try to resolve on local database via jellyfin id to get data

        # best probably is to store a mapping in database for jellyfinid to providerids. This could be loaded initially or during loading
        # the problem with loading them that when you dont have access to providerIds you are quering a list of items so that increases the amount quite heavily to request.

        # we will just mdoify the fields to inlcude ProviderIds fields always.
        pass

        # def modify_fields_query()

        # def modify_fields_query(params: dict) -> str:

    async def transform(self, value: dict | list[dict], request: Request) -> bool:
        """Modifies a value inplace, returns boolean indicating if modified. Expects a DICT or a LIST of DICT's. Raises ValueError on invalid value"""

        auth = extract_mediabrowser_auth(request.headers)
        locale_id = await self.localiser.resolve_locale(
            auth, extract_accepted_locales(request.headers)
        )
        if locale_id is None:
            return False

        modified = False
        for item in deconstruct(value):
            item_type = determine_type(item)

            if item_type is None:
                continue

            provider_ids = await self.get_provider_ids(auth, item)

            item_modified = False
            if item_type == ItemType.Movie:
                item_modified = self.transform_movie(item, provider_ids, locale_id)

            if item_modified:
                modified = True

        # # Fetch metadata and modify content
        return modified

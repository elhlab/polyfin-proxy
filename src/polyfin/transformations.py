from urllib.parse import parse_qs

from starlette.datastructures import URL

from .models import Item, MovieItem, Metadata
from .jellyfin import Api, MediaBrowserAuth
from .localisation import MovieMetadata

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
        if not all(isinstance(item, dict) for item in data):
            raise ValueError("Expected a list of dictionaries")

        return data

    if not isinstance(data, dict):
        raise ValueError(f"Expected dict or list, got {type(data).__name__}")

    items = data.get("Items")
    if not isinstance(items, list):
        return [data]

    if not isinstance(items, list):
        raise ValueError("Expected 'Items' to be a list")

    if not all(isinstance(item, dict) for item in items):
        raise ValueError("Expected 'Items' to contain dictionaries")

    return items


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
    if canonicalize_path(url.path) == "/Users/{id}/Items":
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


class Transformer:

    japi: Api

    def __init__(self, japi: Api) -> None:
        self.japi = japi

    def transform_movie(self, item: MovieItem, metadata: MovieMetadata) -> bool:
        """Modififies and `MovieIten` in place with the given metadata"""

        item.Name = metadata.name
        item.Overview = metadata.overview

        return True

    # def modify_fields_query()

    # def modify_fields_query(params: dict) -> str:

    async def transform(self, item: Item, metadata: Metadata) -> bool:
        """Transforms items found within `value` in place. Caller is responsible for
        resolving `auth`/`locale_id` and for deciding whether to call this at all
        when no locale could be resolved. Returns whether anything was modified."""

        # item_type = determine_type(item)

        # if item_type is None:
        #     continue

        if item.Type == "Movie":
            return self.transform_movie(item, metadata)

        provider_ids = await self.get_provider_ids(auth, item)

        item_modified = False
        if item_type == ItemType.Movie:
            item_modified = self.transform_movie(item, provider_ids, locale_id)

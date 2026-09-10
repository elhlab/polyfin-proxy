import json
import logging
from typing import Protocol

from pydantic import ValidationError
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response, StreamingResponse

from .forwarder import Forwarder, ForwarderBody
from .headers import extract_accepted_locales
from .jellyfin import JellyfinApi, MediaBrowserAuth, extract_mediabrowser_auth
from .localisation import Localiser
from .models import Metadata, MovieItem
from .transformations import (
    Transformer,
    deconstruct,
    is_transformable_path,
    transform_url,
)
from .utils import parse_item

logger = logging.getLogger(__name__)


class MetadataProvider(Protocol):
    """Resolves translated metadata for an item. Not implemented yet -- fetching from
    an external source is a separate, unbuilt piece of work."""

    async def fetch(
        self, item: MovieItem, provider_ids: dict[str, str], locale_id: str
    ) -> Metadata: ...


# TODO: this ai generated processor is good base but not really ideal; fix it
class RequestProcessor:
    """Owns the full lifecycle of a single proxied request: deciding whether to pass
    it through untouched, and if not, resolving the requesting user's locale and
    patching any items in the response body with translated metadata."""

    def __init__(
        self,
        forwarder: Forwarder,
        transformer: Transformer,
        japi: JellyfinApi,
        localiser: Localiser,
        metadata_provider: MetadataProvider,
    ) -> None:
        self.forwarder = forwarder
        self.transformer = transformer
        self.japi = japi
        self.localiser = localiser
        self.metadata_provider = metadata_provider

    async def handle(self, request: StarletteRequest) -> Response | StreamingResponse:
        if not is_transformable_path(request.url.path):
            return await self.forwarder.stream(request)

        async def transform_wrapper(body: ForwarderBody) -> ForwarderBody:
            return await self._transform_body(request, body)

        return await self.forwarder.intercept(
            request, transform_wrapper, transform_url=transform_url
        )

    async def _transform_body(
        self, request: StarletteRequest, body: ForwarderBody
    ) -> ForwarderBody:
        auth = extract_mediabrowser_auth(request.headers)
        accepted_locales = extract_accepted_locales(request.headers)

        locale_id = await self.localiser.resolve_locale(auth, accepted_locales)
        if locale_id is None:
            return body

        data = json.loads(body.content)

        modified = False
        for raw_item in deconstruct(data):
            if await self._transform_item(raw_item, auth, locale_id):
                modified = True

        if not modified:
            return body

        return body.modify(json.dumps(data).encode("utf8"))

    async def _transform_item(
        self, raw_item: dict, auth: MediaBrowserAuth, locale_id: str
    ) -> bool:
        """Patches a single raw item dict in place. Returns whether it was modified.
        Leaves the item untouched for any type/shape we don't handle yet (only Movie,
        for now) rather than failing the whole request."""

        try:
            item = parse_item(raw_item)
        except ValidationError:
            return False

        if not isinstance(item, MovieItem):
            return False

        await self.japi.populate_provider_ids(item, auth)
        if item.ProviderIds is None:
            return False

        metadata = await self.metadata_provider.fetch(item, item.ProviderIds, locale_id)

        if not await self.transformer.transform(item, metadata):
            return False

        raw_item.update(item.model_dump())
        return True

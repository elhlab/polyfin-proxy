import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
import inspect
import logging

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response, StreamingResponse
from starlette.datastructures import Headers, URL as StarletteURL

from .headers import get_interception_headers, get_streaming_headers

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ForwarderBody:
    content: bytes
    content_type: str

    def modify(
        self, content: bytes, content_type: Optional[str] = None
    ) -> "ForwarderBody":
        return ForwarderBody(
            content=content, content_type=content_type or self.content_type
        )


def log_headers(headers: CIMultiDict | CIMultiDictProxy) -> list[tuple[str, str]]:
    return list(headers.items())


class Forwarder:

    baseurl: StarletteURL
    _session: aiohttp.ClientSession

    def __init__(self, url: StarletteURL, session: aiohttp.ClientSession) -> None:
        """Initializes a Forwader. Takes the baseurl of the target url to forward to. A aiohttp CLientSession note it is important that this session does not store cookies."""

        self.baseurl = url
        self._session = session

    async def stream(self, request: StarletteRequest) -> StreamingResponse:
        """Forwards a request to the upstream server and returns a Starlette.StreamingResponse"""

        headers = get_streaming_headers(request.headers)

        url = str(
            request.url.replace(
                scheme=self.baseurl.scheme,
                hostname=self.baseurl.hostname,
                port=self.baseurl.port,
                username=self.baseurl.username,
                password=self.baseurl.password,
            )
        )

        logger.debug(
            "Forwarding streaming request: %s %s headers=%s",
            request.method,
            url,
            log_headers(headers),
        )

        response = await self._session.request(
            request.method,
            url=url,
            headers=headers,
            data=request.stream(),
            allow_redirects=False,
            auto_decompress=False,
        )

        logger.debug(
            "Upstream response: status=%s headers=%s",
            response.status,
            log_headers(response.headers),
        )

        async def reader(response: aiohttp.ClientResponse):
            try:
                async for chunk in response.content.iter_any():
                    yield chunk
            except asyncio.CancelledError:
                logger.info("Downstream cancelled the stream")
            finally:
                response.release()

        return StreamingResponse(
            reader(response),
            status_code=response.status,
            headers=get_streaming_headers(response.headers.copy()),
        )

    async def intercept(
        self,
        request: StarletteRequest,
        transform: Callable[[ForwarderBody], ForwarderBody | Awaitable[ForwarderBody]],
        transform_url: Optional[Callable[[StarletteURL], StarletteURL]] = None,
    ) -> Response:
        """Forwards a request to the upstream and transforms the body with the transform callback. Returns a Starlette.StreamingResponse
        Note the transform function must not modify the content type.
        """

        headers = get_interception_headers(request.headers)

        url = request.url.replace(
            scheme=self.baseurl.scheme,
            hostname=self.baseurl.hostname,
            port=self.baseurl.port,
            username=self.baseurl.username,
            password=self.baseurl.password,
        )

        if transform_url is not None:
            url = transform_url(url)

        logger.debug(
            "Forwarding interception request: %s %s headers=%s",
            request.method,
            url,
            log_headers(headers),
        )

        response = await self._session.request(
            request.method,
            url=str(url),
            headers=headers,
            data=request.stream(),
            allow_redirects=False,
        )

        logger.debug(
            "Upstream response: status=%s headers=%s",
            response.status,
            log_headers(response.headers),
        )

        original_body = ForwarderBody(
            await response.read(), response.headers["Content-Type"]
        )

        transformed_body = transform(original_body)
        if inspect.isawaitable(transformed_body):
            transformed_body = await transformed_body

        headers = get_interception_headers(response.headers.copy())

        # Was the content modified.
        if original_body is not transformed_body:
            # TODO: see about ETags and friends, but I dont see any usage from Jellyfin in our targets. Not a high priority.

            headers["Content-Type"] = transformed_body.content_type

        return Response(
            transformed_body.content,
            status_code=response.status,
            headers=headers,
        )

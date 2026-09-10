import asyncio

from typing import Iterable

import aiohttp
import pytest

from aiohttp import web
from aiohttp.test_utils import TestServer
from aiohttp.web_routedef import AbstractRouteDef
from contextlib import asynccontextmanager
from starlette.datastructures import URL as StarletteURL
from starlette.requests import Request as StarletteRequest

from polyfin.forwarder import Forwarder


def make_request(
    method: str = "GET",
    path: str = "/",
    body: bytes = b"",
) -> StarletteRequest:
    body_sent = False

    async def receive():
        nonlocal body_sent

        if body_sent:
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }

        body_sent = True

        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("localhost", 80),
        "client": ("localhost", 12345),
        "root_path": "",
        "http_version": "1.1",
    }

    return StarletteRequest(scope, receive)


async def read_n(iterator, n):
    result = bytearray()

    async for chunk in iterator:
        result.extend(chunk)

        if len(result) >= n:
            return bytes(result[:n])

    raise AssertionError(
        f"Iterator ended before enough data. Received: {bytes(result)!r}"
    )


@asynccontextmanager
async def create_upstream(routes: Iterable[AbstractRouteDef]):
    app = web.Application()
    app.add_routes(routes)

    server = TestServer(app)
    await server.start_server()

    try:
        yield server
    finally:
        await server.close()


STREAMING_PAYLOADS = {
    "short": b"Hell0, world!",
    "large-binary": bytes(
        (i % 254) + 1 if (i % 254) + 1 != 0x0A else 0xFF for i in range(600_000)
    ),
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", STREAMING_PAYLOADS.values(), ids=STREAMING_PAYLOADS.keys()
)
async def test_streaming_of_arbitrary_paths(payload: bytes):
    """The forwarder must hand data to the client as it arrives from upstream,
    not buffer the whole response first. The upstream handler below writes one
    chunk and then blocks forever, so anything that waits on the response to
    finish before producing bytes will time out rather than fail cleanly."""

    async def stream_handler(request):
        response = web.StreamResponse(status=200)

        await response.prepare(request)

        await response.write(payload)
        await asyncio.Event().wait()

        return response

    routes = [web.get("/arbitrary-path-blah-blah", stream_handler)]

    async with create_upstream(routes) as upstream:
        upstream_url = StarletteURL(str(upstream.make_url("/")))

        async with aiohttp.ClientSession() as session:
            forwarder = Forwarder(upstream_url, session)

            try:
                stream = await asyncio.wait_for(
                    forwarder.stream(make_request("GET", "/arbitrary-path-blah-blah")),
                    timeout=5,
                )
            except asyncio.TimeoutError:
                pytest.fail(
                    "Timeout while waiting for stream. Forwarder may not be streaming properly."
                )

            try:
                chunk = await asyncio.wait_for(
                    read_n(stream.body_iterator, len(payload)), timeout=5
                )
            except asyncio.TimeoutError:
                pytest.fail(
                    "Timeout while reading stream. Forwarder may not be streaming properly."
                )

            assert chunk == payload

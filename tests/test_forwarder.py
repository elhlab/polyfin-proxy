import asyncio

import json
from typing import Iterable

import aiohttp
import pytest

from aiohttp import web
from aiohttp.test_utils import TestServer
from aiohttp.web_routedef import AbstractRouteDef
from contextlib import asynccontextmanager
from starlette.datastructures import URL as StarletteURL
from starlette.requests import Request as StarletteRequest

from polyfin.forwarder import Forwarder, ForwarderBody


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


@pytest.mark.asyncio
async def test_interception():

    async def handler(request):
        return web.Response(status=201, body=b"unmodified", content_type="text/plain")

    routes = [web.get("/intercept-me", handler)]

    async with create_upstream(routes) as upstream:
        upstream_url = StarletteURL(str(upstream.make_url("/")))

        async with aiohttp.ClientSession() as session:
            forwarder = Forwarder(upstream_url, session)

            request = make_request("GET", "/intercept-me")

            async def transform(body: ForwarderBody) -> ForwarderBody:
                return body.modify(b"modified")

            response = await forwarder.intercept(request, transform)

            assert response.status_code == 201
            assert response.headers["content-type"] == "text/plain"
            assert response.body == b"modified"


@pytest.mark.asyncio
async def test_intercept_transform_url():
    async def handler(request):
        return web.json_response(
            {
                "path": request.path,
                "query": request.query_string,
            }
        )

    routes = [web.get("/original", handler), web.get("/transformed", handler)]

    async with create_upstream(routes) as upstream:
        async with aiohttp.ClientSession() as session:
            forwarder = Forwarder(
                StarletteURL(str(upstream.make_url("/"))),
                session,
            )

            def transform_url(url: StarletteURL) -> StarletteURL:
                return url.replace(
                    path="/transformed",
                    query="foo=baz&hello=world",
                )

            response = await forwarder.intercept(
                make_request("GET", "/original?foo=bar"),
                lambda body: body,
                transform_url=transform_url,
            )

            content = response.body
            if isinstance(content, memoryview):
                content = content.tobytes()

            assert json.loads(content) == {
                "path": "/transformed",
                "query": "foo=baz&hello=world",
            }

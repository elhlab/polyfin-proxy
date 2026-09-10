import contextlib
import inspect
import json
import os
from typing import AsyncGenerator, TypedDict, cast
from urllib.parse import parse_qs

import aiohttp
from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from starlette.routing import Route

from polyfin.transformations import is_transformable_path, Transformer
from polyfin.forwarder import Forwarder, ForwarderBody
from polyfin.jellyfin import JellyfinApi
from polyfin.utils import parse_item


class ApplicationState(TypedDict):
    session: aiohttp.ClientSession
    forwarder: Forwarder
    transformer: Transformer


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[ApplicationState]:

    jellyfin_api = JellyfinApi(os.environ["JELLYFIN_URL"])
    async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
        yield {
            "session": session,
            "forwarder": Forwarder(URL(os.environ["JELLYFIN_URL"]), session=session),
            "transformer": Transformer(jellyfin_api),
        }


async def catch_all(request: StarletteRequest[ApplicationState]):
    forwarder = request.state["forwarder"]
    transformer = request.state["transformer"]

    if not is_transformable_path(request.url.path):
        return await forwarder.stream(cast(StarletteRequest, request))

    async def transform_wrapper(body: ForwarderBody) -> ForwarderBody:
        data = json.loads(ForwarderBody.content)

        pitem = parse_item(data)
        metadata = await 
        if await transformer.transform(pitem, metadata):
        #     return body.modify(json.dumps(data).encode("utf8"))

        return body

    print(request.method, request.url)
    return await forwarder.intercept(
        cast(StarletteRequest, request), transform_wrapper, transform_url=transform_url
    )


app = Starlette(
    debug=True,
    lifespan=lifespan,
    routes=[
        Route(
            "/{path:path}",
            catch_all,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        )
    ],
)

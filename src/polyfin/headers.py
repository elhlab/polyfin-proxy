from multidict import CIMultiDict
from starlette.datastructures import Headers


def normalize_headers(headers: Headers | CIMultiDict) -> CIMultiDict:
    if isinstance(headers, CIMultiDict):
        return headers

    return CIMultiDict(
        (key.decode("latin-1"), value.decode("latin-1")) for key, value in headers.raw
    )


def parse_connection_header(value: str) -> list[str]:
    items = value.split(",")

    return [item.strip() for item in items if item.strip()]


HOP_BY_HOP_HEADERS = (
    "Connection",
    "Keep-Alive",
    "Proxy-Authenticate",
    "Proxy-Authorization",
    "TE",
    "Trailer",
    "Transfer-Encoding",
    "Upgrade",
)


def strip_hbp_headers(h: Headers | CIMultiDict) -> CIMultiDict:
    headers = normalize_headers(h)

    while "Connection" in headers:
        conn_headers = parse_connection_header(headers.pop("Connection"))

        for conn_header in conn_headers:
            headers.popall(conn_header, None)

    for conn_header in HOP_BY_HOP_HEADERS:
        headers.popall(conn_header, None)

    return headers


def get_streaming_headers(h: Headers | CIMultiDict) -> CIMultiDict:
    headers = strip_hbp_headers(h)

    if "Host" in headers:
        headers.popall("Host")

    return headers


def get_interception_headers(h: Headers | CIMultiDict) -> CIMultiDict:
    headers = strip_hbp_headers(h)

    STRIPPED_HEADERS = ("Host", "Content-Length", "Content-Encoding", "Accept-Encoding")

    for header in STRIPPED_HEADERS:
        headers.popall(header, None)

    return headers


def extract_accepted_locales(headers: Headers | CIMultiDict) -> list[str]:
    """Parses the Accept-Language header into a list of language tags (eg. "en-US"),
    sorted from most to least preferred per RFC 7231. Ties keep header order."""

    value = normalize_headers(headers).get("Accept-Language")
    if not value:
        return []

    weighted: list[tuple[str, float]] = []
    for part in value.split(","):
        tag, _, params = part.strip().partition(";")
        tag = tag.strip()
        if not tag or tag == "*":
            continue

        quality = 1.0
        for param in params.split(";"):
            param = param.strip()
            if param.startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = 0.0

        weighted.append((tag, quality))

    weighted.sort(key=lambda item: item[1], reverse=True)

    return [tag for tag, _ in weighted]

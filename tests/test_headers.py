import pytest

from multidict import CIMultiDict
from starlette.datastructures import Headers

from polyfin.headers import (
    extract_accepted_locales,
    get_interception_headers,
    get_streaming_headers,
    normalize_headers,
    parse_connection_header,
    strip_hbp_headers,
)


def test_normalize_headers_converts_starlette_headers_to_multidict():
    headers = Headers(raw=[(b"Host", b"example.com"), (b"Accept", b"*/*")])

    normalized = normalize_headers(headers)

    assert isinstance(normalized, CIMultiDict)

    assert normalized["host"] == "example.com"
    assert normalized["hOst"] == "example.com"
    assert normalized["accept"] == "*/*"
    assert normalized["accePt"] == "*/*"


def test_normalize_headers_returns_multidict_unchanged():
    headers = CIMultiDict([("Host", "example.com")])

    assert normalize_headers(headers) is headers


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", []),
        ("close", ["close"]),
        ("keep-alive, Upgrade", ["keep-alive", "Upgrade"]),
        ("  X-Custom ,Y-Custom  ", ["X-Custom", "Y-Custom"]),
    ],
)
def test_parse_connection_header(value, expected):
    assert parse_connection_header(value) == expected


@pytest.mark.parametrize(
    "header",
    [
        "Keep-Alive",
        "Proxy-Authenticate",
        "TE",
        "Trailer",
        "Transfer-Encoding",
        "Upgrade",
    ],
)
def test_strip_hbp_headers_removes_hop_by_hop_headers(header):
    headers = CIMultiDict([(header, "value"), ("Accept", "*/*")])

    result = strip_hbp_headers(headers)

    assert header not in result
    assert result["Accept"] == "*/*"


def test_strip_hbp_headers_removes_headers_named_in_connection():
    headers = CIMultiDict(
        [
            ("Connection", "X-Custom, Y-Custom"),
            ("X-Custom", "1"),
            ("Y-Custom", "2"),
            ("Accept", "*/*"),
        ]
    )

    result = strip_hbp_headers(headers)

    assert "Connection" not in result
    assert "X-Custom" not in result
    assert "Y-Custom" not in result
    assert result["Accept"] == "*/*"


def test_strip_hbp_headers_handles_multiple_connection_headers():
    headers = CIMultiDict(
        [
            ("Connection", "X-Custom"),
            ("Connection", "Y-Custom"),
            ("X-Custom", "1"),
            ("Y-Custom", "2"),
        ]
    )

    result = strip_hbp_headers(headers)

    assert "X-Custom" not in result
    assert "Y-Custom" not in result


def test_get_streaming_headers_drops_host():
    headers = CIMultiDict([("Host", "example.com"), ("Range", "bytes=0-")])

    result = get_streaming_headers(headers)

    assert "Host" not in result
    assert result["Range"] == "bytes=0-"


def test_get_interception_headers_drops_body_and_encoding_headers():
    headers = CIMultiDict(
        [
            ("Host", "example.com"),
            ("Content-Length", "42"),
            ("Content-Encoding", "gzip"),
            ("Accept-Encoding", "gzip"),
            ("Authorization", "Bearer token"),
        ]
    )

    result = get_interception_headers(headers)

    assert list(result.keys()) == ["Authorization"]


def test_extract_accepted_locales_returns_empty_list_when_header_missing():
    headers = Headers(raw=[])

    assert extract_accepted_locales(headers) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fi-FI", ["fi-FI"]),
        ("fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7", ["fi-FI", "fi", "en-US", "en"]),
        ("en;q=0.5,fi;q=0.9", ["fi", "en"]),
        ("fi, en", ["fi", "en"]),
        ("*, fi;q=0.5", ["fi"]),
        ("fi;q=notanumber, en", ["en", "fi"]),
    ],
)
def test_extract_accepted_locales_parses_and_sorts_by_quality(value, expected):
    headers = Headers(raw=[(b"Accept-Language", value.encode("latin-1"))])

    assert extract_accepted_locales(headers) == expected

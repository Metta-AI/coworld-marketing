from __future__ import annotations

import gzip
import json
import os
import zlib
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import unquote, urlparse
from urllib.request import ProxyHandler, Request, build_opener

HTTP_USER_AGENT = "coworld-marketing/0.3.1"


def uri_to_path(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme == "":
        return Path(uri)
    return None


def _opener():
    """Hosted episode pods have no public egress or DNS; declared external reads go through the pod-local
    relay the platform names in COWORLD_EGRESS_RELAY_URL (an explicit HTTP CONNECT proxy). Locally it is unset
    and reads go direct."""
    relay = os.environ.get("COWORLD_EGRESS_RELAY_URL", "").strip()
    if relay:
        return build_opener(ProxyHandler({"http": relay, "https": relay}))
    return build_opener(ProxyHandler({}))


def read_data(uri: str) -> bytes:
    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https"}:
        request = Request(uri, headers={"User-Agent": HTTP_USER_AGENT})
        with _opener().open(request, timeout=60) as response:
            return response.read()
    path = uri_to_path(uri)
    if path is None:
        raise ValueError(f"Unsupported URI for reading: {uri}")
    return path.read_bytes()


def artifact_method(env_var: str) -> Literal["POST", "PUT"]:
    method = os.environ.get(env_var, "PUT").upper()
    if method not in {"POST", "PUT"}:
        raise ValueError(f"{env_var} must be POST or PUT")
    return cast(Literal["POST", "PUT"], method)


def write_data(
    uri: str,
    data: bytes | str,
    *,
    content_type: str,
    http_method: Literal["POST", "PUT"] = "PUT",
) -> None:
    payload = data.encode() if isinstance(data, str) else data
    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https"}:
        request = Request(uri, data=payload, method=http_method)
        request.add_header("Content-Type", content_type)
        request.add_header("User-Agent", HTTP_USER_AGENT)
        with _opener().open(request, timeout=300):
            return
    path = uri_to_path(uri)
    if path is None:
        raise ValueError(f"Unsupported URI for writing: {uri}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def decode_replay_bytes(raw: bytes) -> dict[str, Any]:
    """Replay bytes may arrive raw, gzip- or zlib-compressed; sniff the content, never the suffix."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    elif len(raw) >= 2 and (raw[0] & 0x0F) == 8 and (raw[0] >> 4) <= 7 and ((raw[0] << 8) | raw[1]) % 31 == 0:
        raw = zlib.decompress(raw)
    return json.loads(raw)

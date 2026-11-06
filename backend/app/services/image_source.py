"""Load the bytes of a stored project photo without opening a hole.

Two sources are allowed. A reference that starts with ``/`` is a path inside
the frontend public folder, and it may not escape it. Anything else must be an
http or https address that resolves to a public address, so the endpoint cannot
be used to read the machine or the local network.

Residual risk: the name is resolved once, then httpx connects again, so a
hostile DNS answer could change in between. Blocking every non-public answer
before the request removes the simple cases; a pinned-IP client would remove
the rest and is not worth the code here.
"""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx

MAX_BYTES: int = 5 * 1024 * 1024
TIMEOUT_SECONDS: float = 5.0
ALLOWED_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")


class ImageUnavailable(Exception):
    """The photo cannot be read, or it must not be read."""


def load_image_bytes(reference: str, public_dir: Path) -> bytes:
    """Return the bytes of the photo that ``reference`` points at."""
    candidate = reference.strip()
    if not candidate:
        raise ImageUnavailable("The project has no photo to read")
    if candidate.startswith("/"):
        return _read_local(candidate, public_dir)
    return _read_remote(candidate)


def _read_local(reference: str, public_dir: Path) -> bytes:
    root = public_dir.resolve()
    target = (root / reference.lstrip("/")).resolve()
    if target != root and root not in target.parents:
        raise ImageUnavailable("The photo path leaves the public folder")
    if not target.is_file():
        raise ImageUnavailable("The photo is not in the public folder")
    if target.stat().st_size > MAX_BYTES:
        raise ImageUnavailable("The photo is larger than 5 MB")
    return target.read_bytes()


def _read_remote(reference: str) -> bytes:
    parsed = urlparse(reference)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ImageUnavailable("Only http and https photo addresses are accepted")
    for address in _resolve(parsed.hostname):
        if not _is_public(address):
            raise ImageUnavailable("The photo host is not a public address")

    chunks: list[bytes] = []
    size = 0
    try:
        with httpx.stream(
            "GET", reference, timeout=TIMEOUT_SECONDS, follow_redirects=False
        ) as response:
            if response.status_code != 200:
                raise ImageUnavailable("The photo could not be downloaded")
            content_type = (
                response.headers.get("content-type", "").split(";")[0].strip().lower()
            )
            if content_type not in ALLOWED_TYPES:
                raise ImageUnavailable("The address does not hold an image")
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ImageUnavailable("The photo is larger than 5 MB")
                chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise ImageUnavailable("The photo could not be downloaded") from exc
    return b"".join(chunks)


def _resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ImageUnavailable("The photo host does not resolve") from exc
    return sorted({info[4][0] for info in infos})


def _is_public(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_reserved
        or parsed.is_multicast
        or parsed.is_unspecified
    )
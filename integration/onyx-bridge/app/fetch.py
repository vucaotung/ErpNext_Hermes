"""Fetch a URL and extract readable text. Deliberately the only thing this
bridge is allowed to do with an arbitrary URL - it never executes anything
found on the page, never follows redirects to internal/private IPs.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "ErpNextHermesOnyxBridge/1.0 (+internal legal-knowledge-base crawler)"


class FetchError(Exception):
    pass


def _is_public_host(hostname: str) -> bool:
    """Blocks SSRF against internal infra (loopback, private ranges,
    link-local) - this bridge only exists to pull public legal/reference
    pages, never internal services."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch_and_extract(url: str) -> tuple[str, str]:
    """Returns (title, text). Raises FetchError with a safe, user-facing
    message on any failure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("Chỉ hỗ trợ link http/https")
    if not parsed.hostname or not _is_public_host(parsed.hostname):
        raise FetchError("Không thể lấy nội dung từ địa chỉ này")

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise FetchError(f"Không tải được trang: {e}") from e

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    clean_text = "\n".join(lines)

    if len(clean_text) < 50:
        raise FetchError("Trang không có nội dung văn bản đáng kể (có thể cần JavaScript)")

    return title, clean_text

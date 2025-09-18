# spankbang.py
# ---------------
from __future__ import annotations

import asyncio
import json
import re
from typing import ClassVar, Iterable
from urllib.parse import urlparse, urlunparse

from truelink.exceptions import ExtractionFailedException
from truelink.types import FileItem, FolderResult, LinkResult
from .base import BaseResolver


class SpankBangResolver(BaseResolver):
    """
    Resolver for spankbang domains by scraping the page and extracting `var stream_data`,
    then choosing the best MP4 link in priority 1080p > 720p > 480p. [web:90][web:76]
    """

    DOMAINS: ClassVar[list[str]] = [
        "spankbang.com",
        "spankbang.party",
        "spankbang.video",
        "spankbang.xxx",
        "spankbang.fun",
        "spankbang.cam",
        "spankbang.site",
    ]

    # canonical host to normalize across variants
    CANONICAL_HOST: ClassVar[str] = "spankbang.com"

    # Quality order for selection
    PREFERRED_QUALITIES: ClassVar[list[str]] = ["1080p", "720p", "480p"]

    # Regex patterns to find the JS object assignment in variable contexts [web:90]
    STREAM_BLOCK_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"var\s+stream_data\s*=\s*\{.*?\};", re.I | re.S),
        re.compile(r"window\.stream_data\s*=\s*\{.*?\};", re.I | re.S),
        re.compile(r"\bstream_data\s*=\s*\{.*?\};", re.I | re.S),
    ]

    # Fallback direct URL scraping for typical quality-marked MP4s
    FALLBACK_PATTERNS: ClassVar[dict[str, re.Pattern]] = {
        "1080p": re.compile(r"https?://[^\s\"'<>]+-1080p\.mp4\?[^\s\"'<>]*", re.I),
        "720p": re.compile(r"https?://[^\s\"'<>]+-720p\.mp4\?[^\s\"'<>]*", re.I),
        "480p": re.compile(r"https?://[^\s\"'<>]+-480p\.mp4\?[^\s\"'<>]*", re.I),
    }

    TITLE_RE: ClassVar[re.Pattern] = re.compile(r"<title>\s*(.*?)\s*</title>", re.I | re.S)

    def _normalize_to_canonical(self, original_url: str) -> str:
        """
        Replace supported spankbang domains with the canonical host using netloc only. [web:90]
        """
        p = urlparse(original_url)
        if p.netloc in self.DOMAINS:
            return urlunparse(p._replace(netloc=self.CANONICAL_HOST))
        return original_url

    def _clean_title(self, raw_title: str | None) -> str | None:
        """
        Decode and clean the HTML <title>, removing trailing ' - SpankBang'. [web:90]
        """
        if not raw_title:
            return None
        # Unescape common HTML entities quickly
        txt = raw_title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
        txt = re.sub(r"\s+", " ", txt).strip()
        txt = re.sub(r"\s*-\s*SpankBang\s*$", "", txt, flags=re.I)
        return txt or None

    def _extract_title(self, html: str) -> str | None:
        """
        Extract title from DOM <title> or og:title if present. [web:90]
        """
        # Try <title>
        m = self.TITLE_RE.search(html)
        if m:
            cleaned = self._clean_title(m.group(1))
            if cleaned:
                return cleaned
        # Try og:title meta
        m2 = re.search(r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.I)
        if m2:
            cleaned = self._clean_title(m2.group(1))
            if cleaned:
                return cleaned
        return None

    @staticmethod
    def _strip_trailing_commas(js_obj: str) -> str:
        # Remove trailing commas inside objects/arrays to make it JSONable [web:90]
        return re.sub(r",\s*([}\]])", r"\1", js_obj)

    @staticmethod
    def _single_to_double_quoted_strings(js_obj: str) -> str:
        # Convert single-quoted JS strings to JSON double quoted with escaping
        def repl(m: re.Match) -> str:
            s = m[1]
            s = s.replace('\\"', '"').replace("\\'", "'")
            s = s.replace("\\", "\\\\").replace('"', '\\"')
            return f"\"{s}\""

        return re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", repl, js_obj, flags=re.S)

    @staticmethod
    def _quote_unquoted_keys(js_obj: str) -> str:
        # Turn bare keys like 1080p: or main: into "1080p": / "main":
        return re.sub(r"(\s*)([A-Za-z0-9_]+)\s*:", r'\1"\2":', js_obj)

    def _js_object_to_json(self, js_obj: str) -> str:
        """
        Convert a JS object literal into JSON string so json.loads can parse. [web:90]
        """
        s = self._strip_trailing_commas(js_obj)
        s = self._single_to_double_quoted_strings(s)
        s = self._quote_unquoted_keys(s)
        return s

    def _find_stream_block(self, html: str) -> str | None:
        """
        Find the raw JS assignment text containing stream_data. [web:90]
        """
        for pat in self.STREAM_BLOCK_PATTERNS:
            if m := pat.search(html):
                return m.group(0)
        return None

    def _extract_stream_dict(self, html: str) -> dict | None:
        """
        Extract and JSON-decode the stream_data object from the page. [web:90]
        """
        MAX_HTML_SIZE = 2 * 1024 * 1024  # 2MB limit
        if len(html) > MAX_HTML_SIZE:
            # Optionally, log a warning here
            return None
        block = self._find_stream_block(html)
        if not block:
            return None
        # Keep from first '{' to last '}' inclusive
        obj_body = re.sub(r"^[^{]*\{", "{", block, flags=re.S)
        obj_body = re.sub(r";\s*$", "", obj_body.strip())
        json_like = self._js_object_to_json(obj_body)
        try:
            data = json.loads(json_like)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    def _fallback_find_by_quality(self, html: str) -> dict[str, list[str]]:
        """
        Fallback: scrape quality-specific direct URLs via regex if JSON decode fails. [web:90]
        """
        found: dict[str, list[str]] = {}
        for q, pat in self.FALLBACK_PATTERNS.items():
            if matches := pat.findall(html) or []:
                found[q] = matches
        return found

    @staticmethod
    def _first_str(it: Iterable[str] | None) -> str | None:
        if not it:
            return None
        return next((x for x in it if isinstance(x, str) and x), None)

    def _choose_best_url(self, data: dict | None, fallback: dict[str, list[str]]) -> str | None:
        """
        Prefer 1080p > 720p > 480p using JSON data arrays first, then fallback regex matches. [web:90]
        """
        if isinstance(data, dict):
            for q in self.PREFERRED_QUALITIES:
                v = data.get(q)
                if isinstance(v, list) and v:
                    u = self._first_str(v)
                    if u:
                        return u
            # Some pages include "main" array
            main = data.get("main")
            if isinstance(main, list) and main:
                u = self._first_str(main)
                if u:
                    return u
        # Fallback matches from HTML
        for q in self.PREFERRED_QUALITIES:
            arr = fallback.get(q)
            if arr:
                return arr[0]
        return None

    @staticmethod
    def _maybe_add_extension(name: str | None, url: str | None) -> str | None:
        if not name:
            return None
        if not url:
            return name
        # infer extension from URL path
        path = urlparse(url).path.lower()
        m = re.search(r"\.(mp4|mkv|webm)$", path, re.I)
        if m and not re.search(r"\.(mp4|mkv|webm)$", name, re.I):
            return f"{name}.{m[1].lower()}"
        return name

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        # Normalize host if matches our set
        target = self._normalize_to_canonical(url)  # netloc-based canonicalization [web:90]

        # Fetch page via BaseResolver helper; set a desktop UA in BaseResolver if needed [web:83][web:93]
        try:
            async with await self._get(target, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ExtractionFailedException(
                        f"HTTP {resp.status} fetching page: {text[:200]}"
                    )
                html = await resp.text()
        except Exception as e:
            raise ExtractionFailedException(f"Failed to fetch page: {e}") from e

        # Extract title -> filename
        filename = self._extract_title(html)
        if not filename:
            # Try to extract a unique identifier from the URL
            from urllib.parse import urlparse
            url_parts = urlparse(url)
            # Use last path segment as identifier, fallback to 'video'
            unique_id = url_parts.path.rstrip('/').split('/')[-1] or "video"
            filename = f"video_{unique_id}"

        # Parse stream_data JSON
        data = self._extract_stream_dict(html)

        # Fallback direct scrape for typical quality URLs
        fallback = {} if data else self._fallback_find_by_quality(html)

        # Choose best quality link
        best_url = self._choose_best_url(data, fallback)
        if not best_url:
            raise ExtractionFailedException("Could not extract a playable quality link")

        # Append extension if needed based on URL path
        final_name = self._maybe_add_extension(filename, best_url) or filename

        # Infer MIME type from extension
        import mimetypes
        mime_type, _ = mimetypes.guess_type(final_name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        return LinkResult(
            url=best_url,
            filename=final_name,
            mime_type=mime_type,
            size=None,
        )

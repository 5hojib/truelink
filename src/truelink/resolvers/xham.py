# xham.py
# ---------------
from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse, urlunparse
from os.path import basename

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class XhamResolver(BaseResolver):
    """Resolver for xhamster variants via vidquickly API,
    normalizing host to xhamster1.desi before processing.
    """

    DOMAINS: ClassVar[list[str]] = [
        "xhamster.com",
        "xhamster19.com",
        "xhamster1.desi",
        "xhamster2.com",
        "xhaccess.com",
    ]

    API_URL: ClassVar[str] = (
        "https://vidquickly.com/api/v1/xhamster-get-link?url="
    )

    CANONICAL_HOST: ClassVar[str] = "xhamster1.desi"

    def _normalize_to_canonical(self, original_url: str) -> str:
        """Replace supported domains with xhamster1.desi using netloc only."""
        parsed = urlparse(original_url)

        to_replace = {
            "xhamster.com",
            "xhamster19.com",
            "xhamster1.desi",
            "xhamster2.com",
            "xhaccess.com",
        }

        if parsed.netloc in to_replace:
            replaced = parsed._replace(netloc=self.CANONICAL_HOST)
            return urlunparse(replaced)

        return original_url

    def _extract_quality(self, title: str) -> int:
        """Extract numeric quality from title like 'Video 720p'."""
        match = re.search(r"(\d+)", title or "")
        return int(match.group(1)) if match else 0

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        canonical_url = self._normalize_to_canonical(url)

        api_url = self.API_URL + canonical_url

        try:
            async with await self._get(api_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExtractionFailedException(
                        f"vidquickly API error ({response.status}): {error_text[:200]}"
                    )

                try:
                    data = await response.json()
                except Exception as e:
                    snippet = await response.text()
                    raise ExtractionFailedException(
                        f"Failed to parse JSON: {e} - Response: {snippet[:200]}"
                    ) from e

            links = data.get("links", [])

            if not isinstance(links, list) or not links:
                raise ExtractionFailedException("No direct MP4 links found")

            # 🔥 Select best quality (highest resolution)
            best = max(
                links,
                key=lambda x: self._extract_quality(x.get("title", "")),
            )

            link_url = best.get("url")
            if not link_url:
                raise ExtractionFailedException("Selected link has no URL")

            # Filename from URL or videoDetails title
            filename = None
            video_details = data.get("videoDetails", {})
            title = video_details.get("title")

            if title:
                safe_title = re.sub(r"[^\w\-_. ]", "", title)
                filename = f"{safe_title}.mp4"
            else:
                filename = basename(urlparse(link_url).path)

            mime_type = "video/mp4"
            size = None  # API does not provide size

            return LinkResult(
                url=link_url,
                filename=filename,
                mime_type=mime_type,
                size=size,
            )

        except Exception as e:
            raise ExtractionFailedException(
                f"Failed to resolve domain URL: {e}"
            ) from e

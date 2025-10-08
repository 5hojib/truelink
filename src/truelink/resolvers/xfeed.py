from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException
from truelink.types import LinkResult

from .base import BaseResolver


class XfeedResolver(BaseResolver):
    DOMAINS: ClassVar[list[str]] = ["xfeed.com", "www.xfeed.com"]

    async def resolve(self, url: str) -> LinkResult:
        async with await self._get(
            url,
            headers={"Referer": "https://xfeed.com/", "User-Agent": "Mozilla/5.0"},
        ) as r:
            if r.status != 200:
                msg = f"Xfeed HTTP {r.status}"
                raise ExtractionFailedException(msg)
            html = await r.text()

        # Search for .mp4 URL pattern in the page
        mp4_match = re.search(r'd_url:\s*["\']([^"\']*\.mp4)["\']', html)
        if not mp4_match:
            # Fallback: search for any .mp4 path
            mp4_match = re.search(r'["\']([^"\']*\.mp4)["\']', html)

        if not mp4_match:
            msg = "Xfeed: .mp4 URL not found"
            raise ExtractionFailedException(msg)

        d_url = mp4_match.group(1)

        # If it's already a full URL, use it directly
        if d_url.startswith("http"):
            mp4_url = d_url
        else:
            # If it's a path, construct the full URL
            if not d_url.startswith("/"):
                d_url = "/" + d_url

            # Get host from EMBED_URL or use default
            host = "vxf3d.cachefly.net"  # default
            embed_match = re.search(
                r'window\.EMBED_URL\s*=\s*["\']([^"\']+)["\']', html
            )
            if embed_match:
                host = urlparse(embed_match.group(1)).netloc

            mp4_url = f"https://{host}{d_url}"

        filename, size, mime = await self._fetch_file_details(mp4_url)
        return LinkResult(url=mp4_url, filename=filename, mime_type=mime, size=size)

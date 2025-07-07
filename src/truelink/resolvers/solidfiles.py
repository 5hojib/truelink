from __future__ import annotations

import json
import re

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class SolidFilesResolver(BaseResolver):
    """Resolver for SolidFiles.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve SolidFiles.com URL"""
        try:
            # SolidFiles sometimes requires a specific User-Agent.
            # BaseResolver's USER_AGENT should be sufficient, but if issues arise,
            # the original User-Agent was:
            # "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36"
            # We'll use the one from BaseResolver for consistency for now.
            headers = {
                # "User-Agent": self.USER_AGENT (already set by BaseResolver's session)
            }
            async with await self._get(url, headers=headers) as response:
                page_source = await response.text()

            # Original regex: r"viewerOptions\'\,\ (.*?)\)\;"
            # This extracts a JSON-like object string.
            match = re.search(
                r"viewerOptions['\"]?\s*,\s*(\{.*?\})\s*\)\s*;",
                page_source,
                re.DOTALL | re.IGNORECASE,
            )
            if not match:
                # Fallback: Try to find a download button or link directly if viewerOptions isn't there
                # This is a guess, as SolidFiles structure might vary.
                # Example: <a href="some_download_link" class="button">Download</a>
                from lxml.html import fromstring  # Local import if only used here

                html = fromstring(page_source)
                # Look for common download button patterns
                dl_links = html.xpath(
                    '//a[contains(translate(@href, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "solidfilesusercontent.com")]/@href',
                )
                if not dl_links:
                    dl_links = html.xpath(
                        '//a[contains(@class, "download-button") or contains(@id, "download-button")]/@href',
                    )

                if dl_links:
                    direct_link = dl_links[0]
                    if not direct_link.startswith("http"):  # If relative path
                        from urllib.parse import urljoin

                        direct_link = urljoin(url, direct_link)

                    filename_from_page_title = html.xpath("//title/text()")
                    filename_guess = (
                        filename_from_page_title[0]
                        .replace("SolidFiles - ", "")
                        .strip()
                        if filename_from_page_title
                        else None
                    )

                    filename, size = await self._fetch_file_details(direct_link)
                    return LinkResult(
                        url=direct_link,
                        filename=filename if filename else filename_guess,
                        size=size,
                    )

                raise ExtractionFailedException(
                    "SolidFiles error: Could not find 'viewerOptions' or a fallback download link in page source.",
                )

            options_json_str = match.group(1)

            try:
                # The extracted string might not be perfect JSON (e.g. trailing commas, single quotes)
                # Try to clean it up or use a more lenient JSON parser if needed.
                # For now, standard json.loads
                options_data = json.loads(options_json_str)
            except json.JSONDecodeError as json_err:
                raise ExtractionFailedException(
                    f"SolidFiles error: Failed to parse viewerOptions JSON. Content: {options_json_str[:200]}. Error: {json_err}",
                ) from json_err

            if "downloadUrl" not in options_data:
                raise ExtractionFailedException(
                    "SolidFiles error: 'downloadUrl' not found in viewerOptions data.",
                )

            direct_link = options_data["downloadUrl"]

            # Filename might be in viewerOptions too, e.g., options_data.get('nodeName') or options_data.get('name')
            filename_from_options = options_data.get("nodeName") or options_data.get(
                "name",
            )

            filename, size = await self._fetch_file_details(direct_link)

            return LinkResult(
                url=direct_link,
                filename=filename if filename else filename_from_options,
                size=size,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve SolidFiles.com URL '{url}': {e!s}",
            ) from e

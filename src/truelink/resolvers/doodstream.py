from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# todo
class DoodStreamResolver(BaseResolver):
    """Resolver for DoodStream URLs (dood.watch, dood.to, etc.)"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve DoodStream URL"""
        try:
            parsed_url = urlparse(url)

            if "/e/" in parsed_url.path:
                page_url_str = url.replace("/e/", "/d/")
            else:
                page_url_str = url

            async with await self._get(page_url_str) as page_response:
                page_html_text = await page_response.text()

            html = fromstring(page_html_text)

            intermediate_link_elements = html.xpath(
                "//div[contains(@class,'download-content')]//a/@href",
            )
            if not intermediate_link_elements:
                intermediate_link_elements = html.xpath(
                    "//a[contains(@class,'btn-download') or contains(@class,'download_button')]/@href",
                )
                if not intermediate_link_elements:
                    if (
                        "File not found" in page_html_text
                        or "File has been removed" in page_html_text
                    ):
                        raise ExtractionFailedException(
                            "DoodStream error: File not found or removed.",
                        )
                    raise ExtractionFailedException(
                        "DoodStream error: Could not find the intermediate download link on the page.",
                    )

            intermediate_path = intermediate_link_elements[0]

            if intermediate_path.startswith("//"):
                intermediate_url = f"{parsed_url.scheme}:{intermediate_path}"
            elif intermediate_path.startswith("/"):
                intermediate_url = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}{intermediate_path}"
                )
            else:
                intermediate_url = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}/{intermediate_path}"
                )

            await asyncio.sleep(2)

            headers_intermediate = {"Referer": page_url_str}
            async with await self._get(
                intermediate_url,
                headers=headers_intermediate,
            ) as intermediate_response:
                intermediate_page_text = await intermediate_response.text()

            final_link_match = re.search(
                r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]",
                intermediate_page_text,
            )
            if not final_link_match:
                if "Error generating download link" in intermediate_page_text:
                    raise ExtractionFailedException(
                        "DoodStream error: Server reported an error generating the download link.",
                    )
                raise ExtractionFailedException(
                    "DoodStream error: Could not find final download link pattern (window.open) on intermediate page.",
                )

            direct_link = final_link_match.group(1)

            if not direct_link.startswith("http"):
                raise ExtractionFailedException(
                    f"DoodStream error: Extracted final link is not absolute: {direct_link}",
                )

            fetch_referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            filename, size, _ = await self._fetch_file_details(
                direct_link,
                headers={"Referer": fetch_referer},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve DoodStream URL '{url}': {e!s}",
            ) from e

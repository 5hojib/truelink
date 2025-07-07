from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class DoodStreamResolver(BaseResolver):
    """Resolver for DoodStream URLs (dood.watch, dood.to, etc.)"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve DoodStream URL"""
        try:
            parsed_url = urlparse(url)

            # Normalize URL: /e/ (embed) links should be changed to /d/ (download page)
            # as the download preparation script is usually on the /d/ page.
            if "/e/" in parsed_url.path:
                page_url_str = url.replace("/e/", "/d/")
                # Re-parse if changed
                # parsed_url = urlparse(page_url_str) # Not strictly needed again if only path changed
            else:
                page_url_str = url

            # Fetch the download page
            async with await self._get(page_url_str) as page_response:
                page_html_text = await page_response.text()

            html = fromstring(page_html_text)

            # DoodStream often has a button/link that leads to an intermediate page or triggers JS.
            # Original XPath: //div[@class='download-content']//a/@href
            # This usually gets a relative path like '/download/xxxxxxx'
            intermediate_link_elements = html.xpath(
                "//div[contains(@class,'download-content')]//a/@href",
            )
            if not intermediate_link_elements:
                # Fallback: check for other common patterns if 'download-content' changed
                intermediate_link_elements = html.xpath(
                    "//a[contains(@class,'btn-download') or contains(@class,'download_button')]/@href",
                )
                if not intermediate_link_elements:
                    # Check if page content indicates an error (e.g., "File not found", "DMCA")
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

            # Construct full intermediate URL
            if intermediate_path.startswith("//"):
                intermediate_url = f"{parsed_url.scheme}:{intermediate_path}"
            elif intermediate_path.startswith("/"):
                intermediate_url = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}{intermediate_path}"
                )
            else:  # Should be a relative path starting with /
                intermediate_url = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}/{intermediate_path}"
                )

            # Wait for a bit as per original script (sleep(2))
            await asyncio.sleep(2)

            # Fetch the intermediate page content (this page usually contains the window.open script)
            # The referer for this GET should be the initial page_url_str
            headers_intermediate = {"Referer": page_url_str}
            async with await self._get(
                intermediate_url,
                headers=headers_intermediate,
            ) as intermediate_response:
                intermediate_page_text = await intermediate_response.text()

            # Regex from original: search(r"window\.open\('(\S+)'", _res.text)
            # This looks for JavaScript `window.open('DIRECT_LINK_HERE', ...)`
            final_link_match = re.search(
                r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]",
                intermediate_page_text,
            )
            if not final_link_match:
                # If window.open not found, DoodStream might have changed its method.
                # Look for alternative patterns if possible or common error messages.
                if "Error generating download link" in intermediate_page_text:
                    raise ExtractionFailedException(
                        "DoodStream error: Server reported an error generating the download link.",
                    )
                raise ExtractionFailedException(
                    "DoodStream error: Could not find final download link pattern (window.open) on intermediate page.",
                )

            direct_link = final_link_match.group(1)

            # The direct_link should be absolute. If not, it's an issue.
            if not direct_link.startswith("http"):
                raise ExtractionFailedException(
                    f"DoodStream error: Extracted final link is not absolute: {direct_link}",
                )

            # Referer for _fetch_file_details: original script used parsed_url.scheme + hostname
            # This should be the domain of the DoodStream site we are on.
            fetch_referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": fetch_referer},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve DoodStream URL '{url}': {e!s}",
            ) from e

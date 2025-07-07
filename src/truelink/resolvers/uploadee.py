from __future__ import annotations

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class UploadEeResolver(BaseResolver):
    """Resolver for Upload.ee URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Upload.ee URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            html = fromstring(response_text)

            # Original XPath: //a[@id='d_l']/@href
            direct_link_elements = html.xpath("//a[@id='d_l']/@href")

            if not direct_link_elements:
                # Fallback: Upload.ee might have changed its structure.
                # Look for other common download button patterns.
                # Example: <a ... class="...download..." href="...">
                # This is a guess and might need refinement based on actual page structure.
                fallback_links = html.xpath(
                    "//a[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download') and @href]/@href",
                )
                if not fallback_links:
                    # Check for error messages on page
                    error_messages = html.xpath(
                        "//div[contains(@class, 'alert-danger')]/text() | //div[contains(@class, 'error')]/text()",
                    )
                    if error_messages:
                        raise ExtractionFailedException(
                            f"Upload.ee error: {error_messages[0].strip()}",
                        )
                    if (
                        "File not found" in response_text
                        or "File has been deleted" in response_text
                    ):
                        raise ExtractionFailedException(
                            "Upload.ee error: File not found or has been deleted.",
                        )
                    raise ExtractionFailedException(
                        "Upload.ee error: Direct download link element (id='d_l' or fallback) not found.",
                    )

                direct_link = fallback_links[0]
            else:
                direct_link = direct_link_elements[0]

            # The link from Upload.ee is usually direct.
            # Using the original URL as referer for fetching details, just in case.
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Upload.ee URL '{url}': {e!s}",
            ) from e

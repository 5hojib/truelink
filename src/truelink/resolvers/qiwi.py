from __future__ import annotations

from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class QiwiResolver(BaseResolver):
    """Resolver for Qiwi.gg URLs"""

    # Note: The resolver constructs a link using "spyderrock.com".
    # This is an external domain dependency that might change.

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Qiwi.gg URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if not path_segments:
                raise InvalidURLException(
                    "Qiwi.gg error: Could not extract file ID from URL (empty path).",
                )

            file_id = path_segments[
                -1
            ]  # Assume file ID is the last part of the path

            # Fetch the Qiwi.gg page to extract filename and extension
            async with await self._get(url) as response:
                page_html_text = await response.text()

            html = fromstring(page_html_text)

            # XPath from original: //h1[@class="page_TextHeading__VsM7r"]/text()
            # This class name might change. Let's try a more robust XPath if possible,
            # e.g., looking for h1 containing the filename.
            # For now, sticking to the original.
            filename_elements = html.xpath(
                '//h1[contains(@class,"TextHeading")]/text()',
            )  # Made class check more general

            if not filename_elements:
                # Fallback: try to find filename in <title> tag
                title_text = html.xpath("//title/text()")
                if title_text and title_text[0].strip():
                    # Title often is "filename - qiwi.gg" or similar
                    # This is a guess, actual title format may vary.
                    potential_filename_from_title = (
                        title_text[0].split(" - ")[0].strip()
                    )
                    if (
                        "." in potential_filename_from_title
                    ):  # Check if it looks like a filename with extension
                        filename_elements = [potential_filename_from_title]

                if not filename_elements:
                    # Check for common error messages if filename element is not found
                    if (
                        "File not found" in page_html_text
                        or "This file does not exist" in page_html_text
                    ):
                        raise ExtractionFailedException(
                            "Qiwi.gg error: File not found on page.",
                        )
                    raise ExtractionFailedException(
                        "Qiwi.gg error: Could not find filename element on page to determine extension.",
                    )

            full_filename = filename_elements[0].strip()
            if not full_filename or "." not in full_filename:
                raise ExtractionFailedException(
                    f"Qiwi.gg error: Extracted filename '{full_filename}' is invalid or missing extension.",
                )

            # Original logic: ext = name[0].split(".")[-1]
            # This assumes filename_elements[0] is the filename.
            file_extension = full_filename.split(".")[-1]
            if not file_extension:  # Should not happen if previous check passed
                raise ExtractionFailedException(
                    f"Qiwi.gg error: Could not determine file extension from '{full_filename}'.",
                )

            # Construct the direct link using spyderrock.com
            direct_link = f"https://spyderrock.com/{file_id}.{file_extension}"

            # Fetch details for the spyderrock link
            # The referer might be important. Using the original qiwi.gg URL.
            filename_from_details, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            # Use filename from page if Content-Disposition doesn't provide a better one.
            # full_filename already includes the extension.
            final_filename = (
                filename_from_details if filename_from_details else full_filename
            )

            return LinkResult(url=direct_link, filename=final_filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Qiwi.gg URL '{url}': {e!s}",
            ) from e

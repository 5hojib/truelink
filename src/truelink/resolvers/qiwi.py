from __future__ import annotations

from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class QiwiResolver(BaseResolver):
    """Resolver for Qiwi.gg URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Qiwi.gg URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if not path_segments:
                raise InvalidURLException(
                    "Qiwi.gg error: Could not extract file ID from URL (empty path).",
                )

            file_id = path_segments[-1]

            async with await self._get(url) as response:
                page_html_text = await response.text()

            html = fromstring(page_html_text)

            filename_elements = html.xpath(
                '//h1[contains(@class,"TextHeading")]/text()',
            )

            if not filename_elements:
                title_text = html.xpath("//title/text()")
                if title_text and title_text[0].strip():
                    potential_filename_from_title = (
                        title_text[0].split(" - ")[0].strip()
                    )
                    if "." in potential_filename_from_title:
                        filename_elements = [potential_filename_from_title]

                if not filename_elements:
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

            file_extension = full_filename.split(".")[-1]
            if not file_extension:
                raise ExtractionFailedException(
                    f"Qiwi.gg error: Could not determine file extension from '{full_filename}'.",
                )

            direct_link = f"https://spyderrock.com/{file_id}.{file_extension}"

            filename_from_details, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

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

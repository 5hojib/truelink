from __future__ import annotations

from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class RacatyResolver(BaseResolver):
    """Resolver for Racaty.net URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Racaty.net URL"""
        try:
            # Follow initial redirects to get the canonical URL
            async with await self._get(url) as initial_response:
                canonical_url = str(initial_response.url)

            parsed_url = urlparse(canonical_url)
            path_segments = parsed_url.path.split("/")
            file_id = None
            if path_segments:
                file_id = path_segments[-1]  # Assumes ID is the last part

            if not file_id:
                raise InvalidURLException(
                    f"Could not extract file ID from Racaty URL: {canonical_url}",
                )

            post_data = {"op": "download2", "id": file_id}

            # POST to the canonical URL
            async with await self._post(
                canonical_url,
                data=post_data,
            ) as post_response:
                response_text = await post_response.text()

            html = fromstring(response_text)

            direct_link_elements = html.xpath("//a[@id='uniqueExpirylink']/@href")

            if not direct_link_elements:
                # Check for error messages if link not found
                error_msg = html.xpath(
                    "//div[contains(@class,'alert-danger')]/text()",
                )
                if error_msg:
                    raise ExtractionFailedException(
                        f"Racaty error: {error_msg[0].strip()}",
                    )

                # Check for common messages like "File not found"
                if (
                    "File Not Found" in response_text
                    or "No such file" in response_text
                ):
                    raise ExtractionFailedException(
                        f"Racaty error: File Not Found or link expired for ID {file_id}.",
                    )

                raise ExtractionFailedException(
                    "Racaty error: Direct download link ('uniqueExpirylink') not found.",
                )

            direct_link = direct_link_elements[0]

            # Racaty links might be direct or might need a referer.
            # Using the canonical_url as referer for fetching details.
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": canonical_url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Racaty.net URL '{url}': {e!s}",
            ) from e

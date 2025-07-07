from __future__ import annotations

from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class AkmFilesResolver(BaseResolver):
    """Resolver for AkmFiles.com / AkmFls.xyz URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve AkmFiles URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = parsed_url.path.split("/")
            file_id = None
            if path_segments:
                file_id = path_segments[-1]  # Assumes ID is the last part

            if not file_id:
                raise InvalidURLException(
                    f"Could not extract file ID from AkmFiles URL: {url}",
                )

            post_data = {"op": "download2", "id": file_id}

            # POST to the original URL
            # AkmFiles might require specific headers, e.g. Referer.
            # For now, assume default headers from BaseResolver are okay.
            async with await self._post(url, data=post_data) as post_response:
                response_text = await post_response.text()

            html = fromstring(response_text)

            # Original XPath: //a[contains(@class,'btn btn-dow')]/@href
            direct_link_elements = html.xpath(
                "//a[contains(@class,'btn-dow') or contains(@class,'btn-download')]/@href",
            )

            if not direct_link_elements:
                # Check for common error messages if link not found
                error_msg = html.xpath(
                    "//div[contains(@class,'alert-danger')]/text()",
                )
                if error_msg:
                    raise ExtractionFailedException(
                        f"AkmFiles error: {error_msg[0].strip()}",
                    )

                if (
                    "File Not Found" in response_text
                    or "No such file" in response_text
                ):
                    raise ExtractionFailedException(
                        f"AkmFiles error: File Not Found or link expired for ID {file_id}.",
                    )

                raise ExtractionFailedException(
                    "AkmFiles error: Direct download link not found on page.",
                )

            direct_link = direct_link_elements[0]

            # Ensure the link is absolute
            if direct_link.startswith("//"):
                direct_link = f"{parsed_url.scheme}:{direct_link}"
            elif direct_link.startswith("/"):
                direct_link = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}{direct_link}"
                )
            elif not direct_link.startswith("http"):
                from urllib.parse import urljoin

                direct_link = urljoin(url, direct_link)

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve AkmFiles URL '{url}': {e!s}",
            ) from e

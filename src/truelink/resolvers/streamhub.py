from __future__ import annotations

import asyncio
from urllib.parse import urljoin, urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class StreamHubResolver(BaseResolver):
    """Resolver for StreamHub.ink / StreamHub.to URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve StreamHub URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if not path_segments:
                raise InvalidURLException(
                    "StreamHub: Invalid URL, no path segments found.",
                )

            # Assume file code is the last part of the path
            file_code = path_segments[-1]

            # Normalize URL to the /d/ format, as per original script
            download_page_url = (
                f"{parsed_url.scheme}://{parsed_url.netloc}/d/{file_code}"
            )

            # First GET to fetch the page with the form
            async with await self._get(download_page_url) as page_response:
                page_html_text = await page_response.text()
            html = fromstring(page_html_text)

            # Extract form data
            # Original XPath: //form[@name="F1"]//input
            form_inputs = html.xpath('//form[@name="F1"]//input')
            if not form_inputs:
                # Fallback: Try a more generic form search if 'F1' changes
                form_inputs = html.xpath(
                    '//form[contains(@action, "/d/")]//input | //form[button/@type="submit"]//input',
                )
                if not form_inputs:
                    # Check for error messages if form not found
                    error_div = html.xpath(
                        '//div[contains(@class, "alert-danger")]/text()',
                    )  # More generic error check
                    if error_div:  # Get all text from error div
                        error_message = "".join(error_div).strip()
                        raise ExtractionFailedException(
                            f"StreamHub error (page): {error_message}",
                        )
                    if "File not found" in page_html_text:
                        raise ExtractionFailedException(
                            "StreamHub error: File not found.",
                        )
                    raise ExtractionFailedException(
                        "StreamHub error: Download form inputs not found on page.",
                    )

            post_data = {}
            for i in form_inputs:
                name = i.get("name")
                value = i.get("value")
                if name:  # Ensure name exists
                    post_data[name] = value if value is not None else ""

            # Add referer for the POST request
            post_headers = {"Referer": download_page_url}

            # Original script: sleep(1)
            await asyncio.sleep(1)

            # POST the form data to the same download_page_url
            async with await self._post(
                download_page_url,
                data=post_data,
                headers=post_headers,
            ) as post_response:
                post_response_text = await post_response.text()

            post_html = fromstring(post_response_text)

            # Extract direct link
            # Original XPath: //a[@class="btn btn-primary btn-go downloadbtn"]/@href
            direct_link_elements = post_html.xpath(
                '//a[contains(@class,"downloadbtn")]/@href',
            )
            if not direct_link_elements:
                # Check for error messages after POST
                error_div_post = post_html.xpath(
                    '//div[contains(@class, "alert-danger")]/text()',
                )
                if error_div_post:
                    error_message_post = "".join(error_div_post).strip()
                    raise ExtractionFailedException(
                        f"StreamHub error (after POST): {error_message_post}",
                    )
                raise ExtractionFailedException(
                    "StreamHub error: Direct download button/link not found after POST.",
                )

            direct_link = direct_link_elements[0]

            # Ensure link is absolute
            if not direct_link.startswith("http"):
                direct_link = urljoin(
                    download_page_url,
                    direct_link,
                )  # Use download_page_url as base

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": download_page_url},
            )
            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve StreamHub URL '{url}': {e!s}",
            ) from e

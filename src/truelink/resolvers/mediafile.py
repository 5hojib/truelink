from __future__ import annotations

import asyncio
import re

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class MediaFileResolver(BaseResolver):
    """Resolver for MediaFile.cc URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve MediaFile.cc URL"""
        try:
            # Initial GET request, allow_redirects=True is default for aiohttp's get
            async with await self._get(url) as response:
                response_text = await response.text()

            match = re.search(r"href='([^']+)'", response_text)
            if not match:
                # Fallback: Check if it's a direct download page already (e.g. from a redirect)
                # Try to find 'showFileInformation' directly on the current page
                postvalue_direct = re.search(
                    r"showFileInformation(.*);",
                    response_text,
                )
                if not postvalue_direct:
                    raise ExtractionFailedException(
                        "Unable to find initial download link or post value on the page.",
                    )

                # If found directly, the current URL is the one to be used as referer for AJAX
                download_url = str(
                    response.url,
                )  # Get the final URL after any redirects
                postid = postvalue_direct.group(1).replace("(", "").replace(")", "")

            else:  # Original flow if href match is found
                download_url = match.group(1)
                # Original code: sleep(60)
                await asyncio.sleep(60)

                # GET request to the extracted download_url
                # Cookies from previous response should be handled by the session
                async with await self._get(
                    download_url,
                    headers={"Referer": url},
                ) as res_download_page:
                    download_page_text = await res_download_page.text()

                postvalue = re.search(
                    r"showFileInformation(.*);",
                    download_page_text,
                )
                if not postvalue:
                    raise ExtractionFailedException(
                        "Unable to find post value on download page.",
                    )
                postid = postvalue.group(1).replace("(", "").replace(")", "")

            # AJAX POST request
            ajax_headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": download_url,
            }
            async with await self._post(
                "https://mediafile.cc/account/ajax/file_details",
                data={"u": postid},
                headers=ajax_headers,
            ) as ajax_response:
                # Ensure response is JSON
                try:
                    json_response = await ajax_response.json()
                except (
                    Exception
                ) as json_error:  # More specific error for JSON parsing
                    raise ExtractionFailedException(
                        f"Failed to parse JSON response from file_details: {json_error}",
                    )

            if "html" not in json_response:
                raise ExtractionFailedException(
                    "AJAX response does not contain 'html' key.",
                )

            html_content_from_ajax = json_response["html"]

            # Find all links in the returned HTML, filter for 'download_token'
            # The original code: `[i for i in findall(r'https://[^\s"\']+', html) if "download_token" in i][1]`
            # This implies there might be multiple links and the second one is chosen.
            # We need to replicate this carefully.
            potential_links = re.findall(
                r'https://[^\s"\']+',
                html_content_from_ajax,
            )
            token_links = [
                link for link in potential_links if "download_token" in link
            ]

            if (
                len(token_links) < 2
            ):  # Or check if len(token_links) == 0 or 1 depending on expected behavior
                # Try to find any link if the specific one isn't there
                if token_links:  # if there's at least one
                    direct_link = token_links[0]
                # if no token_links, try any link from the ajax response
                elif potential_links:
                    direct_link = potential_links[0]  # Or some other logic
                else:
                    raise ExtractionFailedException(
                        "No suitable download link with 'download_token' found in AJAX response.",
                    )
            else:
                direct_link = token_links[1]  # Original logic: take the second one

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": download_url},
            )
            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFile.cc URL '{url}': {e!s}",
            ) from e

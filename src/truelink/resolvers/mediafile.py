from __future__ import annotations

import asyncio
import re
from typing import ClassVar

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class MediaFileResolver(BaseResolver):
    """Resolver for MediaFile.cc URLs"""

    DOMAINS: ClassVar[list[str]] = ["mediafile.cc"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve MediaFile.cc URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            match = re.search(r"href='([^']+)'", response_text)
            if not match:
                postvalue_direct = re.search(
                    r"showFileInformation(.*);",
                    response_text,
                )
                if not postvalue_direct:
                    raise ExtractionFailedException(
                        "Unable to find initial download link or post value on the page.",
                    )

                download_url = str(response.url)
                postid = postvalue_direct.group(1).replace("(", "").replace(")", "")

            else:
                download_url = match.group(1)
                await asyncio.sleep(60)

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

            ajax_headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": download_url,
            }
            async with await self._post(
                "https://mediafile.cc/account/ajax/file_details",
                data={"u": postid},
                headers=ajax_headers,
            ) as ajax_response:
                try:
                    json_response = await ajax_response.json()
                except Exception as json_error:
                    raise ExtractionFailedException(
                        f"Failed to parse JSON response from file_details: {json_error}",
                    )

            if "html" not in json_response:
                raise ExtractionFailedException(
                    "AJAX response does not contain 'html' key.",
                )

            html_content_from_ajax = json_response["html"]

            potential_links = re.findall(
                r'https://[^\s"\']+',
                html_content_from_ajax,
            )
            token_links = [
                link for link in potential_links if "download_token" in link
            ]

            if len(token_links) < 2:
                if token_links:
                    direct_link = token_links[0]
                elif potential_links:
                    direct_link = potential_links[0]
                else:
                    raise ExtractionFailedException(
                        "No suitable download link with 'download_token' found in AJAX response.",
                    )
            else:
                direct_link = token_links[1]

            filename, size, mime_type = await self._fetch_file_details(
                direct_link,
                headers={"Referer": download_url},
            )
            return LinkResult(
                url=direct_link, filename=filename, mime_type=mime_type, size=size
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFile.cc URL '{url}': {e!s}",
            ) from e

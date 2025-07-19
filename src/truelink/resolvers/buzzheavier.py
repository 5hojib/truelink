from __future__ import annotations

import re
from typing import ClassVar

from lxml.html import HtmlElement, fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class BuzzHeavierResolver(BaseResolver):
    """Resolver for BuzzHeavier URLs"""

    DOMAINS: ClassVar[list[str]] = ["buzzheavier.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve BuzzHeavier URL"""
        pattern = r"^https?://buzzheavier.com/[a-zA-Z0-9]+$"
        if not re.match(pattern, url):
            return LinkResult(url=url)

        try:
            async with await self._get(url) as response:
                html_content = await response.text()
                tree = fromstring(html_content)

            link_elements = tree.xpath(
                "//a[contains(@class, 'link-button') and contains(@class, 'gay-button')]/@hx-get",
            )

            if link_elements:
                download_url = await self._get_download_url(
                    f"https://buzzheavier.com{link_elements[0]}",
                )

                referer = download_url.split("?")[0]
                buzz_headers = {
                    "referer": referer,
                    "hx-current-url": referer,
                    "hx-request": "true",
                    "priority": "u=1, i",
                }
                filename, size, mime_type = await self._fetch_file_details(
                    download_url,
                    headers=buzz_headers,
                )
                return LinkResult(
                    url=download_url,
                    filename=filename,
                    mime_type=mime_type,
                    size=size,
                )

            folder_elements = tree.xpath("//tbody[@id='tbody']/tr")
            if folder_elements:
                return await self._process_folder(tree, folder_elements)

            raise ExtractionFailedException("No download link found")

        except Exception as e:
            raise ExtractionFailedException(
                f"Failed to resolve BuzzHeavier URL: {e}",
            ) from e

    async def _get_download_url(self, url: str, is_folder: bool = False) -> str:
        """Get download URL from BuzzHeavier"""
        if "/download" not in url:
            url += "/download"

        headers = {
            "referer": url.split("/download")[0],
            "hx-current-url": url.split("/download")[0],
            "hx-request": "true",
            "priority": "u=1, i",
        }

        async with await self._get(url, headers=headers) as response:
            redirect_url = response.headers.get("Hx-Redirect")
            if not redirect_url:
                if not is_folder:
                    raise ExtractionFailedException("Failed to get download URL")
                return None
            return redirect_url

    async def _process_folder(
        self, tree: HtmlElement, folder_elements: list[HtmlElement]
    ) -> FolderResult:
        """Process folder contents"""
        contents = []
        total_size = 0

        for element in folder_elements:
            try:
                file_id = element.xpath(".//a")[0].get("href", "").strip()

                download_url = await self._get_download_url(
                    f"https://buzzheavier.com{file_id}",
                    True,
                )

                if download_url:
                    referer = download_url.split("?")[0]
                    buzz_headers = {
                        "referer": referer,
                        "hx-current-url": referer,
                        "hx-request": "true",
                        "priority": "u=1, i",
                    }
                    (
                        actual_filename,
                        item_size,
                        mime_type,
                    ) = await self._fetch_file_details(
                        download_url,
                        headers=buzz_headers,
                    )

                    contents.append(
                        FileItem(
                            url=download_url,
                            filename=actual_filename,
                            mime_type=mime_type,
                            size=item_size,
                            path="",
                        ),
                    )
                    if item_size is not None:
                        total_size += item_size

            except Exception:
                continue

        title = (
            tree.xpath("//span/text()")[0].strip()
            if tree.xpath("//span/text()")
            else "BuzzHeavier Folder"
        )

        return FolderResult(
            title=title,
            contents=contents,
            total_size=total_size,
        )

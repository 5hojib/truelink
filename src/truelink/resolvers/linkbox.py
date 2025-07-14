from __future__ import annotations

import os.path
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class LinkBoxResolver(BaseResolver):
    """Resolver for LinkBox.to URLs"""

    def __init__(self):
        super().__init__()
        self._folder_details: FolderResult | None = None

    async def _fetch_item_detail(self, item_id: str) -> None:
        """Fetches and processes a single item (when shareType is singleItem)."""
        if self._folder_details is None:
            self._folder_details = FolderResult(title="", contents=[], total_size=0)

        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/detail",
                params={"itemId": item_id},
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (detail) error {response.status}: {err_text[:200]}"
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (detail) request failed: {e!s}"
            ) from e

        data = json_data.get("data")
        if not data or "itemInfo" not in data:
            msg = json_data.get("msg", "data not found in item detail response")
            raise ExtractionFailedException(f"LinkBox API (detail) error: {msg}")

        item_info = data["itemInfo"]
        item_url = item_info.get("url")
        if not item_url:
            raise ExtractionFailedException(
                "LinkBox API (detail) error: URL missing for item."
            )

        filename, size, mime_type = await self._fetch_file_details(item_url)
        self._folder_details.title = filename
        self._folder_details.contents.append(
            FileItem(
                url=item_url,
                filename=filename,
                mime_type=mime_type,
                size=size,
                path="",
            )
        )
        if size:
            self._folder_details.total_size += size

    async def _fetch_list_recursive(
        self, share_token: str, parent_id: int = 0, current_path: str = ""
    ):
        """Recursively fetch folder listings."""
        if self._folder_details is None:
            self._folder_details = FolderResult(title="", contents=[], total_size=0)

        params = {"shareToken": share_token, "pageSize": 1000, "pid": parent_id}
        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/share_out_list",
                params=params,
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (list) error {response.status}: {err_text[:200]}"
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (list) request failed: {e!s}"
            ) from e

        data = json_data.get("data")
        if not data:
            msg = json_data.get("msg", "data not found in share_out_list response")
            raise ExtractionFailedException(f"LinkBox API (list) error: {msg}")

        if data.get("shareType") == "singleItem" and "itemId" in data:
            await self._fetch_item_detail(data["itemId"])
            return

        if not self._folder_details.title:
            self._folder_details.title = data.get("dirName") or "LinkBox Folder"

        for content_item in data.get("list", []):
            if content_item.get("type") == "dir" and "url" not in content_item:
                subfolder_id = content_item.get("id")
                if subfolder_id is not None:
                    full_new_path = os.path.join(
                        current_path, content_item.get("name", "")
                    )
                    await self._fetch_list_recursive(
                        share_token, subfolder_id, full_new_path
                    )
            elif "url" in content_item:
                item_url = content_item["url"]
                filename, size, mime_type = await self._fetch_file_details(item_url)
                self._folder_details.contents.append(
                    FileItem(
                        url=item_url,
                        filename=filename,
                        mime_type=mime_type,
                        size=size,
                        path=current_path,
                    )
                )
                if size:
                    self._folder_details.total_size += size

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve LinkBox.to URL."""
        self._folder_details = FolderResult(title="", contents=[], total_size=0)

        parsed_url = urlparse(url)
        share_token = parsed_url.path.strip("/").split("/")[-1]

        if not share_token:
            raise InvalidURLException(
                "LinkBox error: Could not extract shareToken from URL."
            )

        params = {"shareToken": share_token, "pageSize": 1, "pid": 0}
        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/share_out_list",
                params=params,
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (initial check) error {response.status}: {err_text[:200]}"
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (initial check) request failed: {e!s}"
            ) from e

        initial_data = json_data.get("data")
        if not initial_data:
            msg = json_data.get("msg", "data not found in initial API response")
            raise ExtractionFailedException(
                f"LinkBox API (initial check) error: {msg}"
            )

        if (
            initial_data.get("shareType") == "singleItem"
            and "itemId" in initial_data
        ):
            await self._fetch_item_detail(initial_data["itemId"])
        else:
            if not self._folder_details.title:
                self._folder_details.title = (
                    initial_data.get("dirName") or "LinkBox Content"
                )
            await self._fetch_list_recursive(share_token, 0, "")

        if not self._folder_details.contents:
            raise ExtractionFailedException("LinkBox: No content found.")

        if len(self._folder_details.contents) == 1:
            single_item = self._folder_details.contents[0]
            if (
                self._folder_details.title == single_item.filename
                and not single_item.path
            ):
                return LinkResult(
                    url=single_item.url,
                    filename=single_item.filename,
                    mime_type=single_item.mime_type,
                    size=single_item.size,
                )

        return self._folder_details

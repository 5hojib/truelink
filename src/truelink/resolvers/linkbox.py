from __future__ import annotations

import os
from typing import ClassVar
from urllib.parse import urlparse

from truelink import mimetypes
from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class LinkBoxResolver(BaseResolver):
    """Resolver for LinkBox.to URLs"""

    DOMAINS: ClassVar[list[str]] = [
        "linkbox.to",
        "lbx.to",
        "linkbox.cloud",
        "teltobx.net",
        "telbx.net",
    ]
    BASE_API = "https://www.linkbox.to/api/file"

    def __init__(self) -> None:
        super().__init__()
        self._folder: FolderResult | None = None

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve LinkBox.to URL"""
        self._folder = FolderResult(title="", contents=[], total_size=0)
        share_token = self._extract_share_token(url)
        initial_data = await self._api_call(
            "share_out_list", {"shareToken": share_token, "pageSize": 1, "pid": 0}
        )

        if not initial_data:
            raise ExtractionFailedException(
                "LinkBox: No data in initial API response."
            )

        if (
            initial_data.get("shareType") == "singleItem"
            and "itemId" in initial_data
        ):
            await self._fetch_item_detail(initial_data["itemId"])
        else:
            self._folder.title = initial_data.get("dirName") or "LinkBox Content"
            await self._fetch_list_recursive(share_token)

        if not self._folder.contents:
            raise ExtractionFailedException("LinkBox: No files found in folder.")

        if len(self._folder.contents) == 1:
            file = self._folder.contents[0]
            return LinkResult(
                url=file.url,
                filename=file.filename,
                mime_type=file.mime_type,
                size=file.size,
            )

        return self._folder

    async def _fetch_item_detail(self, item_id: str) -> None:
        data = await self._api_call("detail", {"itemId": item_id})
        item_info = data.get("itemInfo") if data else None
        if not item_info:
            raise ExtractionFailedException(
                "LinkBox API: Missing itemInfo in response."
            )

        filename = self._finalize_filename(item_info)
        url = item_info.get("url")
        if not url:
            raise ExtractionFailedException("LinkBox API: Missing URL in item info.")

        size = self._extract_size(item_info.get("size"))
        self._folder.title = filename
        self._add_file(filename, url, size)

    async def _fetch_list_recursive(
        self, share_token: str, parent_id: int = 0, current_path: str = ""
    ) -> None:
        data = await self._api_call(
            "share_out_list",
            {"shareToken": share_token, "pageSize": 1000, "pid": parent_id},
        )

        if data.get("shareType") == "singleItem" and "itemId" in data:
            await self._fetch_item_detail(data["itemId"])
            return

        self._folder.title = (
            self._folder.title or data.get("dirName") or "LinkBox Folder"
        )
        for item in data.get("list", []):
            name = item.get("name", "unknown_item")
            if item.get("type") == "dir" and "url" not in item:
                await self._fetch_list_recursive(
                    share_token,
                    item["id"],
                    os.path.join(current_path, name) if current_path else name,
                )
            elif "url" in item:
                filename = self._finalize_filename(item)
                url = item["url"]
                size = self._extract_size(item.get("size"))
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type is None:
                    mime_type = "application/octet-stream"
                self._add_file(filename, url, mime_type, size, current_path)

    async def _api_call(self, endpoint: str, params: dict) -> dict:
        try:
            async with await self._get(
                f"{self.BASE_API}/{endpoint}", params=params
            ) as response:
                if response.status != 200:
                    msg = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API ({endpoint}) error {response.status}: {msg[:200]}"
                    )
                json_data = await response.json()
                if "data" not in json_data:
                    raise ExtractionFailedException(
                        f"LinkBox API ({endpoint}) error: {json_data.get('msg')}"
                    )
                return json_data["data"]
        except ExtractionFailedException:
            raise
        except Exception as e:
            raise ExtractionFailedException(
                f"LinkBox API ({endpoint}) failed: {e!s}"
            ) from e

    def _extract_share_token(self, url: str) -> str:
        token = urlparse(url).path.strip("/").split("/")[-1]
        if not token:
            raise InvalidURLException("LinkBox: Missing shareToken in URL.")
        return token

    def _extract_size(self, size_val: str | float | None) -> int | None:
        if isinstance(size_val, str) and size_val.isdigit():
            return int(size_val)
        if isinstance(size_val, int | float):
            return int(size_val)
        return None

    def _finalize_filename(self, item: dict) -> str:
        name = item.get("name", "unknown_file")
        sub_type = item.get("sub_type")
        if sub_type and not name.strip().endswith(f".{sub_type}"):
            name += f".{sub_type}"
        return name

    def _add_file(
        self,
        filename: str,
        url: str,
        mime_type: str | None,
        size: int | None,
        path: str = "",
    ) -> None:
        self._folder.contents.append(
            FileItem(
                url=url, filename=filename, mime_type=mime_type, size=size, path=path
            )
        )
        if size:
            self._folder.total_size += size

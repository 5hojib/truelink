from __future__ import annotations

import os.path  # For ospath.join, though can be replaced with PurePath for better os-agnosticism
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class LinkBoxResolver(BaseResolver):
    """Resolver for LinkBox.to URLs"""

    def __init__(self):
        super().__init__()
        # Store folder details during recursion
        self._folder_details: FolderResult | None = None

    async def _fetch_item_detail(self, item_id: str) -> None:
        """Fetches and processes a single item (when shareType is singleItem)."""
        if self._folder_details is None:  # Should be initialized by resolve()
            self._folder_details = FolderResult(title="", contents=[], total_size=0)

        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/detail",
                params={"itemId": item_id},
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (detail) error {response.status}: {err_text[:200]}",
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (detail) request failed: {e!s}",
            ) from e

        data = json_data.get("data")
        if not data:
            msg = json_data.get("msg", "data not found in item detail response")
            raise ExtractionFailedException(f"LinkBox API (detail) error: {msg}")

        item_info = data.get("itemInfo")
        if not item_info:
            raise ExtractionFailedException(
                "LinkBox API (detail) error: itemInfo not found",
            )

        filename = item_info.get("name", "unknown_file")
        sub_type = item_info.get("sub_type")
        if (
            sub_type
            and isinstance(filename, str)
            and not filename.strip().endswith(f".{sub_type}")
        ):
            filename += f".{sub_type}"

        if (
            not self._folder_details.title
        ):  # Set folder title from the single item if not already set
            self._folder_details.title = filename

        item_url = item_info.get("url")
        if not item_url:
            raise ExtractionFailedException(
                "LinkBox API (detail) error: URL missing for item.",
            )

        size = None
        if "size" in item_info:
            size_val = item_info["size"]
            if (isinstance(size_val, str) and size_val.isdigit()) or isinstance(
                size_val,
                int | float,
            ):
                size = int(size_val)

        self._folder_details.contents.append(
            FileItem(
                filename=filename,
                url=item_url,
                size=size,
                path="",
            ),  # Single item has no sub-path
        )
        if size:
            self._folder_details.total_size += size

    async def _fetch_list_recursive(
        self,
        share_token: str,
        parent_id: int = 0,
        current_path: str = "",
    ):
        """Recursively fetches file and folder listings."""
        if self._folder_details is None:  # Should be initialized
            self._folder_details = FolderResult(title="", contents=[], total_size=0)

        params = {
            "shareToken": share_token,
            "pageSize": 1000,  # Assuming max items per page
            "pid": parent_id,
        }
        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/share_out_list",
                params=params,
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (list) error {response.status}: {err_text[:200]}",
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (list) request failed: {e!s}",
            ) from e

        data = json_data.get("data")
        if not data:
            msg = json_data.get("msg", "data not found in share_out_list response")
            raise ExtractionFailedException(f"LinkBox API (list) error: {msg}")

        # Handle single item shares directly if indicated by API (original script logic)
        if data.get("shareType") == "singleItem" and "itemId" in data:
            # This means the initial call to share_out_list was for a single item.
            # We should call _fetch_item_detail here.
            # The recursive structure might not be needed if it's truly a single item share.
            # The original code calls __singleItem from within __fetch_links if shareType is singleItem.
            # This implies the main resolve function should check shareType first.
            # For now, let this path call _fetch_item_detail.
            await self._fetch_item_detail(data["itemId"])
            return  # Single item processed, no further recursion needed from here.

        if not self._folder_details.title and "dirName" in data:
            self._folder_details.title = data["dirName"] or "LinkBox Folder"

        contents_list = data.get("list", [])
        if (
            not contents_list
            and parent_id == 0
            and not self._folder_details.contents
        ):  # Empty if it's the root and no items yet
            # This might not be an error if the folder is genuinely empty.
            # Consider how to handle empty shared folders. For now, it will result in empty FolderResult.
            pass

        for content_item in contents_list:
            item_name = content_item.get("name", "unknown_item")
            if (
                content_item.get("type") == "dir" and "url" not in content_item
            ):  # It's a sub-folder
                subfolder_id = content_item.get("id")
                if subfolder_id is not None:  # Ensure ID exists
                    # Path logic from original: new_path = os.path.join(details["title"], content["name"]) if not folderPath else os.path.join(folderPath, content["name"])
                    # The path should be relative to the main shared folder's title.
                    # If current_path is empty, it's a direct child of the root.
                    new_path_segment = item_name
                    full_new_path = (
                        os.path.join(current_path, new_path_segment)
                        if current_path
                        else new_path_segment
                    )
                    await self._fetch_list_recursive(
                        share_token,
                        subfolder_id,
                        full_new_path,
                    )
            elif "url" in content_item:  # It's a file
                filename = item_name
                sub_type = content_item.get("sub_type")
                if (
                    sub_type
                    and isinstance(filename, str)
                    and not filename.strip().endswith(f".{sub_type}")
                ):
                    filename += f".{sub_type}"

                item_url = content_item["url"]
                size = None
                if "size" in content_item:
                    size_val = content_item["size"]
                    if (
                        isinstance(size_val, str) and size_val.isdigit()
                    ) or isinstance(size_val, int | float):
                        size = int(size_val)

                self._folder_details.contents.append(
                    FileItem(
                        filename=filename,
                        url=item_url,
                        size=size,
                        path=current_path,
                    ),
                )
                if size:
                    self._folder_details.total_size += size

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve LinkBox.to URL"""
        self._folder_details = FolderResult(
            title="",
            contents=[],
            total_size=0,
        )  # Reset for each call

        parsed_url = urlparse(url)
        path_segments = parsed_url.path.split("/")
        share_token = None
        if path_segments:
            share_token = path_segments[
                -1
            ]  # Assumes share token is the last part of the path

        if not share_token:
            raise InvalidURLException(
                "LinkBox error: Could not extract shareToken from URL.",
            )

        # Initial call to determine if it's a single item or a list/folder
        # We make one call to share_out_list to check 'shareType'
        params = {
            "shareToken": share_token,
            "pageSize": 1,
            "pid": 0,
        }  # pageSize 1 is enough to get shareType
        try:
            async with await self._get(
                "https://www.linkbox.to/api/file/share_out_list",
                params=params,
            ) as response:
                if response.status != 200:
                    err_text = await response.text()
                    raise ExtractionFailedException(
                        f"LinkBox API (initial check) error {response.status}: {err_text[:200]}",
                    )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"LinkBox API (initial check) request failed: {e!s}",
            ) from e

        initial_data = json_data.get("data")
        if not initial_data:
            msg = json_data.get("msg", "data not found in initial API response")
            raise ExtractionFailedException(
                f"LinkBox API (initial check) error: {msg}",
            )

        if (
            initial_data.get("shareType") == "singleItem"
            and "itemId" in initial_data
        ):
            await self._fetch_item_detail(initial_data["itemId"])
        else:
            # If not singleItem, or if shareType is missing, proceed with full recursive fetch
            # The initial dirName can set the title here
            if not self._folder_details.title and "dirName" in initial_data:
                self._folder_details.title = (
                    initial_data["dirName"] or "LinkBox Content"
                )
            # Start recursive fetching from root (pid=0)
            await self._fetch_list_recursive(share_token, 0, "")

        if not self._folder_details.contents:
            # This could be an empty folder or a genuine error if no items were processed.
            # If title is also empty, it's more likely an issue.
            if not self._folder_details.title:
                raise ExtractionFailedException(
                    "LinkBox: No content found and no title obtained.",
                )
            # Otherwise, it's an empty folder, which is a valid FolderResult.

        # If only one item was found (e.g. from singleItem shareType or a folder with one file)
        # and the title is essentially the filename, return LinkResult for consistency.
        if len(self._folder_details.contents) == 1:
            single_item = self._folder_details.contents[0]
            # Heuristic: if folder title is same as the single file's name, treat as LinkResult
            if (
                self._folder_details.title == single_item.filename
                and not single_item.path
            ):
                return LinkResult(
                    url=single_item.url,
                    filename=single_item.filename,
                    size=single_item.size,
                )

        return self._folder_details

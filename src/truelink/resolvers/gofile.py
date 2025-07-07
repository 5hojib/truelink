from __future__ import annotations

import os.path  # For ospath.join
from hashlib import sha256
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

# Assuming PASSWORD_ERROR_MESSAGE is available
PASSWORD_ERROR_MESSAGE_GOFILE = (
    "GoFile link {} requires a password (append ::password to the URL)."
)


class GoFileResolver(BaseResolver):
    """Resolver for GoFile.io URLs"""

    def __init__(self):
        super().__init__()
        self._folder_details: FolderResult | None = None
        self._account_token: str | None = (
            None  # To store the fetched token for API calls
        )

    async def _get_gofile_token(self) -> str:
        """Fetches an account token from GoFile API."""
        # This token is often required for subsequent API calls.
        # It might be a guest token or associated with an account if cookies were pre-set.
        # BaseResolver's session might pick up some cookies, but explicit token fetch is safer.
        api_url = (
            "https://api.gofile.io/accounts"  # Original used POST, let's verify.
        )
        # The example curl on gofile.io/api uses GET for createAccount
        # Let's try GET https://api.gofile.io/createAccount first
        # Or if the original POST to /accounts works, use that.
        # Sticking to original's POST to /accounts for now.

        # The original script's headers for token fetch:
        # headers = { "User-Agent": user_agent, "Accept-Encoding": "gzip, deflate, br", "Accept": "*/*", "Connection": "keep-alive"}
        # BaseResolver's session sets User-Agent. Others are standard.
        async with await self._post(
            api_url,
            data=None,
        ) as response:  # POST with no body
            if response.status != 200:
                err_text = await response.text()
                raise ExtractionFailedException(
                    f"GoFile: Failed to get token (status {response.status}). {err_text[:200]}",
                )
            try:
                json_data = await response.json()
            except Exception as e_json:
                err_txt = await response.text()
                raise ExtractionFailedException(
                    f"GoFile: Failed to parse token JSON. {e_json}. Response: {err_txt[:200]}",
                )

        if json_data.get("status") != "ok" or "token" not in json_data.get(
            "data",
            {},
        ):
            raise ExtractionFailedException(
                f"GoFile: Failed to get valid token. API Response: {json_data.get('message', 'Unknown error')}",
            )

        return json_data["data"]["token"]

    async def _fetch_gofile_links_recursive(
        self,
        content_id: str,
        password_hash: str,
        current_path: str = "",
    ):
        """Recursively fetches file and folder listings from GoFile."""
        if self._folder_details is None:  # Should be initialized
            self._folder_details = FolderResult(title="", contents=[], total_size=0)
        if not self._account_token:  # Should be fetched by resolve()
            raise ExtractionFailedException(
                "GoFile: Account token not available for fetching links.",
            )

        # wt=4fd6sg89d7s6&cache=true -> These seem like specific parameters, keeping them.
        api_url = (
            f"https://api.gofile.io/contents/{content_id}?wt=4fd6sg89d7s6&cache=true"
        )
        if password_hash:
            api_url += f"&password={password_hash}"

        headers = {
            "Authorization": f"Bearer {self._account_token}",
            # Other headers like User-Agent are handled by BaseResolver's session
        }

        try:
            async with await self._get(api_url, headers=headers) as response:
                if response.status != 200:
                    try:
                        json_err = await response.json()
                        status_msg = json_err.get("status", "")
                        if "error-passwordRequired" in status_msg:
                            # URL for password message should be the original user-provided URL
                            # This is tricky as resolve() has that, not this recursive func directly.
                            # For now, using a generic message.
                            raise ExtractionFailedException(
                                PASSWORD_ERROR_MESSAGE_GOFILE.format(
                                    f"ID: {content_id}",
                                ),
                            )
                        if "error-passwordWrong" in status_msg:
                            raise ExtractionFailedException(
                                "GoFile error: Incorrect password provided.",
                            )
                        if "error-notFound" in status_msg:
                            raise ExtractionFailedException(
                                f"GoFile error: Content ID '{content_id}' not found.",
                            )
                        if "error-notPublic" in status_msg:
                            raise ExtractionFailedException(
                                f"GoFile error: Folder ID '{content_id}' is not public.",
                            )

                        err_detail = json_err.get("message", await response.text())
                        raise ExtractionFailedException(
                            f"GoFile API (contents) error {response.status}: {status_msg} - {err_detail[:200]}",
                        )
                    except Exception:  # If error response is not JSON
                        err_text = await response.text()
                        raise ExtractionFailedException(
                            f"GoFile API (contents) error {response.status}: {err_text[:200]}",
                        )
                json_data = await response.json()
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"GoFile API (contents) request for ID '{content_id}' failed: {e!s}",
            ) from e

        if json_data.get("status") != "ok":
            # This should ideally be caught by status code check above, but as a fallback.
            raise ExtractionFailedException(
                f"GoFile API (contents) returned non-ok status: {json_data.get('status', 'Unknown status')}",
            )

        data_node = json_data.get("data")
        if not data_node:
            raise ExtractionFailedException(
                "GoFile API (contents) error: 'data' node missing in response.",
            )

        if not self._folder_details.title:  # Set root folder title
            self._folder_details.title = data_node.get(
                "name",
                content_id
                if data_node.get("type") == "folder"
                else "GoFile Content",
            )

        children_nodes = data_node.get("children", {})
        for (
            child_id,
            child_content,
        ) in children_nodes.items():  # children is a dict of id: content_obj
            child_name = child_content.get("name", child_id)
            if child_content.get("type") == "folder":
                if not child_content.get(
                    "public",
                    True,
                ):  # Skip non-public subfolders unless behavior changes
                    continue
                new_path_segment = child_name
                full_new_path = (
                    os.path.join(current_path, new_path_segment)
                    if current_path
                    else new_path_segment
                )
                await self._fetch_gofile_links_recursive(
                    child_id,
                    password_hash,
                    full_new_path,
                )
            else:  # It's a file
                file_link = child_content.get("link")
                if not file_link:
                    continue  # Skip if no link

                size = None
                if "size" in child_content:
                    size_val = child_content["size"]
                    if isinstance(
                        size_val,
                        int | float,
                    ):  # Gofile API usually provides size in bytes
                        size = int(size_val)

                self._folder_details.contents.append(
                    FileItem(
                        filename=child_name,
                        url=file_link,
                        size=size,
                        path=current_path,
                    ),
                )
                if size:
                    self._folder_details.total_size += size

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve GoFile.io URL"""
        self._folder_details = FolderResult(
            title="",
            contents=[],
            total_size=0,
        )  # Reset
        self._account_token = None  # Reset

        _password = ""
        request_url = url
        if "::" in url:
            parts = url.split("::", 1)
            request_url = parts[0]
            _password = parts[1]

        parsed_url = urlparse(request_url)
        path_segments = parsed_url.path.split("/")
        content_id = None
        if path_segments:  # ID is usually the last part of path, e.g. /d/ gratuitamente or /d/folderId
            content_id = path_segments[-1]

        if not content_id:
            raise InvalidURLException(
                "GoFile error: Could not extract content ID from URL.",
            )

        # Hash password if provided
        password_hash = (
            sha256(_password.encode("utf-8")).hexdigest() if _password else ""
        )

        try:
            self._account_token = await self._get_gofile_token()
            await self._fetch_gofile_links_recursive(
                content_id,
                password_hash,
                "",
            )  # Start with empty path

        except ExtractionFailedException as e:
            # Specific error message for password required, if not handled deeper
            if "passwordRequired" in str(e) and not _password:
                raise ExtractionFailedException(
                    PASSWORD_ERROR_MESSAGE_GOFILE.format(request_url),
                ) from e
            raise e  # Re-raise other extraction failures
        except Exception as e_outer:
            raise ExtractionFailedException(
                f"GoFile resolution failed: {e_outer!s}",
            ) from e_outer

        if not self._folder_details.contents:
            # Check if it was a root file that failed (e.g. wrong password for a single root file)
            # The API for single root files might be different or covered by the children logic if root is a "folder" of one.
            # If contents is empty, it means no files were successfully processed.
            # This could be an empty folder, or an error not caught.
            if (
                not self._folder_details.title
            ):  # No title and no contents often means failure
                raise ExtractionFailedException(
                    f"GoFile: No downloadable content found for ID '{content_id}'. It might be empty, private, or password protected.",
                )
            # If title exists but no content, it's an empty folder.

        # Original script returned (url, header) for single file.
        # We will return LinkResult or FolderResult. The header (cookie) is used for API calls,
        # not directly for downloads unless links are not truly direct.
        # For now, assuming links are direct once obtained.
        if len(self._folder_details.contents) == 1:
            single_item = self._folder_details.contents[0]
            # If the main "folder" title is essentially the item's name and path is empty.
            if (
                self._folder_details.title == single_item.filename
                and not single_item.path
            ):
                # The token might be needed in headers for the download itself.
                # This is where the original `details["header"]` would be relevant.
                # For now, returning LinkResult without custom headers.
                # If downloads fail, this might need to be revisited to pass headers.
                return LinkResult(
                    url=single_item.url,
                    filename=single_item.filename,
                    size=single_item.size,
                )

        return self._folder_details

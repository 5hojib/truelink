from __future__ import annotations

import os.path  # For ospath.join
from hashlib import sha256
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

PASSWORD_ERROR_MESSAGE_GOFILE = (
    "GoFile link {} requires a password (append ::password to the URL)."
)


class GoFileResolver(BaseResolver):
    """Resolver for GoFile.io URLs"""

    def __init__(self):
        super().__init__()
        self._folder_details: FolderResult | None = None
        self._account_token: str | None = None

    async def _get_gofile_token(self) -> str:
        """Fetches an account token from GoFile API."""
        api_url = "https://api.gofile.io/accounts"
        async with await self._post(api_url, data=None) as response:
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
        if self._folder_details is None:
            self._folder_details = FolderResult(title="", contents=[], total_size=0)
        if not self._account_token:
            raise ExtractionFailedException(
                "GoFile: Account token not available for fetching links.",
            )

        api_url = (
            f"https://api.gofile.io/contents/{content_id}?wt=4fd6sg89d7s6&cache=true"
        )
        if password_hash:
            api_url += f"&password={password_hash}"

        headers = {"Authorization": f"Bearer {self._account_token}"}

        try:
            async with await self._get(api_url, headers=headers) as response:
                if response.status != 200:
                    try:
                        json_err = await response.json()
                        status_msg = json_err.get("status", "")
                        if "error-passwordRequired" in status_msg:
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
                    except Exception:
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
            raise ExtractionFailedException(
                f"GoFile API (contents) returned non-ok status: {json_data.get('status', 'Unknown status')}",
            )

        data_node = json_data.get("data")
        if not data_node:
            raise ExtractionFailedException(
                "GoFile API (contents) error: 'data' node missing in response.",
            )

        if not self._folder_details.title:
            self._folder_details.title = data_node.get(
                "name",
                content_id
                if data_node.get("type") == "folder"
                else "GoFile Content",
            )

        children_nodes = data_node.get("children", {})
        for child_id, child_content in children_nodes.items():
            child_name = child_content.get("name", child_id)
            if child_content.get("type") == "folder":
                if not child_content.get("public", True):
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
            else:
                file_link = child_content.get("link")
                if not file_link:
                    continue

                size = None
                if "size" in child_content:
                    size_val = child_content["size"]
                    if isinstance(size_val, int | float):
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
        )
        self._account_token = None

        _password = ""
        request_url = url
        if "::" in url:
            parts = url.split("::", 1)
            request_url = parts[0]
            _password = parts[1]

        parsed_url = urlparse(request_url)
        path_segments = parsed_url.path.split("/")
        content_id = None
        if path_segments:
            content_id = path_segments[-1]

        if not content_id:
            raise InvalidURLException(
                "GoFile error: Could not extract content ID from URL.",
            )

        password_hash = (
            sha256(_password.encode("utf-8")).hexdigest() if _password else ""
        )

        try:
            self._account_token = await self._get_gofile_token()
            await self._fetch_gofile_links_recursive(content_id, password_hash, "")

        except ExtractionFailedException as e:
            if "passwordRequired" in str(e) and not _password:
                raise ExtractionFailedException(
                    PASSWORD_ERROR_MESSAGE_GOFILE.format(request_url),
                ) from e
            raise e
        except Exception as e_outer:
            raise ExtractionFailedException(
                f"GoFile resolution failed: {e_outer!s}",
            ) from e_outer

        if not self._folder_details.contents:
            if not self._folder_details.title:
                raise ExtractionFailedException(
                    f"GoFile: No downloadable content found for ID '{content_id}'. It might be empty, private, or password protected.",
                )

        if len(self._folder_details.contents) == 1:
            single_item = self._folder_details.contents[0]
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

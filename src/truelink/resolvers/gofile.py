from __future__ import annotations

import os
from hashlib import sha256
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

if TYPE_CHECKING:
    import aiohttp

PASSWORD_ERROR_MESSAGE = (
    "GoFile link {} requires a password (append ::password to the URL)."
)


class GoFileResolver(BaseResolver):
    """Resolver for GoFile.io URLs."""

    DOMAINS: ClassVar[list[str]] = ["gofile.io"]

    def __init__(self) -> None:
        super().__init__()
        self._folder_details: FolderResult | None = None
        self._account_token: str | None = None

    async def _get_account_token(self) -> str:
        api_url = "https://api.gofile.io/accounts"
        async with await self._post(api_url, data=None) as response:
            if response.status != 200:
                err = await response.text()
                raise ExtractionFailedException(
                    f"GoFile: Failed to get token ({response.status}). {err[:200]}"
                )
            try:
                data = await response.json()
            except Exception as e:
                err = await response.text()
                raise ExtractionFailedException(
                    f"GoFile: Failed to parse token JSON. {e}. Response: {err[:200]}"
                )

        if data.get("status") != "ok" or "token" not in data.get("data", {}):
            raise ExtractionFailedException(
                f"GoFile: Invalid token response. Message: {data.get('message', 'Unknown error')}"
            )

        return data["data"]["token"]

    async def _fetch_folder_contents(
        self,
        content_id: str,
        password_hash: str,
        current_path: str = "",
    ) -> None:
        if self._folder_details is None:
            self._folder_details = FolderResult(title="", contents=[], total_size=0)

        if not self._account_token:
            raise ExtractionFailedException("GoFile: Missing account token.")

        api_url = (
            f"https://api.gofile.io/contents/{content_id}?wt=4fd6sg89d7s6&cache=true"
        )
        if password_hash:
            api_url += f"&password={password_hash}"

        headers = {"Authorization": f"Bearer {self._account_token}"}

        try:
            async with await self._get(api_url, headers=headers) as response:
                if response.status != 200:
                    await self._handle_api_error(response, content_id)
                data = await response.json()
        except ExtractionFailedException:
            raise
        except Exception as e:
            raise ExtractionFailedException(
                f"GoFile API request failed for ID '{content_id}': {e}"
            ) from e

        if data.get("status") != "ok":
            raise ExtractionFailedException(
                f"GoFile API returned non-ok status: {data.get('status', 'Unknown')}"
            )

        node = data.get("data")
        if not node:
            raise ExtractionFailedException("GoFile API error: 'data' node missing.")

        if not self._folder_details.title:
            self._folder_details.title = node.get(
                "name",
                content_id if node.get("type") == "folder" else "GoFile Content",
            )

        for child_id, content in node.get("children", {}).items():
            name = content.get("name", child_id)
            if content.get("type") == "folder":
                if not content.get("public", True):
                    continue
                next_path = (
                    os.path.join(current_path, name) if current_path else name
                )
                await self._fetch_folder_contents(child_id, password_hash, next_path)
            else:
                url = content.get("link")
                if not url:
                    continue
                filename, size, mime_type = await self._fetch_file_details(
                    url, {"Cookie": f"accountToken={self._account_token}"}
                )
                self._folder_details.contents.append(
                    FileItem(
                        url=url,
                        filename=filename,
                        mime_type=mime_type,
                        size=size,
                        path=current_path,
                    )
                )
                self._folder_details.total_size += size

    async def _handle_api_error(
        self, response: aiohttp.ClientResponse, content_id: str
    ) -> None:
        try:
            error_data = await response.json()
            status = error_data.get("status", "")
            message = error_data.get("message", "")
            if "error-passwordRequired" in status:
                raise ExtractionFailedException(
                    PASSWORD_ERROR_MESSAGE.format(f"ID: {content_id}")
                )
            if "error-passwordWrong" in status:
                raise ExtractionFailedException("GoFile error: Incorrect password.")
            if "error-notFound" in status:
                raise ExtractionFailedException(
                    f"GoFile error: ID '{content_id}' not found."
                )
            if "error-notPublic" in status:
                raise ExtractionFailedException(
                    f"GoFile error: Folder ID '{content_id}' is not public."
                )
            raise ExtractionFailedException(
                f"GoFile API error {response.status}: {status} - {message[:200]}"
            )
        except Exception:
            text = await response.text()
            raise ExtractionFailedException(
                f"GoFile API error {response.status}: {text[:200]}"
            )

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve GoFile.io URL."""
        self._folder_details = FolderResult(title="", contents=[], total_size=0)
        self._account_token = None

        request_url, password = ([*url.split("::", 1), ""])[:2]
        parsed = urlparse(request_url)
        content_id = parsed.path.strip("/").split("/")[-1]

        if not content_id:
            raise InvalidURLException("GoFile error: Content ID not found in URL.")

        password_hash = sha256(password.encode()).hexdigest() if password else ""

        try:
            self._account_token = await self._get_account_token()
            await self._fetch_folder_contents(content_id, password_hash)
        except ExtractionFailedException as e:
            if "passwordRequired" in str(e) and not password:
                raise ExtractionFailedException(
                    PASSWORD_ERROR_MESSAGE.format(request_url)
                ) from e
            raise
        except Exception as e:
            raise ExtractionFailedException(f"GoFile resolution failed: {e}") from e

        headers = {"Cookie": f"accountToken={self._account_token}"}

        if not self._folder_details.contents:
            raise ExtractionFailedException(
                f"GoFile: No content found for ID '{content_id}'. It might be empty, private, or protected."
            )

        if (
            len(self._folder_details.contents) == 1
            and self._folder_details.title
            == self._folder_details.contents[0].filename
            and not self._folder_details.contents[0].path
        ):
            item = self._folder_details.contents[0]
            return LinkResult(
                url=item.url,
                filename=item.filename,
                mime_type=item.mime_type,
                size=item.size,
                headers=headers,
            )

        self._folder_details.headers = headers
        return self._folder_details

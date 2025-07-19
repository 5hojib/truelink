from __future__ import annotations

import base64
import re
from typing import ClassVar

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class SwissTransferResolver(BaseResolver):
    """Resolver for SwissTransfer.com URLs"""

    DOMAINS: ClassVar[list[str]] = ["swisstransfer.com"]

    async def _get_file_metadata(
        self,
        transfer_id: str,
        password_b64: str | None,
    ) -> dict:
        """Fetches metadata for a given transfer_id."""
        api_url = f"https://www.swisstransfer.com/api/links/{transfer_id}"
        headers = {"User-Agent": self.USER_AGENT}
        if password_b64:
            headers["Authorization"] = password_b64
        else:
            headers["Content-Type"] = "application/json"

        async with await self._get(api_url, headers=headers) as response:
            if response.status != 200:
                err_text = await response.text()
                try:
                    json_err = await response.json(content_type=None)
                    if "message" in json_err:
                        err_text = json_err["message"]
                except Exception:
                    pass
                raise ExtractionFailedException(
                    f"SwissTransfer API (metadata) error {response.status}: {err_text[:200]}",
                )
            try:
                return await response.json()
            except Exception as e_json:
                err_txt = await response.text()
                raise ExtractionFailedException(
                    f"SwissTransfer API (metadata) error: Failed to parse JSON. {e_json}. Response: {err_txt[:200]}",
                )

    async def _generate_download_token(
        self,
        password_str: str | None,
        container_uuid: str,
        file_uuid: str,
    ) -> str:
        """Generates a download token for a specific file."""
        api_url = "https://www.swisstransfer.com/api/generateDownloadToken"
        headers = {
            "User-Agent": self.USER_AGENT,
            "Content-Type": "application/json",
        }
        payload = {
            "password": password_str if password_str else "",
            "containerUUID": container_uuid,
            "fileUUID": file_uuid,
        }

        async with await self._post(
            api_url,
            headers=headers,
            json=payload,
        ) as response:
            if response.status != 200:
                err_text = await response.text()
                try:
                    json_err = await response.json(content_type=None)
                    if "message" in json_err:
                        err_text = json_err["message"]
                except Exception:
                    pass
                raise ExtractionFailedException(
                    f"SwissTransfer API (token) error {response.status}: {err_text[:200]}",
                )
            token_text = await response.text()
            return token_text.strip().replace('"', "")

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve SwissTransfer.com URL"""

        match = re.match(
            r"https://www\.swisstransfer\.com/d/([\w-]+)(?:::(\S+))?",
            url,
        )
        if not match:
            raise InvalidURLException(
                f"Invalid SwissTransfer URL format. Expected '/d/transfer-id[::password]'. Got: {url}",
            )

        transfer_id, password_str = match.groups()
        password_str = password_str or None

        password_b64 = None
        if password_str:
            try:
                password_b64 = base64.b64encode(password_str.encode("utf-8")).decode(
                    "utf-8",
                )
            except Exception as e_b64:
                raise InvalidURLException(
                    f"Failed to base64 encode password: {e_b64}",
                )

        metadata_response = await self._get_file_metadata(transfer_id, password_b64)

        try:
            data_node = metadata_response["data"]
            container_uuid = data_node["containerUUID"]
            download_host = data_node["downloadHost"]
            files_list = data_node["container"]["files"]
            folder_name = (
                data_node["container"].get("message")
                or f"SwissTransfer_{transfer_id}"
            )
        except (KeyError, TypeError) as e_parse:
            raise ExtractionFailedException(
                f"SwissTransfer error: Could not parse required fields from metadata. Error: {e_parse}. Metadata: {str(metadata_response)[:300]}",
            )

        if not files_list:
            raise ExtractionFailedException(
                "SwissTransfer error: No files found in the transfer metadata.",
            )

        if len(files_list) == 1:
            file_info = files_list[0]
            file_uuid = file_info.get("UUID")
            file_display_name = file_info.get("fileName", "unknown_file")
            file_size_bytes = file_info.get("fileSizeInBytes")

            if not file_uuid:
                raise ExtractionFailedException(
                    "SwissTransfer error: File UUID missing for single file.",
                )

            token = await self._generate_download_token(
                password_str,
                container_uuid,
                file_uuid,
            )
            if not token:
                raise ExtractionFailedException(
                    "SwissTransfer error: Failed to generate download token for single file.",
                )

            direct_download_url = f"https://{download_host}/api/download/{transfer_id}/{file_uuid}?token={token}"

            return LinkResult(
                url=direct_download_url,
                filename=file_display_name,
                size=file_size_bytes,
            )

        folder_contents: list[FileItem] = []
        total_folder_size = 0

        for file_info in files_list:
            file_uuid = file_info.get("UUID")
            file_display_name = file_info.get("fileName")
            file_size_bytes = file_info.get("fileSizeInBytes")

            if not (file_uuid and file_display_name):
                continue

            try:
                token = await self._generate_download_token(
                    password_str,
                    container_uuid,
                    file_uuid,
                )
                if not token:
                    continue
            except ExtractionFailedException:
                continue

            item_download_url = f"https://{download_host}/api/download/{transfer_id}/{file_uuid}?token={token}"
            folder_contents.append(
                FileItem(
                    url=item_download_url,
                    filename=file_display_name,
                    size=file_size_bytes,
                    path="",
                ),
            )
            if file_size_bytes is not None:
                total_folder_size += file_size_bytes

        if not folder_contents:
            raise ExtractionFailedException(
                "SwissTransfer error: No valid files could be processed in the multi-file transfer.",
            )

        return FolderResult(
            title=folder_name,
            contents=folder_contents,
            total_size=total_folder_size,
        )

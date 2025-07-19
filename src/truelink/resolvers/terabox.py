from __future__ import annotations

from typing import ClassVar
from urllib.parse import quote

from truelink.exceptions import ExtractionFailedException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


class TeraboxResolver(BaseResolver):
    DOMAINS: ClassVar[list[str]] = [
        "terabox.com",
        "nephobox.com",
        "4funbox.com",
        "mirrobox.com",
        "momerybox.com",
        "teraboxapp.com",
        "1024tera.com",
        "terabox.app",
        "gibibox.com",
        "goaibox.com",
        "terasharelink.com",
        "teraboxlink.com",
        "freeterabox.com",
        "1024terabox.com",
        "teraboxshare.com",
        "terafileshare.com",
        "terabox.club",
    ]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        if "/file/" in url and ("terabox.com" in url or "teraboxapp.com" in url):
            filename, size, mime_type = await self._fetch_file_details(url)
            return LinkResult(
                url=url, filename=filename, mime_type=mime_type, size=size
            )

        api_url = f"https://wdzone-terabox-api.vercel.app/api?url={quote(url)}"

        try:
            async with await self._get(api_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExtractionFailedException(
                        f"Terabox API error ({response.status}): {error_text[:200]}",
                    )
                try:
                    json_response = await response.json()
                except Exception as json_error:
                    text_snippet = await response.text()
                    raise ExtractionFailedException(
                        f"Terabox API error: Failed to parse JSON response. {json_error}. Response: {text_snippet[:200]}",
                    )

            if "✅ Status" not in json_response or not json_response.get(
                "📜 Extracted Info",
            ):
                error_message = json_response.get(
                    "message",
                    "File not found or API failed to extract info.",
                )
                if "error" in json_response:
                    error_message = json_response["error"]
                raise ExtractionFailedException(f"Terabox: {error_message}")

            extracted_info = json_response["📜 Extracted Info"]

            if not isinstance(extracted_info, list) or not extracted_info:
                raise ExtractionFailedException(
                    "Terabox API error: '📜 Extracted Info' is not a valid list or is empty.",
                )

            if len(extracted_info) == 1:
                file_data = extracted_info[0]
                direct_link = file_data.get("🔽 Direct Download Link")

                if not direct_link:
                    raise ExtractionFailedException(
                        "Terabox API error: Missing download link for single file.",
                    )

                (
                    header_filename,
                    header_size,
                    mime_type,
                ) = await self._fetch_file_details(
                    direct_link,
                )

                return LinkResult(
                    url=direct_link,
                    filename=header_filename,
                    mime_type=mime_type,
                    size=header_size,
                )

            folder_contents: list[FileItem] = []
            total_size = 0
            folder_title = extracted_info[0].get("📂 Title", "Terabox Folder")

            for item_data in extracted_info:
                item_link = item_data.get("🔽 Direct Download Link")
                item_filename, item_size, mime_type = await self._fetch_file_details(
                    item_link,
                )
                if not item_link:
                    continue

                folder_contents.append(
                    FileItem(
                        url=item_link,
                        filename=item_filename,
                        mime_type=mime_type,
                        size=item_size,
                        path="",
                    ),
                )
                total_size += item_size

            if not folder_contents:
                raise ExtractionFailedException(
                    "Terabox: No valid files found in folder data from API.",
                )

            return FolderResult(
                title=folder_title,
                contents=folder_contents,
                total_size=total_size,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Terabox URL '{url}': {e!s}",
            ) from e

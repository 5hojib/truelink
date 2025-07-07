from __future__ import annotations

from urllib.parse import quote

from truelink.exceptions import ExtractionFailedException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


# Placeholder for speed_string_to_bytes.
# A more robust implementation would handle various units like KB, MB, GB, TB and case-insensitivity.
def _speed_string_to_bytes_placeholder(size_str: str) -> int:
    """
    Basic placeholder for converting size strings (e.g., "1.2GB", "500MB") to bytes.
    This is a simplified version and may need to be replaced with a more robust one.
    """
    size_str = (size_str or "").upper().strip()
    num_part = "".join(filter(lambda x: x.isdigit() or x == ".", size_str))
    if not num_part:
        return 0

    num = float(num_part)

    if "TB" in size_str or "TIB" in size_str:
        return int(num * (1024**4))
    if "GB" in size_str or "GIB" in size_str:
        return int(num * (1024**3))
    if "MB" in size_str or "MIB" in size_str:
        return int(num * (1024**2))
    if "KB" in size_str or "KIB" in size_str:
        return int(num * 1024)
    if "B" in size_str:  # Bytes
        return int(num)
    return int(num)  # Default to bytes if no unit or unrecognized


class TeraboxResolver(BaseResolver):
    """Resolver for Terabox URLs"""

    # Assuming speed_string_to_bytes is available, e.g. from a utils module
    # For now, using the placeholder defined above.
    _speed_string_to_bytes = _speed_string_to_bytes_placeholder

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Terabox URL"""

        # If the URL already seems to be a direct file link from Terabox (e.g. contains /file/)
        # This was a direct return in the original code.
        # We should still try to fetch details for it.
        if "/file/" in url and (
            "terabox.com" in url or "teraboxapp.com" in url
        ):  # Basic check
            # Consider if these "/file/" URLs are always direct or sometimes need API processing.
            # For now, assume they are direct enough for _fetch_file_details.
            filename, size = await self._fetch_file_details(url)
            return LinkResult(url=url, filename=filename, size=size)

        # API endpoint from the original script
        # Note: Reliance on a third-party Vercel API introduces an external dependency that might break.
        api_url = f"https://wdzone-terabox-api.vercel.app/api?url={quote(url)}"

        try:
            # The original script uses a generic "user_agent". BaseResolver already sets one.
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
                if "error" in json_response:  # Some APIs return an 'error' field
                    error_message = json_response["error"]
                raise ExtractionFailedException(f"Terabox: {error_message}")

            extracted_info = json_response["📜 Extracted Info"]

            if not isinstance(extracted_info, list) or not extracted_info:
                raise ExtractionFailedException(
                    "Terabox API error: '📜 Extracted Info' is not a valid list or is empty.",
                )

            # If only one file in the extracted info, return as LinkResult
            if len(extracted_info) == 1:
                file_data = extracted_info[0]
                direct_link = file_data.get("🔽 Direct Download Link")
                filename = file_data.get("📂 Title")
                size_str = file_data.get("📏 Size", "0")

                if not direct_link:
                    raise ExtractionFailedException(
                        "Terabox API error: Missing download link for single file.",
                    )

                size_bytes = self._speed_string_to_bytes(size_str)

                # Fetch details from the direct link to confirm/get more accurate filename/size if possible
                # Filename from API might be better, but size from HEAD request is more reliable.
                header_filename, header_size = await self._fetch_file_details(
                    direct_link,
                )

                return LinkResult(
                    url=direct_link,
                    filename=header_filename if header_filename else filename,
                    size=header_size if header_size is not None else size_bytes,
                )

            # If multiple files, return as FolderResult
            folder_contents: list[FileItem] = []
            total_size_bytes = 0
            folder_title = extracted_info[0].get(
                "📂 Title",
                "Terabox Folder",
            )  # Use first item's title for folder, or a generic one

            for item_data in extracted_info:
                item_link = item_data.get("🔽 Direct Download Link")
                item_filename = item_data.get("📂 Title")
                item_size_str = item_data.get("📏 Size", "0")

                if not item_link or not item_filename:
                    # Skip item if essential data is missing
                    continue

                item_size_bytes = self._speed_string_to_bytes(item_size_str)

                # For folder items, we might not want to call _fetch_file_details for each one
                # to save time, unless sizes are critical and often wrong from API.
                # For now, trust API size for folder items.
                folder_contents.append(
                    FileItem(
                        filename=item_filename,
                        url=item_link,
                        size=item_size_bytes
                        if item_size_bytes > 0
                        else None,  # Use None if size is 0 or invalid
                        path="",  # API doesn't seem to provide paths, assuming flat structure
                    ),
                )
                total_size_bytes += item_size_bytes

            if not folder_contents:
                raise ExtractionFailedException(
                    "Terabox: No valid files found in folder data from API.",
                )

            return FolderResult(
                title=folder_title,
                contents=folder_contents,
                total_size=total_size_bytes,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Terabox URL '{url}': {e!s}",
            ) from e

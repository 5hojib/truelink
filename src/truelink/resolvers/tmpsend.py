from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class TmpSendResolver(BaseResolver):
    """Resolver for TmpSend.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve TmpSend.com URL"""
        try:
            parsed_url = urlparse(url)
            file_id = None

            # Check if URL is in "thank-you" or "download" format with query parameter 'd'
            if parsed_url.path.strip("/") in ["thank-you", "download"]:
                query_params = parse_qs(parsed_url.query)
                file_id_list = query_params.get("d")
                if file_id_list:
                    file_id = file_id_list[0]
            else:  # Assume it's a direct share link like tmpsend.com/fileId
                # Path might be just "/fileId" or "/fileId/"
                path_segments = [seg for seg in parsed_url.path.split("/") if seg]
                if path_segments:
                    file_id = path_segments[0]  # Takes the first segment as ID

            if not file_id:
                raise InvalidURLException(
                    f"TmpSend error: Could not extract file ID from URL '{url}'. "
                    "Expected format like /fileId, /thank-you?d=fileId, or /download?d=fileId.",
                )

            # Construct the direct download link and the referer URL
            # Based on original script:
            #   Referer: https://tmpsend.com/thank-you?d={file_id}
            #   Download: https://tmpsend.com/download?d={file_id}

            referer_url = f"https://tmpsend.com/thank-you?d={file_id}"
            direct_download_link = f"https://tmpsend.com/download?d={file_id}"

            # TmpSend links might be direct or might require the referer.
            # _fetch_file_details will use this referer.
            custom_headers = {"Referer": referer_url}
            filename, size = await self._fetch_file_details(
                direct_download_link,
                custom_headers=custom_headers,
            )

            # If filename is not found, it might be in the original URL or page title (if we were to fetch it)
            # For now, relying on Content-Disposition from _fetch_file_details.
            # TmpSend often uses Content-Disposition like "attachment; filename="actual_filename.ext""

            return LinkResult(url=direct_download_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve TmpSend.com URL '{url}': {e!s}",
            ) from e

from __future__ import annotations

from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class TmpSendResolver(BaseResolver):
    """Resolver for TmpSend.com URLs"""

    DOMAINS: ClassVar[list[str]] = ["tmpsend.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve TmpSend.com URL"""
        try:
            parsed_url = urlparse(url)
            file_id = None

            if parsed_url.path.strip("/") in ["thank-you", "download"]:
                query_params = parse_qs(parsed_url.query)
                file_id_list = query_params.get("d")
                if file_id_list:
                    file_id = file_id_list[0]
            else:
                path_segments = [seg for seg in parsed_url.path.split("/") if seg]
                if path_segments:
                    file_id = path_segments[0]

            if not file_id:
                raise InvalidURLException(
                    f"TmpSend error: Could not extract file ID from URL '{url}'. "
                    "Expected format like /fileId, /thank-you?d=fileId, or /download?d=fileId.",
                )

            referer_url = f"https://tmpsend.com/thank-you?d={file_id}"
            direct_download_link = f"https://tmpsend.com/download?d={file_id}"

            headers = {"Referer": referer_url}
            filename, size, mime_type = await self._fetch_file_details(
                direct_download_link,
                headers=headers,
            )

            return LinkResult(
                url=direct_download_link,
                filename=filename,
                mime_type=mime_type,
                size=size,
                headers=headers,
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve TmpSend.com URL '{url}': {e!s}",
            ) from e

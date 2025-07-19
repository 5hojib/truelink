from __future__ import annotations

from typing import ClassVar
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# todo
class OneDriveResolver(BaseResolver):
    """Resolver for OneDrive (1drv.ms) URLs"""

    DOMAINS: ClassVar[list[str]] = ["1drv.ms", "onedrive.live.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve OneDrive URL"""
        try:
            async with await self._get(url) as initial_response:
                final_url_after_redirects = str(initial_response.url)

            parsed_link = urlparse(final_url_after_redirects)
            link_data = parse_qs(parsed_link.query)

            if not link_data:
                raise ExtractionFailedException(
                    "OneDrive error: Unable to find link_data (query parameters) in the URL.",
                )

            folder_id_list = link_data.get("resid")
            if not folder_id_list:
                raise ExtractionFailedException(
                    "OneDrive error: 'resid' not found in URL query parameters.",
                )
            folder_id = folder_id_list[0]

            authkey_list = link_data.get("authkey")
            if not authkey_list:
                raise ExtractionFailedException(
                    "OneDrive error: 'authkey' not found in URL query parameters.",
                )
            authkey = authkey_list[0]

            drive_id_part = folder_id.split("!", 1)[0]
            api_url = f"https://api.onedrive.com/v1.0/drives/{drive_id_part}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}"

            api_headers = {"User-Agent": self.USER_AGENT}

            try:
                async with await self._get(
                    api_url,
                    headers=api_headers,
                ) as api_response:
                    if api_response.status == 200:
                        json_resp = await api_response.json()
                    else:
                        boundary = str(uuid4())
                        custom_body_parts = [
                            f"--{boundary}",
                            'Content-Disposition: form-data; name="data"',
                            "Prefer: Migration=EnableRedirect;FailOnMigratedFiles",
                            "X-HTTP-Method-Override: GET",
                            "Content-Type: application/json",
                            "",
                            "{}",
                            f"--{boundary}--",
                            "",
                        ]
                        custom_body = "\r\n".join(custom_body_parts).encode("utf-8")

                        override_headers = {
                            "User-Agent": self.USER_AGENT,
                            "Content-Type": f"multipart/form-data; boundary={boundary}",
                        }
                        async with await self._post(
                            api_url,
                            data=custom_body,
                            headers=override_headers,
                        ) as post_api_response:
                            if post_api_response.status != 200:
                                error_text = await post_api_response.text()
                                raise ExtractionFailedException(
                                    f"OneDrive API error (after trying override). Status: {post_api_response.status}. Response: {error_text[:200]}",
                                )
                            json_resp = await post_api_response.json()

            except Exception as e_api:
                if isinstance(e_api, ExtractionFailedException):
                    raise
                raise ExtractionFailedException(
                    f"OneDrive API request failed: {e_api!s}",
                ) from e_api

            if "@content.downloadUrl" not in json_resp:
                err_msg = json_resp.get("error", {}).get(
                    "message",
                    "Direct download link ('@content.downloadUrl') not found in OneDrive API response.",
                )
                raise ExtractionFailedException(err_msg)

            direct_link = json_resp["@content.downloadUrl"]

            filename = json_resp.get("name")
            size = json_resp.get("size")

            if not filename or size is None:
                details_filename, details_size, _ = await self._fetch_file_details(
                    direct_link,
                )
                if details_filename and not filename:
                    filename = details_filename
                if details_size is not None and size is None:
                    size = details_size

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve OneDrive URL '{url}': {e!s}",
            ) from e

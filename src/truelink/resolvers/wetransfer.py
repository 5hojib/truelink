from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# ToDo
class WeTransferResolver(BaseResolver):
    """Resolver for WeTransfer.com URLs"""

    DOMAINS: ClassVar[list[str]] = ["wetransfer.com", "we.tl"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve WeTransfer.com URL"""
        try:
            async with await self._get(url) as initial_response:
                canonical_url = str(initial_response.url)

            parsed_url = urlparse(canonical_url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if len(path_segments) < 2 or path_segments[0] != "downloads":
                if not path_segments or path_segments[0] != "downloads":
                    raise InvalidURLException(
                        f"Invalid WeTransfer URL format. Expected '/downloads/...' path: {canonical_url}",
                    )

                if len(path_segments) >= 3:
                    transfer_id = path_segments[1]
                    security_hash = path_segments[2]
                    if len(path_segments) >= 4:
                        security_hash = path_segments[3]
                elif len(path_segments) == 2 and path_segments[0] == "downloads":
                    raise InvalidURLException(
                        f"WeTransfer URL does not seem to contain a security hash: {canonical_url}",
                    )
                else:
                    raise InvalidURLException(
                        f"Could not parse transfer_id and security_hash from WeTransfer URL: {canonical_url}",
                    )

            api_url = (
                f"https://wetransfer.com/api/v4/transfers/{transfer_id}/download"
            )
            json_data = {"security_hash": security_hash, "intent": "entire_transfer"}

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }

            async with await self._post(
                api_url,
                json=json_data,
                headers=headers,
            ) as api_response:
                if api_response.status != 200:
                    error_text = await api_response.text()
                    try:
                        json_err_data = await api_response.json(content_type=None)
                        if "message" in json_err_data:
                            error_text = json_err_data["message"]
                        elif "error" in json_err_data:
                            error_text = json_err_data["error"]
                    except Exception:
                        pass
                    raise ExtractionFailedException(
                        f"WeTransfer API error ({api_response.status}): {error_text[:300]}",
                    )

                try:
                    json_resp_data = await api_response.json()
                except Exception as e_json:
                    err_txt = await api_response.text()
                    raise ExtractionFailedException(
                        f"WeTransfer API error: Failed to parse JSON. {e_json}. Response: {err_txt[:200]}",
                    )

            if "direct_link" in json_resp_data:
                direct_link = json_resp_data["direct_link"]
                filename = json_resp_data.get("display_name") or json_resp_data.get(
                    "name",
                )
                size_api = json_resp_data.get("size")

                header_filename, header_size, _ = await self._fetch_file_details(
                    direct_link,
                )

                final_filename = header_filename if header_filename else filename
                final_size = header_size if header_size is not None else size_api

                return LinkResult(
                    url=direct_link,
                    filename=final_filename,
                    size=final_size,
                )

            if "message" in json_resp_data:
                raise ExtractionFailedException(
                    f"WeTransfer API error: {json_resp_data['message']}",
                )
            if "error" in json_resp_data:
                raise ExtractionFailedException(
                    f"WeTransfer API error: {json_resp_data['error']}",
                )

            raise ExtractionFailedException(
                "WeTransfer error: 'direct_link' not found in API response and no specific error message.",
            )

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve WeTransfer URL '{url}': {e!s}",
            ) from e

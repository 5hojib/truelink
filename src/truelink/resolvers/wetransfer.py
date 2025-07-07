from __future__ import annotations

from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class WeTransferResolver(BaseResolver):
    """Resolver for WeTransfer.com URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve WeTransfer.com URL"""
        try:
            # Follow initial redirects (e.g., from we.tl shortlinks)
            async with await self._get(url) as initial_response:
                canonical_url = str(
                    initial_response.url,
                )  # This is the main transfer page URL

            parsed_url = urlparse(canonical_url)
            path_segments = [seg for seg in parsed_url.path.split("/") if seg]

            if len(path_segments) < 2 or path_segments[0] != "downloads":
                # Standard WeTransfer links look like: https://wetransfer.com/downloads/<transfer_id>/<security_hash>
                # Or sometimes /<transfer_id>/<email_id>/<security_hash>
                # The original code splits and takes splited_url[-2] as transfer_id and splited_url[-1] as security_hash.
                # This assumes a certain path structure.
                # Let's refine ID and hash extraction.
                # Example: /downloads/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6/x1y2z3
                # transfer_id = a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
                # security_hash = x1y2z3 (or could be an email hash)

                # A common structure is /downloads/[transfer_id]/[recipient_id_or_security_hash]/[security_hash_if_recipient_id_present]
                # For simplicity, we'll assume the last two parts are the transfer_id and security_hash respectively if path is long enough
                # Or if it's /downloads/transfer_id/security_hash

                # Let's try to find the transfer ID (usually a long hex string) and hash
                # The transfer ID is what's used in the API path. The security hash is in the JSON body.
                if not path_segments or path_segments[0] != "downloads":
                    raise InvalidURLException(
                        f"Invalid WeTransfer URL format. Expected '/downloads/...' path: {canonical_url}",
                    )

                if (
                    len(path_segments) >= 3
                ):  # e.g. /downloads/transferId/securityHash
                    transfer_id = path_segments[1]
                    security_hash = path_segments[
                        2
                    ]  # This might be recipient_id if path is longer
                    if (
                        len(path_segments) >= 4
                    ):  # /downloads/transferId/recipientId/securityHash
                        security_hash = path_segments[3]
                elif (
                    len(path_segments) == 2 and path_segments[0] == "downloads"
                ):  # /downloads/transferId (security hash might be missing or implied)
                    # This case is less common for direct user links.
                    # The API call requires a security_hash in the JSON body.
                    # The original script took splitted_url[-1] as security_hash.
                    # If canonical_url itself is /downloads/transfer_id, it's problematic.
                    # For now, assume the URL must contain the hash part.
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
            json_data = {
                "security_hash": security_hash,
                "intent": "entire_transfer",  # As per original script
            }

            # WeTransfer API might require specific headers, e.g., CSRF token, if interacting via browser.
            # For direct API call, usually User-Agent and Content-Type are enough.
            # The session in BaseResolver handles User-Agent.
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",  # Common for API calls
            }

            async with await self._post(
                api_url,
                json=json_data,
                headers=headers,
            ) as api_response:
                if api_response.status != 200:
                    error_text = await api_response.text()
                    try:  # Try to parse JSON error from WeTransfer
                        json_err_data = await api_response.json(
                            content_type=None,
                        )  # Allow any content type for error
                        if "message" in json_err_data:
                            error_text = json_err_data["message"]
                        elif "error" in json_err_data:
                            error_text = json_err_data["error"]
                    except Exception:
                        pass  # Use raw error_text if not JSON
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
                # WeTransfer direct links are usually pre-signed and have filename in Content-Disposition.
                # The API response might also contain filename and size.
                filename = json_resp_data.get("display_name") or json_resp_data.get(
                    "name",
                )
                size_api = json_resp_data.get("size")  # Typically in bytes

                # Fetch details from the link to confirm/get more accurate info
                header_filename, header_size = await self._fetch_file_details(
                    direct_link,
                )

                final_filename = header_filename if header_filename else filename
                final_size = header_size if header_size is not None else size_api

                return LinkResult(
                    url=direct_link,
                    filename=final_filename,
                    size=final_size,
                )

            # Handle other API responses (errors, etc.)
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

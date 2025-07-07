from __future__ import annotations

from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class ShrdskResolver(BaseResolver):
    """Resolver for Shrdsk.me URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Shrdsk.me URL"""
        try:
            parsed_url = urlparse(url)
            path_segments = parsed_url.path.split("/")
            short_id = None
            if path_segments:
                short_id = path_segments[-1]  # Assumes ID is the last part

            if not short_id:
                raise InvalidURLException(
                    f"Could not extract short ID from Shrdsk.me URL: {url}",
                )

            # Step 1: Call the cloud function API
            # Note: Reliance on a specific cloud function URL (affiliate2apk) can be brittle.
            api1_url = f"https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={short_id}"

            async with await self._get(api1_url) as api_res1:
                if api_res1.status != 200:
                    err_text = await api_res1.text()
                    raise ExtractionFailedException(
                        f"Shrdsk API1 (cloud function) error ({api_res1.status}): {err_text[:200]}",
                    )
                try:
                    json_res1 = await api_res1.json()
                except Exception as e_json:
                    err_txt = await api_res1.text()
                    raise ExtractionFailedException(
                        f"Shrdsk API1 error: Failed to parse JSON. {e_json}. Response: {err_txt[:200]}",
                    )

            if "download_data" not in json_res1 or not json_res1["download_data"]:
                error_msg = json_res1.get(
                    "error",
                    "Missing 'download_data' in API1 response or data is empty.",
                )
                raise ExtractionFailedException(f"Shrdsk API1 error: {error_msg}")

            download_data_param = json_res1["download_data"]

            # Step 2: GET request to shrdsk.me/download/... with allow_redirects=False
            # The domain for this step might need to be confirmed if shrdsk.me has mirrors or changes.
            # For now, using shrdsk.me as per original.
            download_page_url = f"https://shrdsk.me/download/{download_data_param}"

            async with await self._get(
                download_page_url,
                allow_redirects=False,
            ) as download_res:
                # We expect a redirect (3xx status) with a 'Location' header
                if not (
                    300 <= download_res.status < 400
                    and "Location" in download_res.headers
                ):
                    # If not a redirect, something is wrong. Maybe the page shows an error.
                    page_text = await download_res.text()
                    if (
                        "File not found" in page_text
                        or "link has expired" in page_text
                    ):
                        raise ExtractionFailedException(
                            "Shrdsk error: File not found or link expired on download page.",
                        )
                    raise ExtractionFailedException(
                        f"Shrdsk error: Expected redirect from {download_page_url} but got status {download_res.status}. "
                        f"Response: {page_text[:200]}",
                    )

                direct_link = download_res.headers["Location"]

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": download_page_url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Shrdsk.me URL '{url}': {e!s}",
            ) from e

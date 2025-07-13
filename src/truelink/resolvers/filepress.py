from __future__ import annotations

from urllib.parse import urlparse

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# Todo
class FilePressResolver(BaseResolver):
    """Resolver for FilePress URLs (via filebee.xyz)"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve FilePress URL"""
        try:
            file_id_match = url.split("/")
            if not file_id_match or not file_id_match[-1]:
                raise InvalidURLException(
                    "FilePress error: Could not extract file ID from URL.",
                )
            file_id = file_id_match[-1]

            filebee_url = f"https://filebee.xyz/file/{file_id}"
            async with await self._get(filebee_url) as fb_response:
                resolved_filebee_url = str(fb_response.url)

            parsed_fb_url = urlparse(resolved_filebee_url)
            api_file_id = parsed_fb_url.path.split("/")[-1]
            if not api_file_id:
                raise ExtractionFailedException(
                    "FilePress error: Could not determine API file ID from filebee URL.",
                )

            api_base_scheme = parsed_fb_url.scheme
            api_base_host = parsed_fb_url.hostname

            api1_url = f"{api_base_scheme}://{api_base_host}/api/file/downlaod/"
            json_data1 = {"id": api_file_id, "method": "publicDownlaod"}
            headers1 = {"Referer": f"{api_base_scheme}://{api_base_host}"}

            async with await self._post(
                api1_url,
                json=json_data1,
                headers=headers1,
            ) as api_res1:
                if api_res1.status != 200:
                    err_txt = await api_res1.text()
                    raise ExtractionFailedException(
                        f"FilePress API1 error ({api_res1.status}): {err_txt[:200]}",
                    )
                try:
                    json_res1 = await api_res1.json()
                except Exception as e_json:
                    err_txt = await api_res1.text()
                    raise ExtractionFailedException(
                        f"FilePress API1 error: Failed to parse JSON. {e_json}. Response: {err_txt[:200]}",
                    )

            if "data" not in json_res1 or not json_res1["data"]:
                status_text = json_res1.get(
                    "statusText",
                    "Missing 'data' in API1 response or data is empty.",
                )
                raise ExtractionFailedException(
                    f"FilePress API1 error: {status_text}",
                )

            intermediate_id = json_res1["data"]

            api2_url = f"{api_base_scheme}://{api_base_host}/api/file/downlaod2/"
            json_data2 = {"id": intermediate_id, "method": "publicDownlaod"}
            headers2 = {"Referer": f"{api_base_scheme}://{api_base_host}"}

            async with await self._post(
                api2_url,
                json=json_data2,
                headers=headers2,
            ) as api_res2:
                if api_res2.status != 200:
                    err_txt = await api_res2.text()
                    raise ExtractionFailedException(
                        f"FilePress API2 error ({api_res2.status}): {err_txt[:200]}",
                    )
                try:
                    json_res2 = await api_res2.json()
                except Exception as e_json:
                    err_txt = await api_res2.text()
                    raise ExtractionFailedException(
                        f"FilePress API2 error: Failed to parse JSON. {e_json}. Response: {err_txt[:200]}",
                    )

            if "data" not in json_res2 or not json_res2["data"]:
                status_text = json_res2.get(
                    "statusText",
                    "Missing 'data' in API2 response or data is empty.",
                )
                raise ExtractionFailedException(
                    f"FilePress API2 error: {status_text}",
                )

            gdrive_file_id = json_res2["data"]
            direct_link = (
                f"https://drive.google.com/uc?id={gdrive_file_id}&export=download"
            )

            filename, size, _ = await self._fetch_file_details(direct_link)

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve FilePress URL '{url}': {e!s}",
            ) from e

from __future__ import annotations

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class DevUploadsResolver(BaseResolver):
    """Resolver for DevUploads URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve DevUploads URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()
            html = fromstring(response_text)

            if not (form_inputs := html.xpath("//input[@name]")):
                raise ExtractionFailedException(
                    "Unable to find link data on initial page",
                )

            data = {i.get("name"): i.get("value") for i in form_inputs}

            async with await self._post(
                "https://gujjukhabar.in/",
                data=data,
            ) as response_gujju:
                response_gujju_text = await response_gujju.text()

            html_gujju = fromstring(response_gujju_text)
            if not (form_inputs_gujju := html_gujju.xpath("//input[@name]")):
                raise ExtractionFailedException(
                    "Unable to find link data on gujjukhabar.in",
                )

            data_gujju = {i.get("name"): i.get("value") for i in form_inputs_gujju}

            headers_du2 = {
                "Origin": "https://gujjukhabar.in",
                "Referer": "https://gujjukhabar.in/",
            }
            async with await self._get(
                "https://du2.devuploads.com/dlhash.php",
                headers=headers_du2,
            ) as resp_ipp:
                ipp_text = await resp_ipp.text()
                if not ipp_text:
                    raise ExtractionFailedException("Unable to find ipp value")
            data_gujju["ipp"] = ipp_text.strip()

            if not data_gujju.get("rand"):
                raise ExtractionFailedException(
                    "Unable to find rand value in form data",
                )

            async with await self._post(
                "https://devuploads.com/token/token.php",
                data={"rand": data_gujju["rand"], "msg": ""},
                headers=headers_du2,
            ) as resp_xd:
                xd_text = await resp_xd.text()
                if not xd_text:
                    raise ExtractionFailedException("Unable to find xd value")
            data_gujju["xd"] = xd_text.strip()

            async with await self._post(url, data=data_gujju) as final_response:
                final_response_text = await final_response.text()

            html_final = fromstring(final_response_text)
            if not (
                direct_link_elements := html_final.xpath(
                    "//input[@name='orilink']/@value",
                )
            ):
                raise ExtractionFailedException(
                    "Unable to find Direct Link in final page",
                )

            direct_link = direct_link_elements[0]

            filename, size = await self._fetch_file_details(direct_link)
            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve DevUploads URL '{url}': {e!s}",
            ) from e

from __future__ import annotations

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class OsdnResolver(BaseResolver):
    """Resolver for OSDN.net URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve OSDN.net URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            html = fromstring(response_text)

            # Original code had a typo: .xapth, correcting to .xpath
            mirror_link_elements = html.xpath('//a[@class="mirror_link"]/@href')

            if not mirror_link_elements:
                # Fallback: Check for a direct download button if the primary mirror link class isn't found
                # This is a guess, actual OSDN pages might have other structures
                fallback_links = html.xpath(
                    '//a[contains(@href, "dl.osdn.net") and contains(@class, "btn")]/@href',
                )
                if not fallback_links:
                    raise ExtractionFailedException(
                        "OSDN error: Direct download link or mirror link not found.",
                    )

                # Assuming the first fallback link is the one
                # It might be a relative or full URL
                direct_link_path = fallback_links[0]
            else:
                direct_link_path = mirror_link_elements[0]

            # The extracted link might be relative
            if direct_link_path.startswith("/"):
                direct_link = f"https://osdn.net{direct_link_path}"
            elif not direct_link_path.startswith("http"):
                # If it's not absolute and not starting with /, it might be relative to current path
                # This case might need more specific handling based on OSDN's URL structure
                # For now, assuming it's relative to hostname if not starting with /
                parsed_original_url = self.session._prepare_url(url)  # type: ignore
                base_url_parts = parsed_original_url.parts
                direct_link = f"{base_url_parts.scheme}://{base_url_parts.host}/{direct_link_path}"
            else:
                direct_link = direct_link_path

            # OSDN links often redirect. _fetch_file_details will handle redirects.
            filename, size = await self._fetch_file_details(direct_link)

            # If filename is not found from headers, try to derive from link
            if not filename and direct_link:
                try:
                    # Example: https://osdn.net/projects/manjarolinux/storage/Manjaro-LXQt-20.2-201201-linux59.iso/
                    # Example direct: http://jaist.dl.osdn.jp/manjarolinux/74185/Manjaro-LXQt-20.2-201201-linux59.iso
                    # Try to get the last part of the path from the direct_link
                    parsed_dl_url = self.session._prepare_url(direct_link)  # type: ignore
                    path_segments = [s for s in parsed_dl_url.path.split("/") if s]
                    if path_segments:
                        filename = path_segments[-1]
                except Exception:
                    pass

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve OSDN.net URL '{url}': {e!s}",
            ) from e

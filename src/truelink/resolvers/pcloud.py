from __future__ import annotations

import json
import re
from typing import ClassVar
from urllib.parse import unquote, urlparse

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


# todo
class PCloudResolver(BaseResolver):
    """Resolver for pCloud.link URLs"""

    DOMAINS: ClassVar[list[str]] = ["u.pcloud.link", "pcloud.com"]

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve pCloud.link URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            direct_link = None

            script_json_match = re.search(
                r"<script[^>]*>\s*(?:var\s+|window\.)?\w+\s*=\s*(\{.*?\});?\s*</script>",
                response_text,
                re.DOTALL | re.IGNORECASE,
            )
            if script_json_match:
                try:
                    json_str = script_json_match.group(1)
                    metadata = json.loads(json_str)
                    if "downloadlink" in metadata and isinstance(
                        metadata["downloadlink"],
                        str,
                    ):
                        direct_link = metadata["downloadlink"]
                    elif "downloadLink" in metadata and isinstance(
                        metadata["downloadLink"],
                        str,
                    ):
                        direct_link = metadata["downloadLink"]

                    if direct_link and r"\/" in direct_link:
                        direct_link = direct_link.replace(r"\/", "/")

                except json.JSONDecodeError:
                    pass
                except TypeError:
                    pass

            if not direct_link:
                matches = re.findall(
                    r"""
                    (?:["']?download(?:L|l)ink["']?\s*[:=]\s*["'](https:[^"']+)["'])
                    |
                    (?:downloadlink\s*=\s*\(?(["']https:[^"']+)["']\)?)
                    """,
                    response_text,
                    re.VERBOSE,
                )

                if matches:
                    for match_tuple in matches:
                        for link_candidate in match_tuple:
                            if link_candidate:
                                direct_link = link_candidate
                                break
                        if direct_link:
                            break

            if not direct_link:
                cdn_links = re.findall(
                    r'["\'](https://[a-zA-Z0-9.-]+\.pcloud.com/[^"\']+)["\']',
                    response_text,
                )
                if cdn_links:
                    for cdn_link in cdn_links:
                        if (
                            any(
                                ext in cdn_link.lower()
                                for ext in [
                                    ".zip",
                                    ".rar",
                                    ".exe",
                                    ".iso",
                                    ".mp4",
                                    ".mkv",
                                ]
                            )
                            or "download=1" in cdn_link
                        ):
                            direct_link = cdn_link
                            break
                    if not direct_link and cdn_links:
                        direct_link = cdn_links[0]

            if not direct_link:
                raise ExtractionFailedException(
                    "pCloud.link error: Direct download link not found in page source.",
                )

            if r"\/" in direct_link:
                direct_link = direct_link.replace(r"\/", "/")

            direct_link = unquote(direct_link)

            filename, size, _ = await self._fetch_file_details(
                direct_link,
                headers={"Referer": url},
            )

            if not filename and direct_link:
                try:
                    path_part = urlparse(direct_link).path
                    if path_part and path_part != "/":
                        potential_filename = path_part.split("/")[-1]
                        if (
                            "." in potential_filename
                            and not potential_filename.split(".")[0].isdigit()
                        ):
                            filename = potential_filename
                except Exception:
                    pass

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve pCloud.link URL '{url}': {e!s}",
            ) from e

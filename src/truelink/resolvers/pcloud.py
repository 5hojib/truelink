from __future__ import annotations

import json  # For attempting to parse JSON if applicable
import re
from urllib.parse import unquote

from truelink.exceptions import ExtractionFailedException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class PCloudResolver(BaseResolver):
    """Resolver for pCloud.link URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve pCloud.link URL"""
        try:
            async with await self._get(url) as response:
                response_text = await response.text()

            # Original regex: r".downloadlink.:..(https:.*).."
            # This seems to be looking for something like: "downloadlink":"https:\/\/..."
            # Let's try a more specific regex for JSON-like structures first.
            # PCloud often embeds metadata as JSON in a script tag.

            direct_link = None

            # Try to find JSON metadata which is common for pCloud share links
            # Look for <script type="text/javascript">var metadata = {...};</script>
            # Or similar inline JSON data.
            script_json_match = re.search(
                r"<script[^>]*>\s*(?:var\s+|window\.)?\w+\s*=\s*(\{.*?\});?\s*</script>",
                response_text,
                re.DOTALL | re.IGNORECASE,
            )
            if script_json_match:
                try:
                    json_str = script_json_match.group(1)
                    # Clean up potential JS comments or non-standard JSON parts if necessary
                    # For now, assume it's mostly valid JSON.
                    metadata = json.loads(json_str)
                    # Look for download link paths within the metadata structure.
                    # Common keys: 'downloadlink', 'downloadLink', 'href' inside objects.
                    # This requires knowledge of pCloud's metadata structure.
                    # Example from some pCloud pages: metadata.variants[0].hosts[0] + metadata.variants[0].path
                    # Or metadata.downloadlink
                    if "downloadlink" in metadata and isinstance(
                        metadata["downloadlink"],
                        str,
                    ):
                        direct_link = metadata["downloadlink"]
                    elif "downloadLink" in metadata and isinstance(
                        metadata["downloadLink"],
                        str,
                    ):  # Camel case
                        direct_link = metadata["downloadLink"]
                    # Add more specific JSON path checks if known.

                    # If link has escaped slashes
                    if direct_link and r"\/" in direct_link:
                        direct_link = direct_link.replace(r"\/", "/")

                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to the original regex or other methods
                    pass
                except TypeError:  # If metadata structure is not as expected
                    pass

            if not direct_link:
                # Fallback to original regex if JSON parsing didn't yield a link
                # Original: findall(r".downloadlink.:..(https:.*)..", res.text)
                # This regex is a bit broad. Let's refine it slightly to be more specific
                # for common patterns like "downloadlink":"https..." or downloadlink = 'https...'
                matches = re.findall(
                    r"""
                    (?:["']?download(?:L|l)ink["']?\s*[:=]\s*["'](https:[^"']+)["']) # "downloadlink":"https..." or 'downloadlink':'https...'
                    |                                                              # OR
                    (?:downloadlink\s*=\s*\(?(["']https:[^"']+)["']\)?)             # downloadlink = 'https...' (optional parens)
                    """,
                    response_text,
                    re.VERBOSE,
                )

                if matches:
                    # findall returns list of tuples if multiple capture groups are used.
                    # Each tuple contains captures from one match. We need the first non-empty capture.
                    for match_tuple in matches:
                        for link_candidate in match_tuple:
                            if link_candidate:
                                direct_link = link_candidate
                                break
                        if direct_link:
                            break

            if not direct_link:
                # Last resort: Look for any link that seems to be a direct download from pCloud's CDNs
                cdn_links = re.findall(
                    r'["\'](https://[a-zA-Z0-9.-]+\.pcloud.com/[^"\']+)["\']',
                    response_text,
                )
                if cdn_links:
                    # This is a guess, might pick up non-download links.
                    # Prioritize links that look like file downloads (e.g., containing typical file extensions or query params like 'download=1')
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
                    if (
                        not direct_link and cdn_links
                    ):  # If no specific pattern, take the first one
                        direct_link = cdn_links[0]

            if not direct_link:
                raise ExtractionFailedException(
                    "pCloud.link error: Direct download link not found in page source.",
                )

            # Unescape slashes if any (though already handled if from JSON path)
            if r"\/" in direct_link:
                direct_link = direct_link.replace(r"\/", "/")

            # Sometimes links might be URL encoded
            direct_link = unquote(direct_link)

            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": url},
            )

            # pCloud filenames from Content-Disposition are often URL-encoded or base64.
            # _fetch_file_details handles basic unquoting. If more complex, it might need adjustment.
            # If filename is still None, try to get it from the URL path if it looks like a filename.
            if not filename and direct_link:
                try:
                    path_part = urlparse(direct_link).path
                    if path_part and path_part != "/":
                        potential_filename = path_part.split("/")[-1]
                        # Avoid using generic names like 'download.php' or just numbers as filename
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

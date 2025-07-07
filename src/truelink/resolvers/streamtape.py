from __future__ import annotations

import re
from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult  # FolderResult for type hint

from .base import BaseResolver


class StreamtapeResolver(BaseResolver):
    """Resolver for Streamtape URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Streamtape URL"""
        try:
            parsed_original_url = urlparse(url)
            path_segments = parsed_original_url.path.split("/")

            # Streamtape URLs can be like:
            # /v/VIDEO_ID/filename.mp4
            # /e/VIDEO_ID/ (embed)
            # The original code:
            # splitted_url = url.split("/")
            # _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]
            # This logic for ID extraction seems a bit fragile.
            # Let's try to find 'v' or 'e' and take the next segment as ID.
            _id = None
            for i, segment in enumerate(path_segments):
                if (segment in {"v", "e"}) and i + 1 < len(path_segments):
                    _id = path_segments[i + 1]
                    break

            if not _id:
                # Fallback: if no /v/ or /e/, take the last non-empty part of the path as ID
                # This might catch URLs that are just streamtape.com/VIDEO_ID
                cleaned_path_segments = [s for s in path_segments if s]
                if cleaned_path_segments:
                    _id = cleaned_path_segments[-1]
                else:
                    raise InvalidURLException(
                        f"Could not extract video ID from Streamtape URL: {url}",
                    )

            # Ensure we use the main page URL, not embed if possible, for fetching the script
            # Typically, the script is on the /v/ page. If it's /e/, it might be the same or redirect.
            # For safety, let's try constructing a /v/ URL if it was /e/
            page_url = f"{parsed_original_url.scheme}://{parsed_original_url.netloc}/v/{_id}/"

            async with await self._get(page_url) as response:  # Use page_url
                html_text = await response.text()
            html = fromstring(html_text)

            # Original: script = html.xpath("//script[contains(text(),'ideoooolink')]/text()") or html.xpath("//script[contains(text(),'ideoolink')]/text()")
            # The 'ideoooolink' or 'ideoolink' seems to be a key part of the script.
            # Let's find script tags and check their content.
            scripts_content = html.xpath("//script/text()")
            target_script_content = None
            for script_text in scripts_content:
                if script_text and (
                    "ideoooolink" in script_text or "ideoolink" in script_text
                ):
                    target_script_content = script_text
                    break

            if not target_script_content:
                # Fallback: Sometimes the relevant script might not have 'ideoooolink' but other patterns.
                # This part is highly dependent on Streamtape's current obfuscation.
                # If the specific strings are not found, try a more generic JS variable extraction if possible.
                # For now, sticking to original identified patterns.
                raise ExtractionFailedException(
                    "Streamtape error: Required script content not found on page.",
                )

            # Original: findall(r"(&expires\S+)'", script[0]) -> script[0] was target_script_content
            # The regex looks for something like &expires=...&ip=...&token=...'
            # and captures the part starting with &expires up to before the closing quote.
            # Example: document.getElementById('ideoooolink').innerHTML = "/streamtape.com/get_video?id=VIDEO_ID&expires=..."
            # We need to find the full part including /get_video?id=...

            # Let's try to find the full 'src' or 'innerHTML' assignment for 'ideoooolink' or 'ideoolink'
            link_match = re.search(
                r"document\.getElementById\(['\"](?:ideoooolink|ideoolink)['\"]\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]",
                target_script_content,
            )

            if not link_match:
                # Fallback: try to find a URL looking like /get_video?id=...&expires=...
                # This is more generic but might pick up wrong links if the page is complex.
                # The original regex `(&expires\S+)'` implies the ID part is already known/prepended.
                # Let's try to extract the part after ID.
                # The script usually has something like: `...blahblah...'blahblah...' + '/get_video?id=XYZ' + '&expires=...'`
                # or `...innerHTML = '/get_video?id=XYZ&expires=...'`

                # Regex to find the part starting from &expires or similar parameters
                # The original regex was `r"(&expires\S+)'"`. This means it expected the ID part to be prepended.
                # Let's refine this to find the whole query string part.
                # A common pattern is `'/get_video?id=ID&expires=...&token=...'`

                # Try to find the full /get_video string
                full_link_pattern = (
                    r"['\"](/get_video\?id=" + re.escape(_id) + r"[^'\"]+)['\"]"
                )
                match_get_video = re.search(full_link_pattern, target_script_content)

                if not match_get_video:
                    raise ExtractionFailedException(
                        "Streamtape error: Download link pattern not found in script.",
                    )

                # This is the path and query part, e.g., /get_video?id=...&expires=...
                link_path_and_query = match_get_video.group(1)
            else:
                link_path_and_query = link_match.group(1)

            # Ensure the link is absolute
            if link_path_and_query.startswith("//"):
                direct_link = f"{parsed_original_url.scheme}:{link_path_and_query}"
            elif link_path_and_query.startswith("/"):
                direct_link = f"{parsed_original_url.scheme}://{parsed_original_url.netloc}{link_path_and_query}"
            else:  # Should not happen if extracted correctly
                direct_link = link_path_and_query

            # The direct_link should now be the full URL to get_video.
            # _fetch_file_details will hit this. Streamtape might require specific referers.
            # The original code doesn't specify a referer for the final link.
            filename, size = await self._fetch_file_details(
                direct_link,
                custom_headers={"Referer": page_url},
            )

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve Streamtape URL '{url}': {e!s}",
            ) from e

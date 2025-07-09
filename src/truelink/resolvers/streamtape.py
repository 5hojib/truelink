from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx  # Added for synchronous requests
from lxml.etree import HTML  # Changed from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FolderResult, LinkResult

from .base import BaseResolver


class StreamtapeResolver(BaseResolver):
    """Resolver for Streamtape URLs"""

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Streamtape URL"""
        try:
            # Logic from the user-provided synchronous streamtape function
            splitted_url = url.split("/")
            _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]

            # Using httpx for synchronous GET request as per user's provided code structure
            # BaseResolver uses an async client, but to integrate the provided code with minimal changes:
            # We'll make a synchronous call here.
            # Alternatively, the provided logic should be rewritten to be async.
            # For now, let's stick to the structure of the provided solution.
            try:
                # We need a synchronous HTTP client here if we are to use the provided logic as-is.
                # The BaseResolver's self.session is async.
                # Using httpx directly for a sync call.
                response = httpx.get(url, follow_redirects=True)
                response.raise_for_status()  # Raise an exception for bad status codes
                html_content = response.text
            except httpx.HTTPStatusError as e:
                raise ExtractionFailedException(
                    f"Streamtape request failed: {e.response.status_code} - {e.request.url}"
                ) from e
            except httpx.RequestError as e:
                raise ExtractionFailedException(
                    f"Streamtape request error: {e.__class__.__name__} for {e.request.url}"
                ) from e

            html = HTML(html_content)
            parsed_original_url = urlparse(url)

            script_elements = html.xpath(
                "//script[contains(text(),'ideoooolink')]/text()"
            ) or html.xpath("//script[contains(text(),'ideoolink')]/text()")

            if not script_elements:
                # Fallback: search all scripts for the pattern if specific ones aren't found
                all_scripts_content = html.xpath("//script/text()")
                script_content = None
                for sc_text in all_scripts_content:
                    if sc_text and "get_video" in sc_text and "expires" in sc_text:
                        # A bit broad, but might catch it if the specific markers are gone
                        script_content = sc_text
                        break
                if not script_content:
                    raise ExtractionFailedException(
                        "Streamtape error: Required script content not found on page."
                    )
            else:
                script_content = script_elements[0]

            # Use the regex from the user's provided successful code
            # This regex captures the query parameters starting with &expires...
            # The original was findall(r"(&expires\S+)'", script_content) - greedy
            # Let's use non-greedy just in case, but stick to the core pattern.
            link_params_matches = re.findall(r"(&expires\S+?)'", script_content)

            if not link_params_matches:
                # Second attempt: Sometimes the 'id' might be part of the JS concatenated string.
                # Look for patterns like: ('&id=XYZ&expires=...') or ('?id=XYZ&expires=...')
                # This is more complex. The initial user regex was simpler.
                # Let's try to find a more complete get_video URL pattern if the simple one fails.
                # Example: `innerHTML = '//streamtape.to/get_video' + ('?id=0JqVB7zqz7hmlp&expires=...')`
                # Regex to find `//<host>/get_video?id=...&expires=...&token=...`
                # This pattern was seen in 'norobotlink' and similar elements.
                # This is a more direct extraction of the full path and query.
                # Example: `//streamtape.to/get_video?id=0JqVB7zqz7hmlp&expires=1752130523&ip=FHEsExInDS9X&token=gkB8Gcms5DtD`

                # Try to find the JS part that looks like `('?id=ID&expires=...&token=...')`
                # or `('&id=ID&expires=...&token=...')`
                # This part is often concatenated after a base URL string.
                # The crucial part is `id={_id}` followed by `&expires=`
                # The substring operations make this very hard to catch with a single regex for all cases.

                # Let's try to find the specific string part from the `ideoooolink` example:
                # `('xcddid=0JqVB7zqz7hmlp&expires=...&token=...').substring(1).substring(2)`
                # This results in `did=0JqVB7zqz7hmlp&expires=...`
                # The 'id' is part of this.
                # The final URL is `.../get_video?` + `did={_id}&expires=...`
                # This means the `id={_id}` part is NOT always needed in the base string if it's in the params.

                # The most reliable pattern from the user's code was `(&expires\S+)'`.
                # This implies the base URL is `https://domain/get_video?id=VIDEO_ID`
                # and the regex provides the rest like `&expires=...&token=...`

                # If the simple `&expires` regex fails, it's possible the structure is different.
                # Let's re-check the `inspect_streamtape.py` output:
                # `document.getElementById('ideoooolink').innerHTML = "/streamtape.to/get_video?" + ('xcddid=0JqVB7zqz7hmlp&expires=...').substring(1).substring(2);`
                # The string being substringed is `'xcddid=0JqVB7zqz7hmlp&expires=...'`
                # `substring(1)` -> `'cddid=0JqVB7zqz7hmlp&expires=...'`
                # `substring(2)` -> `'did=0JqVB7zqz7hmlp&expires=...'`
                # So the final URL is `scheme://netloc/streamtape.to/get_video?did={_id}&expires=...` (still looks wrong)
                # No, `innerHTML = "/streamtape.to/get_video?" + result_of_substring`
                # So, `scheme://netloc` + `"/streamtape.to/get_video?"` + `result_of_substring`
                # This means the path itself contains the domain, which is unusual.
                # `/streamtape.to/get_video?` -> if netloc is `streamtape.to`, this is `https://streamtape.to/streamtape.to/get_video?`
                # This was the original error.

                # The user's code `f"https://streamtape.com/get_video?id={_id}{link[-1]}"`
                # This implies `link[-1]` starts with `&expires`.
                # And the base is always `https://<some_streamtape_domain>/get_video?id={_id}`.

                # Let's simplify and trust the user's original regex structure.
                # The only part to make dynamic is the domain.
                raise ExtractionFailedException(
                    "Streamtape error: Download link parameters ('&expires...') not found in script using primary regex.",
                )

            query_params_suffix = link_params_matches[-1]

            # Construct the direct link using the original URL's scheme and netloc
            # and the path structure from the user's successful code.
            direct_link = f"{parsed_original_url.scheme}://{parsed_original_url.netloc}/get_video?id={_id}{query_params_suffix}"
            # We need to fetch filename and size.
            # The base resolver's _fetch_file_details is async.
            # To keep this part synchronous for now (matching user's provided style):
            try:
                # Perform a HEAD request to get headers for filename and size
                # Need to use a synchronous client again.
                head_response = httpx.head(
                    direct_link, headers={"Referer": url}, follow_redirects=True
                )
                head_response.raise_for_status()

                content_disposition = head_response.headers.get(
                    "content-disposition"
                )
                filename = None
                if content_disposition:
                    # Extract filename from content-disposition, e.g., "attachment; filename=\"video.mp4\""
                    fn_match = re.search(
                        r"filename\*?=['\"]?([^'\"]+)['\"]?", content_disposition
                    )
                    if fn_match:
                        filename = fn_match.group(1)

                if not filename:  # Fallback if filename not in content-disposition
                    # Try to get filename from URL path
                    parsed_link_url = urlparse(direct_link)
                    filename_from_path = parsed_link_url.path.split("/")[-1]
                    if filename_from_path:  # Ensure it's not empty
                        filename = filename_from_path

                content_length = head_response.headers.get("content-length")
                size = (
                    int(content_length)
                    if content_length and content_length.isdigit()
                    else None
                )

            except httpx.HTTPStatusError as e:
                # If HEAD request fails, it might be that HEAD is not allowed or link is bad
                # Log this or handle as partial success (link found, details not)
                # For now, let's assume if HEAD fails, we can't confirm the link fully.
                raise ExtractionFailedException(
                    f"Streamtape: Failed to get file details from '{direct_link}'. Status: {e.response.status_code}",
                ) from e
            except httpx.RequestError as e:
                raise ExtractionFailedException(
                    f"Streamtape: Network error while fetching file details from '{direct_link}'. Error: {e.__class__.__name__}",
                ) from e

            if not filename:  # If filename is still None
                # Default filename if not found
                filename = _id  # Or some other default like "streamtape_video.mp4"

            return LinkResult(url=direct_link, filename=filename, size=size)

        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            # Catch any other unexpected errors during the process
            raise ExtractionFailedException(
                f"An unexpected error occurred while resolving Streamtape URL '{url}': {e!s}",
            ) from e

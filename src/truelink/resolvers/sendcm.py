from __future__ import annotations

import os.path  # For ospath.join
from urllib.parse import urlparse

from lxml.html import fromstring

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver


# Placeholder for speed_string_to_bytes and PASSWORD_ERROR_MESSAGE
def _speed_string_to_bytes_placeholder_sendcm(size_str: str) -> int:
    size_str = (size_str or "").upper().strip()
    num_part = "".join(filter(lambda x: x.isdigit() or x == ".", size_str))
    if not num_part:
        return 0
    num = float(num_part)
    if "GB" in size_str:
        return int(num * (1024**3))
    if "MB" in size_str:
        return int(num * (1024**2))
    if "KB" in size_str:
        return int(num * 1024)
    return int(num)


PASSWORD_ERROR_MESSAGE_SENDCM = (
    "Send.cm link {} requires a password (append ::password to the URL)."
)


class SendCmResolver(BaseResolver):
    """Resolver for Send.cm URLs"""

    _speed_string_to_bytes = _speed_string_to_bytes_placeholder_sendcm

    # --- Cloudflare Bypass Helper ---
    # This is a critical external dependency. If cf.jmdkh.eu.org is down/changes, this will break.
    CF_BYPASS_API_URL = (
        "https://cf.jmdkh.eu.org/v1"  # Hardcoded from original script
    )

    async def _cf_bypass_helper(self, url_to_bypass: str) -> str:
        """
        Uses the external jmdkh.eu.org service to bypass Cloudflare for a given URL.
        Returns the HTML content of the bypassed page.
        """
        payload = {
            "cmd": "request.get",
            "url": url_to_bypass,
            "maxTimeout": 60000,  # As in original script
        }
        # This bypass service might require specific headers if it's mimicking a browser.
        # For now, sending JSON payload.
        headers = {"Content-Type": "application/json", "User-Agent": self.USER_AGENT}

        try:
            async with await self._post(
                self.CF_BYPASS_API_URL,
                json=payload,
                headers=headers,
            ) as cf_response:
                if cf_response.status != 200:
                    err_text = await cf_response.text()
                    raise ExtractionFailedException(
                        f"Send.cm (CF Bypass API) error {cf_response.status}: {err_text[:200]}",
                    )

                json_res = await cf_response.json()

            if (
                json_res.get("status") == "ok"
                and "solution" in json_res
                and "response" in json_res["solution"]
            ):
                return json_res["solution"][
                    "response"
                ]  # This is expected to be HTML content
            error_detail = json_res.get(
                "message",
                "CF Bypass failed or returned unexpected response.",
            )
            raise ExtractionFailedException(
                f"Send.cm (CF Bypass API) error: {error_detail}. Full: {str(json_res)[:200]}",
            )
        except Exception as e:
            if isinstance(e, ExtractionFailedException):
                raise
            raise ExtractionFailedException(
                f"Send.cm: Cloudflare bypass request failed for {url_to_bypass}. Error: {e!s}",
            )

    async def _resolve_sendcm_file(
        self,
        page_url: str,
        file_id_override: str | None = None,
    ) -> LinkResult:
        """Resolves a single Send.cm file link."""
        _password = ""
        request_url = page_url
        if "::" in page_url:
            parts = page_url.split("::", 1)
            request_url = parts[0]
            _password = parts[1]

        password_needed_on_page = False
        file_id_from_page = None

        if file_id_override is None:  # Need to parse the page to get file_id
            try:
                # Use CF bypass to get initial page HTML if needed, though direct POST might work for files.
                # The original script doesn't show CF bypass for the send_cm_file part explicitly,
                # but it's used for folder listing. Let's assume direct access for file POST for now.
                # If it fails, CF bypass might be needed here too.
                async with await self._get(request_url) as response:
                    html_text = await response.text()
                html = fromstring(html_text)

                if html.xpath("//input[@name='password']"):
                    password_needed_on_page = True

                file_id_elements = html.xpath("//input[@name='id']/@value")
                if not file_id_elements:
                    raise ExtractionFailedException(
                        "Send.cm file error: file_id not found on page.",
                    )
                file_id_from_page = file_id_elements[0]
            except (
                Exception
            ) as e:  # Catch issues getting the page or parsing file_id
                if isinstance(e, ExtractionFailedException):
                    raise
                # If GET fails (e.g. CF protection), this is where CF bypass might be needed.
                # For now, re-raise.
                raise ExtractionFailedException(
                    f"Send.cm: Failed to get file page {request_url}. Error: {e!s}",
                )

        actual_file_id = file_id_override if file_id_override else file_id_from_page
        if not actual_file_id:  # Should not happen if logic is correct
            raise ExtractionFailedException(
                "Send.cm file error: Could not determine file_id.",
            )

        post_data = {"op": "download2", "id": actual_file_id}
        if _password and (
            password_needed_on_page or file_id_override
        ):  # Add password if provided and needed/likely needed
            post_data["password"] = _password

        # POST to get the direct link
        # allow_redirects=False to catch Location header
        async with await self._post(
            "https://send.cm/",
            data=post_data,
            allow_redirects=False,
        ) as dl_response:
            if "Location" in dl_response.headers and 300 <= dl_response.status < 400:
                direct_link = dl_response.headers["Location"]
                # Referer for _fetch_file_details
                fetch_headers = {"Referer": "https://send.cm/"}
                filename, size = await self._fetch_file_details(
                    direct_link,
                    custom_headers=fetch_headers,
                )
                return LinkResult(url=direct_link, filename=filename, size=size)
            # No redirect or not a redirect status
            if (
                password_needed_on_page and not _password
            ):  # Or if we tried without password and it failed
                raise ExtractionFailedException(
                    PASSWORD_ERROR_MESSAGE_SENDCM.format(request_url),
                )
            # Other errors
            error_text_snippet = await dl_response.text()
            raise ExtractionFailedException(
                f"Send.cm file error: Could not get direct link. Status {dl_response.status}. Response: {error_text_snippet[:200]}",
            )

    async def _get_file_link_for_folder(self, file_id: str) -> str | None:
        """Helper for folder traversal to get individual file links via POST."""
        try:
            async with await self._post(
                "https://send.cm/",
                data={"op": "download2", "id": file_id},
                allow_redirects=False,
            ) as res:
                if "Location" in res.headers and 300 <= res.status < 400:
                    return res.headers["Location"]
        except Exception:
            pass  # Ignore errors for individual files in folder, just skip them
        return None

    async def _process_sendcm_folder_page(
        self,
        html_page_content: str,
        current_path: str,
        folder_details_obj: FolderResult,
    ):
        """Processes a single folder page's content (files and subfolders)."""
        html = fromstring(html_page_content)

        # Process subfolders first (DFS-like)
        subfolder_elements = html.xpath("//h6/a")  # Gets <a> elements under <h6>
        for folder_elem in subfolder_elements:
            folder_url_path = folder_elem.get("href")
            folder_name = "".join(folder_elem.xpath(".//text()")).strip()
            if not folder_url_path or not folder_name:
                continue

            # Construct full URL for subfolder
            # Assuming folder_url_path is relative like /s/folderId/name
            subfolder_full_url = f"https://send.cm{folder_url_path if folder_url_path.startswith('/') else '/' + folder_url_path}"

            try:
                subfolder_html_content = await self._cf_bypass_helper(
                    subfolder_full_url,
                )
                new_path = os.path.join(current_path, folder_name)
                await self._process_sendcm_folder_page(
                    subfolder_html_content,
                    new_path,
                    folder_details_obj,
                )
            except Exception:
                # Skip subfolder if CF bypass or processing fails
                continue

        # Process files in the current folder
        file_rows = html.xpath('//tr[@class="selectable"]')
        for row in file_rows:
            link_element = row.xpath(".//a/@href")
            name_element = row.xpath(".//a/text()")
            size_element = row.xpath(".//span/text()")  # This gets size like "15 MB"

            if not (link_element and name_element and size_element):
                continue

            file_id = link_element[0].split("/")[-1]
            file_name = name_element[0].strip()
            size_text = size_element[0].strip()

            file_direct_link = await self._get_file_link_for_folder(file_id)
            if file_direct_link:
                size_bytes = self._speed_string_to_bytes(size_text)
                folder_details_obj.contents.append(
                    FileItem(
                        filename=file_name,
                        url=file_direct_link,
                        size=size_bytes,
                        path=current_path,
                    ),
                )
                if size_bytes:  # total_size can be None if parsing failed.
                    folder_details_obj.total_size += size_bytes

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve Send.cm URL (file or folder)"""
        parsed_url = urlparse(
            url.split("::")[0],
        )  # Use URL without password for path checks

        # Handle direct file links (e.g. /d/xxxx or /xxxx if no /s/ or /d/)
        if "/d/" in parsed_url.path or (
            "/s/" not in parsed_url.path
            and parsed_url.path.count("/") <= 2
            and parsed_url.path != "/"
        ):
            # Assuming if not a folder link (/s/) and path is short, it's a file ID or /d/file_id
            file_id_override = None
            if "/d/" not in parsed_url.path:  # If like /xxxx
                file_id_override = parsed_url.path.strip("/")
            return await self._resolve_sendcm_file(url, file_id_override)

        # Handle folder links (/s/...)
        if "/s/" in parsed_url.path:
            folder_details = FolderResult(title="", contents=[], total_size=0)

            # Extract initial folder title from URL if possible
            # e.g. /s/folderId/My-Folder-Name -> My-Folder-Name
            path_parts = [p for p in parsed_url.path.split("/") if p]
            if len(path_parts) >= 3 and path_parts[0] == "s":  # /s/id/name
                folder_details.title = path_parts[2]
            elif (
                len(path_parts) >= 2 and path_parts[0] == "s"
            ):  # /s/id (no name in URL)
                folder_details.title = path_parts[1]  # Use ID as title
            else:
                folder_details.title = "Send.cm Folder"

            try:
                # Main folder page requires CF bypass
                main_folder_html = await self._cf_bypass_helper(
                    url.split("::")[0],
                )  # Use URL without password
                await self._process_sendcm_folder_page(
                    main_folder_html,
                    folder_details.title,
                    folder_details,
                )
            except Exception as e:
                raise ExtractionFailedException(
                    f"Send.cm: Failed to process folder '{url}'. Error: {e!s}",
                )

            if not folder_details.contents:
                # If no contents after processing, it might be an empty folder or an issue.
                # For now, return empty FolderResult if title was set.
                if not folder_details.title:  # Should have a title by now
                    raise ExtractionFailedException(
                        f"Send.cm: No files found in folder '{url}' and no title derived.",
                    )

            # If folder has only one file, and root title matches file name, return as LinkResult
            if len(folder_details.contents) == 1:
                single_item = folder_details.contents[0]
                if (
                    folder_details.title == single_item.filename
                    and not single_item.path
                ):  # Path check ensures it's not in a sub-sub-folder
                    # Original returned (url, header). We use header for _fetch if needed, not in result.
                    return LinkResult(
                        url=single_item.url,
                        filename=single_item.filename,
                        size=single_item.size,
                    )

            return folder_details

        raise InvalidURLException(f"Unrecognized Send.cm URL format: {url}")

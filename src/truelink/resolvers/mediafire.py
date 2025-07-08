from __future__ import annotations

import asyncio
import re
import os.path as ospath # For ospath.join
from urllib.parse import urlparse, unquote

# Use lxml.etree for consistency with user's provided code if it makes a difference,
# otherwise fromstring is fine. For XPath, they are largely compatible.
# from lxml.html import fromstring
from lxml.etree import HTML # As per user's code

import cloudscraper # For Cloudflare bypass

from truelink.exceptions import ExtractionFailedException, InvalidURLException
from truelink.types import FileItem, FolderResult, LinkResult

from .base import BaseResolver

# Using the error message format from user's code, assuming it might be a shared constant.
# If not, this can be defined locally.
# from bot.helper.ext_utils.help_messages import PASSWORD_ERROR_MESSAGE
# For now, define it locally based on user's provided code's apparent usage.
PASSWORD_ERROR_MESSAGE = "ERROR: This link is password protected. Please provide the password for: {}"
# Fallback if the above is not found or causes issues with formatting.
# PASSWORD_ERROR_MESSAGE = "MediaFire link {} requires a password."


class MediaFireResolver(BaseResolver):
    """Resolver for MediaFire URLs (files and folders)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # It's good practice to create the scraper instance once if possible,
        # but MediaFire can be tricky with sessions.
        # For now, creating per call or per function as needed for simplicity,
        # mirroring user's code structure.
        # self.scraper = cloudscraper.create_scraper() # Reconsider if session needs to be long-lived

    async def _run_sync_in_thread(self, func, *args, **kwargs):
        """Helper to run synchronous cloudscraper calls in a separate thread."""
        loop = asyncio.get_running_loop()
        # Pass the current scraper instance if it's session-based and needs to be reused
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def resolve(self, url: str) -> LinkResult | FolderResult:
        """Resolve MediaFire URL (file or folder)"""
        _password = ""
        # Using url.split("::", 1) is safer if password itself could contain "::"
        if "::" in url:
            parts = url.split("::", 1)
            url = parts[0]
            _password = parts[1]

        # Normalize URL: remove query parameters and fragments for some checks, keep for others
        parsed_url = urlparse(url)
        # Scheme and netloc are vital; path should be unquoted for some MediaFire formats.
        # User's code normalizes path like: f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        # Let's adopt this careful normalization where appropriate.
        base_url_for_checks = f"{parsed_url.scheme}://{parsed_url.netloc}{unquote(parsed_url.path)}"


        if "/folder/" in base_url_for_checks: # Use base_url_for_checks for routing
            return await self._resolve_folder(url, _password) # Pass original url for processing
        return await self._resolve_file(url, _password) # Pass original url for processing

    async def _get_page_content(self, scraper_session, url_to_fetch: str) -> str:
        response = await self._run_sync_in_thread(scraper_session.get, url_to_fetch)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text

    async def _post_page_content(self, scraper_session, url_to_fetch: str, data: dict) -> str:
        response = await self._run_sync_in_thread(scraper_session.post, url_to_fetch, data=data)
        response.raise_for_status()
        return response.text

    async def _repair_download(
        self,
        scraper_session, # Pass the session
        repair_url: str,
        original_url_for_password_msg: str, # For error message context
        original_password: str,
    ) -> LinkResult: # Should resolve to LinkResult
        """Helper to handle MediaFire's repair/continue links."""
        full_repair_url = repair_url
        if repair_url.startswith("//"):
            full_repair_url = f"https:{repair_url}"
        elif not repair_url.startswith("http"):
            full_repair_url = f"https://www.mediafire.com{repair_url if repair_url.startswith('/') else '/' + repair_url}"

        # The _resolve_file method creates its own scraper session if one is not passed.
        # To maintain session continuity through repair, we'd ideally pass it.
        # However, _resolve_file as defined will create a new one. This is acceptable for now.
        # This call will effectively re-run _resolve_file with the new URL.
        return await self._resolve_file(full_repair_url, original_password, scraper_session_override=scraper_session)


    async def _resolve_file(self, url: str, password: str, scraper_session_override=None) -> LinkResult:
        """
        Resolves a single MediaFire file link.
        Uses cloudscraper via asyncio.to_thread for network operations.
        Accepts an optional scraper_session_override to reuse a session (e.g., from _repair_download).
        """
        # Direct download link check (from user's code)
        if re.search(r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url):
            # If it's a direct link, we might not have filename/size yet.
            # BaseResolver._fetch_file_details might do a HEAD request.
            # User's code doesn't show how filename/size is obtained for this specific path.
            # For now, assume _fetch_file_details handles it.
            # If _fetch_file_details is not available or suitable, this needs implementation.
            try:
                filename, size = await self._fetch_file_details(url)
            except Exception: # Fallback if _fetch_file_details fails or not implemented
                filename = unquote(url.split("/")[-1])
                size = None # Size unknown without HEAD or range request
            return LinkResult(url=url, filename=filename, size=size)

        # Use provided session or create a new one
        if scraper_session_override:
            scraper = scraper_session_override
        else:
            scraper = cloudscraper.create_scraper()
            # Ensure cloudscraper uses the same User-Agent as defined in BaseResolver
            # for consistency, in case MediaFire is sensitive to it.
            scraper.headers.update({'User-Agent': BaseResolver.USER_AGENT})

        # The URL passed to this function might contain necessary query parameters (e.g. dkey, r)
        # which are essential for MediaFire's stateful navigation.
        # So, for fetching, we should use the 'url' as is.
        # A normalized version can be used for display or specific pre-checks if needed.
        display_url = url # Use the full URL for error messages for clarity

        try:
            # Fetch using the 'url' directly, preserving query parameters
            html_text = await self._get_page_content(scraper, url)
            # User's code uses lxml.etree.HTML
            html = HTML(html_text)

            # Error check (from user's code, adapted class name)
            if error_msg_list := html.xpath('//p[@class="notranslate"]/text()'):
                raise ExtractionFailedException(f"MediaFire error: {error_msg_list[0]}")

            # Password check (from user's code)
            if html.xpath("//div[@class='passwordPrompt']"):
                if not password:
                    # Use the PASSWORD_ERROR_MESSAGE constant
                    raise ExtractionFailedException(PASSWORD_ERROR_MESSAGE.format(display_url))

                # Post password (from user's code)
                # Post to the same 'url' that presented the password prompt
                html_text = await self._post_page_content(scraper, url, data={"downloadp": password})
                html = HTML(html_text) # Re-parse HTML after POST

                if html.xpath("//div[@class='passwordPrompt']"): # Password prompt still there
                    raise ExtractionFailedException("MediaFire error: Wrong password.")

            # Final link extraction (from user's code)
            if not (final_link_elements := html.xpath('//a[@aria-label="Download file"]/@href')):
                # Repair link check (from user's code)
                if repair_link_elements := html.xpath("//a[@class='retry']/@href"):
                    # Pass the current scraper session to _repair_download
                    return await self._repair_download(
                        scraper, # Pass current session
                        repair_link_elements[0],
                        display_url, # original URL for error context
                        password,
                    )
                # User's error message
                raise ExtractionFailedException("ERROR: No links found in this page Try Again")

            final_link = final_link_elements[0]

            # Handle links starting with // (from user's code)
            if final_link.startswith("//"):
                # This becomes a recursive call to _resolve_file with the new URL
                # Pass the current scraper session
                return await self._resolve_file(f"https:{final_link}", password, scraper_session_override=scraper)

            # If the link is another MediaFire page (not a download subdomain), recurse.
            # This logic is similar to the original resolver but adapted.
            final_parsed = urlparse(final_link)
            if "mediafire.com" in final_parsed.hostname and not re.match(r"https?:\/\/download\d+\.mediafire\.com", final_link):
                return await self._resolve_file(final_link, password, scraper_session_override=scraper)


            # At this point, final_link should be the direct download URL.
            # Fetch filename and size.
            try:
                dl_filename, dl_size = await self._fetch_file_details(final_link)
            except Exception: # Fallback
                dl_filename = unquote(final_link.split("/")[-1].split("?")[0]) # Basic filename extraction
                dl_size = None
            return LinkResult(url=final_link, filename=dl_filename, size=dl_size)

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(f"MediaFire Cloudflare challenge failed: {e!s}") from e
        except Exception as e: # Catch other exceptions like requests.exceptions.RequestException
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            # Use class name for better error reporting, as in user's code
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire file '{display_url}': {e.__class__.__name__} - {e!s}",
            ) from e
        finally:
            # If we created the session in this call (not overridden), close it.
            if not scraper_session_override and hasattr(scraper, 'close'):
                 await self._run_sync_in_thread(scraper.close)


    async def _api_request(self, scraper_session, method: str, api_url: str, data=None, params=None) -> dict:
        """Helper for making API requests using cloudscraper session."""
        if method.lower() == "post":
            response_json = await self._run_sync_in_thread(scraper_session.post, api_url, data=data, params=params, timeout=20)
        else: # GET
            response_json = await self._run_sync_in_thread(scraper_session.get, api_url, params=params, data=data, timeout=20)

        response_json.raise_for_status() # Check for HTTP errors
        json_data = response_json.json()

        api_res = json_data.get("response", {})
        if api_res.get("result", "").lower() == "error" or "message" in api_res : # Check for API-level error messages
             error_message = api_res.get("message", "Unknown API error")
             # Add more context if available, e.g. from 'error' or 'details' fields
             if 'error' in api_res: error_message += f" (Code: {api_res['error']})"
             raise ExtractionFailedException(f"MediaFire API error: {error_message}")
        return api_res


    async def _resolve_folder(self, url: str, password: str) -> FolderResult:
        """Resolves a MediaFire folder link using logic from user's provided code."""
        scraper = cloudscraper.create_scraper() # New session for folder operations
        scraper.headers.update({'User-Agent': BaseResolver.USER_AGENT}) # Set User-Agent

        try:
            # Extract folder key(s) from URL (user's code logic)
            try:
                raw = url.split("/", 4)[-1]
                folder_key_part = raw.split("/", 1)[0]
                folder_keys_list = folder_key_part.split(",")
                if not folder_keys_list or not folder_keys_list[0]: # Ensure there's at least one valid key
                    raise ValueError("Empty folder key")
            except Exception as e:
                raise InvalidURLException(f"ERROR: Could not parse folder key from URL '{url}': {e}") from e

            # --- Get Main Folder Info (adapting user's __get_info) ---
            folder_infos_api_data = [] # Stores info from folder/get_info for each key

            # Use the first key for the primary title, but fetch info for all keys if multiple.
            # This is a bit different from user's code which joins keys for one API call.
            # Let's try to get info for each key if that's more robust or what truelink expects.
            # For now, stick to user's code: join keys for `folder/get_info` if multiple.

            folder_key_param_for_api = ",".join(folder_keys_list)

            try:
                folder_info_response = await self._api_request(
                    scraper, "post",
                    "https://www.mediafire.com/api/1.5/folder/get_info.php",
                    data={
                        "recursive": "yes", # As per user's code
                        "folder_key": folder_key_param_for_api,
                        "response_format": "json",
                    }
                )
            except Exception as e:
                 raise ExtractionFailedException(f"ERROR: {e.__class__.__name__} While getting folder info for keys '{folder_key_param_for_api}' - {e}")


            # Process folder_info_response (adapting from user's code)
            # User code expects 'folder_infos' or 'folder_info'
            processed_folder_infos = []
            if "folder_infos" in folder_info_response: # Multiple folders' info returned
                processed_folder_infos.extend(folder_info_response["folder_infos"])
            elif "folder_info" in folder_info_response: # Single folder's info
                processed_folder_infos.append(folder_info_response["folder_info"])
            # elif "message" in folder_info_response: # Already handled by _api_request
            #     raise ExtractionFailedException(f"API Error (folder/get_info): {folder_info_response['message']}")
            else:
                raise ExtractionFailedException("ERROR: Malformed API response from folder/get_info (missing folder_info/folder_infos).")

            if not processed_folder_infos:
                raise ExtractionFailedException("ERROR: No folder information found from API.")

            # Determine overall folder title (e.g., from the first folder info)
            # User's code: details["title"] = folder_infos[0]["name"]
            # The FolderResult type expects a single 'title'.
            # If multiple keys in URL, this might need clarification on how title is formed.
            # For now, use the name of the first folder info object.
            main_folder_title = processed_folder_infos[0].get("name", "MediaFire Folder")


            all_files: list[FileItem] = []
            total_size_bytes: int = 0

            # --- Recursive function to get folder contents (adapting user's __get_content) ---
            async def get_folder_contents_recursive(current_mf_folder_key: str, current_path_prefix: str):
                nonlocal total_size_bytes # Allow modification

                # Get files in the current folder
                try:
                    content_api_params = {
                        "content_type": "files",
                        "folder_key": current_mf_folder_key,
                        "response_format": "json",
                    }
                    files_content_response = await self._api_request(
                        scraper, "get",
                        "https://www.mediafire.com/api/1.5/folder/get_content.php",
                        params=content_api_params
                    )
                except Exception as e:
                    # Log or handle error for this specific subfolder, maybe continue with others
                    # For now, re-raise as it's critical path.
                    raise ExtractionFailedException(f"Failed to get files for folder key {current_mf_folder_key}: {e}")


                api_files = files_content_response.get("folder_content", {}).get("files", [])
                for file_api_data in api_files:
                    if not file_api_data.get("links") or not file_api_data["links"].get("normal_download"):
                        continue # Skip if no download link info

                    # Get page URL from API (this is not the direct link yet)
                    file_page_url = file_api_data["links"]["normal_download"]

                    try:
                        # Resolve this file page to get the direct link and actual size/filename
                        # Pass the folder's password context.
                        # _resolve_file will create its own short-lived scraper session.
                        link_result = await self._resolve_file(file_page_url, password)

                        item_filename = file_api_data.get("filename", "unknown_file")
                        # Use size from resolved link if available, otherwise from API as fallback.
                        item_size = link_result.size
                        if item_size is None and "size" in file_api_data: # Fallback to API size
                             size_str = str(file_api_data["size"])
                             if size_str.isdigit(): item_size = int(size_str)

                        file_item = FileItem(
                            filename=item_filename,
                            url=link_result.url, # This is the direct URL
                            size=item_size,
                            path=ospath.join(current_path_prefix, item_filename) # Path should be relative to folder root
                        )
                        all_files.append(file_item)
                        if item_size: # Ensure item_size is not None
                            total_size_bytes += item_size

                    except ExtractionFailedException:
                        # Log this skip if necessary, e.g. self.logger.warning(...)
                        # For now, skip files that fail to resolve, as per user's code implicit behavior
                        pass
                    except Exception: # Catch any other unexpected error during single file resolution
                        # Log this as well
                        pass


                # Get subfolders and recurse
                try:
                    subfolders_content_params = {
                        "content_type": "folders",
                        "folder_key": current_mf_folder_key,
                        "response_format": "json",
                    }
                    subfolders_response = await self._api_request(
                        scraper, "get",
                        "https://www.mediafire.com/api/1.5/folder/get_content.php",
                        params=subfolders_content_params
                    )
                except Exception as e:
                    raise ExtractionFailedException(f"Failed to get subfolders for folder key {current_mf_folder_key}: {e}")

                api_subfolders = subfolders_response.get("folder_content", {}).get("folders", [])
                for subfolder_api_data in api_subfolders:
                    sub_folder_key = subfolder_api_data.get("folderkey")
                    sub_folder_name = subfolder_api_data.get("name")
                    if sub_folder_key and sub_folder_name:
                        # Construct new path prefix for items within this subfolder
                        new_path_prefix = ospath.join(current_path_prefix, sub_folder_name)
                        await get_folder_contents_recursive(sub_folder_key, new_path_prefix)

            # --- Iterate through initial folder infos and start recursion ---
            # User's code: for folder in folder_infos: __get_content(folder["folderkey"], folder["name"])
            # `processed_folder_infos` contains the info objects (dicts)
            for folder_data in processed_folder_infos:
                folder_key_from_api = folder_data.get("folderkey")
                folder_name_from_api = folder_data.get("name")
                if folder_key_from_api and folder_name_from_api:
                    # The path for files directly under this folder should be relative to its name.
                    await get_folder_contents_recursive(folder_key_from_api, folder_name_from_api)
                # else: skip if key or name is missing, or log warning.

            if not all_files:
                # User code doesn't raise here, but returns empty details.
                # truelink might expect an exception if nothing is found.
                # For now, align with existing resolver's behavior.
                raise ExtractionFailedException(
                    f"No downloadable files found in MediaFire folder '{url}'.",
                )

            # If only one file, user's code returns tuple: (url, [header_empty_string_placeholder])
            # truelink FolderResult type is different. We should always return FolderResult.
            # The original resolver also returns FolderResult.

            return FolderResult(
                title=main_folder_title,
                contents=all_files,
                total_size=total_size_bytes,
            )

        except cloudscraper.exceptions.CloudflareException as e:
            raise ExtractionFailedException(f"MediaFire Cloudflare challenge failed during folder processing: {e!s}") from e
        except Exception as e:
            if isinstance(e, ExtractionFailedException | InvalidURLException):
                raise
            raise ExtractionFailedException(
                f"Failed to resolve MediaFire folder '{url}': {e.__class__.__name__} - {e!s}",
            ) from e
        finally:
            if hasattr(scraper, 'close'):
                await self._run_sync_in_thread(scraper.close)

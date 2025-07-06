import re
import asyncio
from lxml.html import fromstring
from typing import Union

from .base import BaseResolver
from ..types import LinkResult, FolderResult, FileItem
from ..exceptions import ExtractionFailedException

class BuzzHeavierResolver(BaseResolver):
    """Resolver for BuzzHeavier URLs"""
    
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """Resolve BuzzHeavier URL"""
        pattern = r"^https?://buzzheavier.com/[a-zA-Z0-9]+$"
        if not re.match(pattern, url):
            return LinkResult(url=url)
        
        try:
            async with await self._get(url) as response:
                html_content = await response.text()
                tree = fromstring(html_content)
            
            # Check for single file download
            link_elements = tree.xpath(
                "//a[contains(@class, 'link-button') and contains(@class, 'gay-button')]/@hx-get"
            )
            
            if link_elements:
                download_url = await self._get_download_url(f"https://buzzheavier.com{link_elements[0]}")
                # Fetch filename and size
                filename, size = await self._fetch_file_details(download_url)
                return LinkResult(url=download_url, filename=filename, size=size)
            
            # Check for folder contents
            folder_elements = tree.xpath("//tbody[@id='tbody']/tr")
            if folder_elements:
                return await self._process_folder(tree, folder_elements)
            
            raise ExtractionFailedException("No download link found")
            
        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve BuzzHeavier URL: {e}") from e
    
    async def _get_download_url(self, url: str, is_folder: bool = False) -> str:
        """Get download URL from BuzzHeavier"""
        if "/download" not in url:
            url += "/download"
        
        headers = {
            "referer": url.split("/download")[0],
            "hx-current-url": url.split("/download")[0],
            "hx-request": "true",
            "priority": "u=1, i",
        }
        
        async with await self._get(url, headers=headers) as response:
            redirect_url = response.headers.get("Hx-Redirect")
            if not redirect_url:
                if not is_folder:
                    raise ExtractionFailedException("Failed to get download URL")
                return None
            return redirect_url
    
    async def _process_folder(self, tree, folder_elements) -> FolderResult:
        """Process folder contents"""
        contents = []
        total_size = 0
        
        for element in folder_elements:
            try:
                filename_elem = element.xpath(".//a")[0]
                scraped_filename = filename_elem.text.strip()
                file_id = filename_elem.get("href", "").strip()
                # size_text = element.xpath(".//td[@class='text-center']/text()")[0].strip() # Original size text, not reliable
                
                download_url = await self._get_download_url(f"https://buzzheavier.com{file_id}", True)
                
                if download_url:
                    # Fetch actual filename and size
                    actual_filename, item_size = await self._fetch_file_details(download_url)

                    contents.append(FileItem(
                        filename=actual_filename if actual_filename else scraped_filename, # Prioritize actual_filename
                        url=download_url,
                        size=item_size,
                        path="",
                    ))
                    if item_size is not None:
                        total_size += item_size
                    
            except Exception: # Consider more specific exception handling or logging
                continue
        
        title = tree.xpath("//span/text()")[0].strip() if tree.xpath("//span/text()") else "BuzzHeavier Folder"
        
        return FolderResult(
            title=title,
            contents=contents,
            total_size=total_size
        )

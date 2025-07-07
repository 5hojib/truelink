import aiohttp
from abc import ABC, abstractmethod
from typing import Union, Dict, Any, Optional

import re 
from urllib.parse import unquote, urlparse 
from ..types import LinkResult, FolderResult
from ..exceptions import ExtractionFailedException

class BaseResolver(ABC):
    """Base class for all resolvers"""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _create_session(self):
        """Create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={'User-Agent': self.USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def _close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request"""
        if not self.session:
            await self._create_session()
        response = await self.session.get(url, **kwargs)
        return response
    
    async def _post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request"""
        if not self.session:
            await self._create_session()
        response = await self.session.post(url, **kwargs)
        return response
    
    @abstractmethod
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """
        Resolve URL to direct download link(s)
        
        Args:
            url: The URL to resolve
            
        Returns:
            LinkResult or FolderResult
            
        Raises:
            ExtractionFailedException: If extraction fails
        """
        pass

    async def _fetch_file_details(self, url: str, custom_headers: Optional[Dict[str, str]] = None) -> tuple[Optional[str], Optional[int]]:
        """
        Fetch filename and size from URL.
        Uses HEAD request first, then falls back to GET with Range header for size if needed.
        Attempts to extract filename from Content-Disposition or URL.
        Accepts optional custom_headers to be used for the requests.
        """
        filename: Optional[str] = None
        size: Optional[int] = None

        session_created_here = False
        if not self.session:
            await self._create_session()
            session_created_here = True

        if not self.session: # Should not happen if _create_session works
            if session_created_here: await self._close_session()
            return None, None

        request_headers = {}
        if custom_headers:
            request_headers.update(custom_headers)

        # Try HEAD request
        try:
            async with self.session.head(url, headers=request_headers, allow_redirects=True) as resp:
                if resp.status == 200:
                    content_disposition = resp.headers.get("Content-Disposition")
                    if content_disposition:
                        match_utf8 = re.search(r"filename\*=UTF-8''([^']+)$", content_disposition, re.IGNORECASE)
                        if match_utf8:
                            filename = unquote(match_utf8.group(1))
                        else:
                            match_ascii = re.search(r"filename=\"([^\"]+)\"", content_disposition, re.IGNORECASE)
                            if match_ascii:
                                filename = match_ascii.group(1)

                    if not filename:
                        parsed_url = urlparse(url)
                        if parsed_url.path:
                            path_filename = unquote(parsed_url.path.split('/')[-1])
                            if path_filename:
                                filename = path_filename

                    content_length = resp.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        size = int(content_length)
                        # If HEAD gives size, return (handles session_created_here in finally)
                        # No, explicit close if returning early and session was created here.
                        if session_created_here: await self._close_session()
                        return filename, size
        except aiohttp.ClientError:
            pass # HEAD failed, proceed to GET
        except Exception:
            pass # Other error with HEAD

        # Fallback to GET with Range header if size not found
        try:
            get_range_headers = request_headers.copy()
            get_range_headers["Range"] = "bytes=0-0"
            async with self.session.get(url, headers=get_range_headers, allow_redirects=True) as resp:
                if resp.status in (200, 206):
                    # Update filename if not already found (e.g., if HEAD failed)
                    if not filename:
                        content_disposition = resp.headers.get("Content-Disposition")
                        if content_disposition:
                            match_utf8 = re.search(r"filename\*=UTF-8''([^']+)$", content_disposition, re.IGNORECASE)
                            if match_utf8:
                                filename = unquote(match_utf8.group(1))
                            else:
                                match_ascii = re.search(r"filename=\"([^\"]+)\"", content_disposition, re.IGNORECASE)
                                if match_ascii:
                                    filename = match_ascii.group(1)
                        if not filename:
                            parsed_url = urlparse(url)
                            if parsed_url.path:
                                path_filename = unquote(parsed_url.path.split('/')[-1])
                                if path_filename:
                                    filename = path_filename

                    content_range = resp.headers.get("Content-Range")
                    if content_range:
                        try:
                            size = int(content_range.split("/")[-1])
                        except (ValueError, IndexError):
                            pass # Size not found in Content-Range
        except aiohttp.ClientError:
            pass # GET failed
        except Exception:
            pass # Other error with GET

        finally:
            if session_created_here:
                await self._close_session()

        return filename, size

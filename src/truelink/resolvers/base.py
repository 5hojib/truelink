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

    async def _fetch_file_details(self, url: str) -> tuple[Optional[str], Optional[int]]:
        """
        Fetch filename and size from URL using a HEAD request.
        """
        filename: Optional[str] = None
        size: Optional[int] = None

        session_created_here = False
        if not self.session:
            await self._create_session()
            session_created_here = True

        try:
            if not self.session:
                return None, None

            async with self.session.head(url, allow_redirects=True) as response:
                response.raise_for_status() 

                content_disposition = response.headers.get("Content-Disposition")
                if content_disposition:
                    match = re.search(r"filename\*=UTF-8''([^']+)$", content_disposition, re.IGNORECASE)
                    if match:
                        filename = unquote(match.group(1))
                    else:
                        match = re.search(r"filename=\"([^\"]+)\"", content_disposition, re.IGNORECASE)
                        if match:
                            filename = match.group(1)

                if not filename:
                    parsed_url = urlparse(url)
                    if parsed_url.path:
                        filename = unquote(parsed_url.path.split('/')[-1])
                        if not filename: 
                            filename = None

                content_length = response.headers.get("Content-Length")
                if content_length and content_length.isdigit():
                    size = int(content_length)

        except aiohttp.ClientError as e:
            pass
        except Exception as e:
            pass
        finally:
            if session_created_here:
                await self._close_session()

        return filename, size

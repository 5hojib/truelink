import aiohttp
from abc import ABC, abstractmethod
from typing import Union, Dict, Any, Optional

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
        return await self.session.get(url, **kwargs)
    
    async def _post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request"""
        if not self.session:
            await self._create_session()
        return await self.session.post(url, **kwargs)
    
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

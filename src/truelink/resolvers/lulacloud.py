from typing import Union

from .base import BaseResolver
from ..types import LinkResult, FolderResult
from ..exceptions import ExtractionFailedException

class LulaCloudResolver(BaseResolver):
    """Resolver for LulaCloud URLs"""
    
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """Resolve LulaCloud URL"""
        try:
            headers = {"Referer": url}
            async with await self._post(url, headers=headers, allow_redirects=False) as response:
                location = response.headers.get("location")
                if not location:
                    raise ExtractionFailedException("No redirect location found")
                return LinkResult(url=location)
                
        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve LulaCloud URL: {e}") from e

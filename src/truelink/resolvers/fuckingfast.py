import re
from typing import Union

from .base import BaseResolver
from ..types import LinkResult, FolderResult
from ..exceptions import ExtractionFailedException

class FuckingFastResolver(BaseResolver):
    """Resolver for FuckingFast URLs"""
    
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """Resolve FuckingFast URL"""
        try:
            async with await self._get(url) as response:
                content = await response.text()
            
            pattern = r'window\.open\((["\'])(https://fuckingfast\.co/dl/[^"\']+)\1'
            match = re.search(pattern, content)
            
            if not match:
                raise ExtractionFailedException("Could not find download link in page")
            
            return LinkResult(url=match.group(2))
            
        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve FuckingFast URL: {e}") from e

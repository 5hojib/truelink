import re
import logging # Added logging
from typing import Union

from .base import BaseResolver
from ..types import LinkResult, FolderResult
from ..exceptions import ExtractionFailedException

class FuckingFastResolver(BaseResolver):
    """Resolver for FuckingFast URLs"""
    
    async def resolve(self, url: str) -> Union[LinkResult, FolderResult]:
        """Resolve FuckingFast URL"""
        try:
            logging.debug(f"FuckingFastResolver.resolve: Calling self._get('{url}')")
            response_obj_coro = self._get(url)
            logging.debug(f"FuckingFastResolver.resolve: self._get('{url}') returned coro: {response_obj_coro}")
            response_obj = await response_obj_coro
            logging.debug(f"FuckingFastResolver.resolve: awaited self._get('{url}') returned: {type(response_obj)}")
            async with response_obj as response:
                logging.debug(f"FuckingFastResolver.resolve: Entered async with for response: {type(response)}")
                content = await response.text()
            
            pattern = r'window\.open\((["\'])(https://fuckingfast\.co/dl/[^"\']+)\1'
            match = re.search(pattern, content)
            
            if not match:
                raise ExtractionFailedException("Could not find download link in page")
            
            return LinkResult(url=match.group(2))
            
        except Exception as e:
            raise ExtractionFailedException(f"Failed to resolve FuckingFast URL: {e}") from e

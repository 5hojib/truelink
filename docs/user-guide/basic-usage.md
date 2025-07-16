```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver()
    url = "https://buzzheavier.com/rnk4ut0lci9y"

    try:    
        if resolver.is_supported(url):    
            result = await resolver.resolve(url)    
            print(type(result))    
            print(result)    
        else:    
            print(f"URL not supported: {url}")    
    except Exception as e:    
        print(f"Error processing {url}: {e}")

asyncio.run(main())
```

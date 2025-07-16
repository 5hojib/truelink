## Advanced Usage

### Batch Processing

```python
import asyncio
from truelink import TrueLinkResolver

async def process_multiple_urls():
    resolver = TrueLinkResolver()
    urls = [
        "https://buzzheavier.com/rnk4ut0lci9y",
        "https://mediafire.com/file/example",
        "https://gofile.io/d/example"
    ]
    
    tasks = []
    for url in urls:
        if resolver.is_supported(url):
            tasks.append(resolver.resolve(url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Run batch processing
results = asyncio.run(process_multiple_urls())
```


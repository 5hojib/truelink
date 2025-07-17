# Configuration

The `TrueLinkResolver` can be configured with several options to customize its behavior.

## `__init__` Parameters

The following parameters can be passed to the `TrueLinkResolver` constructor:

- **`headers`** (`Optional[dict]`, default: `None`): A dictionary of HTTP headers to use for all requests.
- **`proxy`** (`Optional[str]`, default: `None`): A proxy to use for all HTTP requests.
- **`timeout`** (`Optional[int]`, default: `10`): The timeout in seconds for HTTP requests.

## Example

Here's an example of how to configure the `TrueLinkResolver` with a custom timeout and headers:

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    headers = {"User-Agent": "MyCustomUserAgent/1.0"}
    resolver = TrueLinkResolver(headers=headers, timeout=20)
    url = "https://buzzheavier.com/rnk4ut0lci9y"
    result = await resolver.resolve(url)
    print(result)

asyncio.run(main())
```

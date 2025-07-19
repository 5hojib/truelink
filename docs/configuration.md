# Configuration

The `TrueLinkResolver` can be configured with several options to customize its behavior.

## `__init__` Parameters

The following parameters can be passed to the `TrueLinkResolver` constructor:

- **`timeout`** (`Optional[int]`, default: `10`): The timeout in seconds for HTTP requests.
- **`max_retries`** (`Optional[int]`, default: `3`): The maximum number of retries for failed HTTP requests.

## Example

Here's an example of how to configure the `TrueLinkResolver` with a custom timeout and max_retries:

```python
import asyncio
from truelink import TrueLinkResolver

async def main():
    resolver = TrueLinkResolver(timeout=20, max_retries=5)
    url = "https://buzzheavier.com/rnk4ut0lci9y"
    result = await resolver.resolve(url)
    print(result)

asyncio.run(main())
```

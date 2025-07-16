# Quick Start

This guide will help you get started with TrueLink in just a few minutes.

## Basic Usage

The most common use case is expanding shortened URLs:

```python
from truelink import TrueLink

# Create a TrueLink instance
tl = TrueLink()

# Expand a single URL
expanded = tl.expand("https://bit.ly/example")
print(f"Original: https://bit.ly/example")
print(f"Expanded: {expanded}")
```

## Batch Processing

Process multiple URLs efficiently:

```python
from truelink import TrueLink

urls = [
    "https://bit.ly/example1",
    "https://tinyurl.com/example2",
    "https://t.co/example3"
]

tl = TrueLink()
results = tl.expand_batch(urls)

for original, expanded in results.items():
    print(f"{original} -> {expanded}")
```

## Error Handling

Handle various error scenarios:

```python
from truelink import TrueLink, TrueLinkError

tl = TrueLink()

try:
    result = tl.expand("https://invalid-short-url.com")
    print(result)
except TrueLinkError as e:
    print(f"Error: {e}")
```

## Configuration

Customize TrueLink behavior:

```python
from truelink import TrueLink

# Configure timeout and retry settings
tl = TrueLink(
    timeout=10,
    max_retries=3,
    follow_redirects=True
)

result = tl.expand("https://bit.ly/example")
```

## Common Patterns

### URL Validation
```python
from truelink import TrueLink

tl = TrueLink()

def is_valid_url(url):
    try:
        expanded = tl.expand(url)
        return expanded is not None
    except:
        return False
```

### Link Analysis
```python
from truelink import TrueLink

tl = TrueLink()

def analyze_link(short_url):
    try:
        expanded = tl.expand(short_url)
        return {
            'original': short_url,
            'expanded': expanded,
            'domain': expanded.split('/')[2] if expanded else None
        }
    except Exception as e:
        return {'error': str(e)}
```

## Next Steps

- Read the [User Guide](user-guide/index.md) for detailed information
- Check out [Examples](examples/index.md) for real-world use cases
- Explore the [API Reference](api-reference/index.md) for complete documentation
- Learn about [Advanced Usage](user-guide/advanced-usage.md) for complex scenarios

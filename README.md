# TrueLink

A Python library for resolving media URLs to direct download links from various file hosting services.

## Features

- **Asynchronous**: Built with async/await for efficient handling of multiple requests
- **Easy to use**: Simple API with intuitive method names
- **Extensible**: Support for multiple file hosting platforms
- **Error handling**: Robust error handling for various edge cases
- **URL validation**: Built-in URL validation before processing

## Installation

```bash
pip install truelink
```

## Quick Start

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

## API Reference

### TrueLinkResolver

#### Methods

- `is_supported(url: str) -> bool`: Check if a URL is supported
- `resolve(url: str) -> dict`: Resolve URL to direct download link
- `get_supported_domains() -> list`: Get list of supported domains

#### Return Format

The `resolve()` method returns one of two result types:

**LinkResult** (for single files):
```python
{
    "url": "direct_download_url",
    "filename": "original_filename",
    "mime_type": "video/mp4",
    "size": 1234567,  # Size in bytes (optional)
    "headers": {"Authorization": "Bearer token"}  # Custom headers if needed (optional)
}
```

**FolderResult** (for folders/multi-file links):
```python
{
    "title": "Folder Name",
    "contents": [
        {
            "url": "direct_download_url_1",
            "filename": "file1.pdf",
            "mime_type": "application/pdf",
            "size": 1234567,
            "path": "subfolder/file1.pdf"
        },
        {
            "url": "direct_download_url_2",
            "filename": "file2.jpg",
            "mime_type": "image/jpeg",
            "size": 987654,
            "path": "file2.jpg"
        }
    ],
    "total_size": 2222221,  # Total size of all files
    "headers": {"Authorization": "Bearer token"}  # Custom headers if needed (optional)
}
```

## Supported Sites

### ✅ Working
- [x] buzzheavier
- [x] 1fichier
- [x] fuckingfast
- [x] gofile
- [x] linkbox
- [x] lulacloud
- [x] mediafile (size parsing left)
- [x] mediafire
- [x] pixeldrain
- [x] streamtape
- [x] terabox
- [x] tmpsend
- [x] uploadee
- [x] yandexlink
- [x] ranoz
- [ ] swisstransfer
- [ ] onedrive
- [ ] pcloud

### ⏳ Not Working
- [ ] devuploads (todo)
- [ ] doodstream
- [ ] filepress (todo)
- [ ] krakenfiles
- [ ] uploadhaven (different)
- [ ] wetransfer

## Error Handling

The library provides comprehensive error handling:

```python
from truelink import TrueLinkResolver, TrueLinkException

async def handle_errors():
    resolver = TrueLinkResolver()
    
    try:
        result = await resolver.resolve(url)
    except TrueLinkException as e:
        print(f"TrueLink specific error: {e}")
    except Exception as e:
        print(f"General error: {e}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Adding Support for New Sites

1. Fork the repository
2. Create a new resolver module for your site
3. Add the site to the supported sites list
4. Submit a pull request

## Requirements

- Python 3.7+
- aiohttp
- beautifulsoup4
- requests

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This project is intended for educational and personal use only.

Downloading content using this tool must comply with the terms of service of the respective websites. The developer is not responsible for any misuse or illegal activity involving this software.

Use at your own risk.

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/5hojib/truelink/issues) page
2. Create a new issue with detailed information
3. Include error messages and the URL you're trying to process

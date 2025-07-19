# Welcome to TrueLink

TrueLink is a Python library for resolving media URLs to direct download links from various file hosting services. It's built with `asyncio` to handle multiple requests efficiently and provides a simple, intuitive API for developers.

## Key Features

- **Asynchronous by Design**: Leverages `async/await` syntax for high-performance, non-blocking I/O.
- **Extensible Provider Support**: Easily extendable to support new file hosting services.
- **Robust Error Handling**: Catches common exceptions and provides informative error messages.
- **URL Validation**: Pre-validates URLs to ensure they are supported before processing.
- **Type-Safe**: Fully type-hinted for a better development experience.
- **Caching**: Built-in caching for faster resolution of repeated requests.

## Supported Sites

TrueLink supports a growing list of file hosting services. The table below provides an overview of the currently supported sites and their status.

### Working
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

### Not Working
- [ ] devuploads (todo)
- [ ] doodstream
- [ ] filepress (todo)
- [ ] krakenfiles
- [ ] uploadhaven (different)
- [ ] wetransfer

## Disclaimer

This project is intended for educational and personal use only. Downloading content using this tool must comply with the terms of service of the respective websites. The developer is not responsible for any misuse or illegal activity involving this software. Use at your own risk.

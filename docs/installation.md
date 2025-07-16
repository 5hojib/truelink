# Installation

## Requirements

- Python 3.9 or higher
- An internet connection for URL resolution

## Installation

The recommended way to install TrueLink is from [PyPI](https://pypi.org/project/truelink/) with `pip`:

```bash
pip install truelink
```

## Development Installation

To install TrueLink for development, clone the repository and install it in editable mode with the `dev` extras:

```bash
git clone https://github.com/5hojib/truelink.git
cd truelink
pip install -e ".[dev]"
```

## Verifying the Installation

To verify that TrueLink is installed correctly, you can run the following command:

```bash
python -c "import truelink; print(truelink.__version__)"
```

You should see the installed version number printed to the console.

## Dependencies

TrueLink has the following dependencies:

- `aiohttp`: For making asynchronous HTTP requests.
- `cloudscraper`: To bypass Cloudflare's anti-bot protection.
- `lxml`: For parsing HTML and XML.

These dependencies will be automatically installed when you install TrueLink with `pip`.

# Installation

## Requirements

- Python 3.7 or higher
- pip package manager
- Internet connection for URL resolution

## Install from PyPI

```bash
pip install truelink
```

## Install from Source

```bash
# Clone the repository
git clone https://github.com/5hojib/truelink.git
cd truelink

# Install in development mode
pip install -e .
```

## Development Installation

For development work, install with development dependencies:

```bash
git clone https://github.com/5hojib/truelink.git
cd truelink
pip install -e ".[dev]"
```

## Verify Installation

After installation, verify that TrueLink is working correctly:

```python
import truelink
print(truelink.__version__)

# Test basic functionality
from truelink import TrueLink
tl = TrueLink()
print("TrueLink is ready to use!")
```

## Dependencies

TrueLink relies on the following packages:

- `requests` - For HTTP requests
- `urllib3` - For URL handling
- Additional dependencies will be automatically installed

## Troubleshooting

If you encounter installation issues:

1. **Python Version**: Ensure you're using Python 3.7+
2. **pip Update**: Update pip with `pip install --upgrade pip`
3. **Virtual Environment**: Consider using a virtual environment
4. **Permissions**: On some systems, you might need `sudo` or `--user` flag

For additional help, please [open an issue](https://github.com/5hojib/truelink/issues) on GitHub.

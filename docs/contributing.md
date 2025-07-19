# Contributing to TrueLink

We welcome contributions to TrueLink! This guide will help you get started with contributing to the project.

## Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ``` { .text .no-copy }
   git clone https://github.com/yourusername/truelink.git
   cd truelink
   ```
3. **Create a virtual environment**:
   ``` { .text .no-copy }
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ``` { .text .no-copy }
   pip install -e .
   ```

### Documentation

To work on documentation:

```bash
# Install docs dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve docs locally
mkdocs serve

# Build docs
mkdocs build
```

## Submitting Changes

1. **Create a new branch**:
   ``` { .text .no-copy }
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Write tests** for new functionality

4. **Update documentation** if needed

5. **Run the test suite** to ensure everything passes

6. **Commit your changes**:
   ``` { .text .no-copy }
   git commit -m "Add: description of your changes"
   ```

7. **Push to your fork**:
   ``` { .text .no-copy }
   git push origin feature/your-feature-name
   ```

8. **Submit a pull request** on GitHub

## Pull Request Guidelines

- Provide a clear description of the changes
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Follow the existing code style
- Keep changes focused and atomic

### PR Completion Guide

1.  **Title**: Use a clear and descriptive title that summarizes the changes.
2.  **Description**: Provide a detailed description of the changes, including the problem you are solving and the approach you have taken.
3.  **Link to Issue**: If the PR addresses an existing issue, link to it in the description.
4.  **Screenshots/GIFs**: If the changes are visual, include screenshots or GIFs to demonstrate the changes.
5.  **Testing**: Describe the testing you have done to ensure the changes are working as expected.
6.  **Checklist**: Use the PR template checklist to ensure you have covered all the necessary steps.

## Reporting Issues

When reporting issues:

1. Use a clear and descriptive title
2. Provide steps to reproduce the issue
3. Include relevant error messages
4. Specify your environment (OS, Python version, etc.)
5. Include minimal code examples if applicable

## Code of Conduct

Please be respectful and constructive in all interactions. We want to maintain a welcoming environment for all contributors.

## Getting Help

If you need help with contributing:

- Open an issue for discussion
- Contact the maintainers
- Check existing documentation and examples

Thank you for contributing to TrueLink!

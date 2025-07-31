# Contributing to FileWallBall

Thank you for your interest in contributing to FileWallBall! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/fileWallBall.git`
3. **Install** dependencies: `uv sync --dev`
4. **Create** a feature branch: `git checkout -b feature/your-feature-name`
5. **Make** your changes
6. **Test** your changes: `make test`
7. **Format** your code: `make format`
8. **Commit** your changes (see commit message guidelines below)
9. **Push** to your fork: `git push origin feature/your-feature-name`
10. **Create** a Pull Request

## 📋 Development Setup

### Prerequisites

- Python 3.11+
- uv (Python package manager)
- Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fileWallBall.git
cd fileWallBall

# Install dependencies
uv sync --dev

# Set up pre-commit hooks
uv run pre-commit install

# Verify setup
uv run python scripts/verify_setup.py
```

### Development Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Lint code
make lint

# Run development server
make run

# Clean cache files
make clean
```

## 📝 Code Style Guidelines

### Python Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

### Code Formatting

All code should be formatted using Black with the following settings:
- Line length: 88 characters
- Target Python version: 3.11+

### Import Organization

Imports should be organized using isort with the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

Example:
```python
import os
import sys
from pathlib import Path
from typing import List, Optional

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.models.database import Base
```

### Type Annotations

- Use type annotations for all function parameters and return values
- Use `Optional[T]` for parameters that can be `None`
- Use `Union[T1, T2]` or `T1 | T2` for union types
- Use `List[T]`, `Dict[K, V]`, etc. for generic types

Example:
```python
from typing import List, Optional

def process_files(files: List[str], max_size: Optional[int] = None) -> bool:
    """Process a list of files."""
    pass
```

### Documentation

- Use docstrings for all public functions and classes
- Follow Google-style docstring format
- Include type information in docstrings

Example:
```python
def upload_file(file_path: str, user_id: str) -> dict:
    """Upload a file to the system.

    Args:
        file_path: Path to the file to upload
        user_id: ID of the user uploading the file

    Returns:
        Dictionary containing upload result information

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is too large
    """
    pass
```

## 🧪 Testing Guidelines

### Test Structure

- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- End-to-end tests go in `tests/e2e/`
- Use descriptive test names that explain what is being tested

### Test Naming

- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- Test classes should be named `Test*`

Example:
```python
def test_file_upload_with_valid_file():
    """Test file upload with a valid file."""
    pass

def test_file_upload_with_invalid_file_type():
    """Test file upload with an invalid file type."""
    pass
```

### Test Coverage

- Aim for at least 80% code coverage
- Focus on testing business logic and edge cases
- Use fixtures for common test data and setup

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/unit/test_config.py

# Run tests with coverage
make test-cov

# Run tests with specific markers
uv run pytest -m "unit"
uv run pytest -m "integration"
```

## 📝 Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools

### Examples

```
feat: add file upload endpoint

- Add POST /upload endpoint
- Add file validation
- Add file storage service

Closes #123
```

```
fix(auth): resolve authentication token validation issue

The authentication token validation was failing for tokens with
special characters. This fix properly handles URL-safe base64
encoding.

Fixes #456
```

```
docs: update API documentation

- Add examples for all endpoints
- Update response schemas
- Fix typos in descriptions
```

## 🔄 Pull Request Guidelines

### Before Submitting

1. **Test** your changes thoroughly
2. **Format** your code: `make format`
3. **Lint** your code: `make lint`
4. **Run** tests: `make test`
5. **Update** documentation if needed
6. **Check** that all CI checks pass

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows the style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Documentation is updated
- [ ] Changes generate no new warnings
- [ ] Tests are added that prove the fix is effective or that the feature works

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**: All PRs must pass automated checks
2. **Code Review**: At least one maintainer must approve
3. **Testing**: All tests must pass
4. **Documentation**: Documentation must be updated if needed

## 🐛 Bug Reports

### Before Reporting

1. Check if the issue has already been reported
2. Try to reproduce the issue with the latest version
3. Check the documentation and existing issues

### Bug Report Template

```markdown
## Bug Description
Clear and concise description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g. Ubuntu 22.04]
- Python Version: [e.g. 3.11.5]
- uv Version: [e.g. 0.1.0]
- Browser: [e.g. Chrome 120.0]

## Additional Context
Add any other context about the problem here
```

## 💡 Feature Requests

### Before Requesting

1. Check if the feature has already been requested
2. Consider if the feature aligns with the project's goals
3. Think about the implementation complexity

### Feature Request Template

```markdown
## Feature Description
Clear and concise description of the feature

## Problem Statement
What problem does this feature solve?

## Proposed Solution
How would you like to see this implemented?

## Alternative Solutions
Any alternative solutions you've considered?

## Additional Context
Add any other context or screenshots about the feature request
```

## 📞 Getting Help

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Documentation**: Check the README.md and docs/ directory

## 🏷️ Labels

We use the following labels to categorize issues and pull requests:

- **bug**: Something isn't working
- **documentation**: Improvements or additions to documentation
- **enhancement**: New feature or request
- **good first issue**: Good for newcomers
- **help wanted**: Extra attention is needed
- **question**: Further information is requested
- **wontfix**: This will not be worked on

## 📄 License

By contributing to FileWallBall, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to FileWallBall! 🎉

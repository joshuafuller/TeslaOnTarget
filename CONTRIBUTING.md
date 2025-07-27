# Contributing to TeslaOnTarget

Thank you for your interest in contributing to TeslaOnTarget! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct: be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Issues

- Check if the issue already exists in the issue tracker
- Include clear description of the problem
- Provide steps to reproduce the issue
- Include your environment details (OS, Python version, Tesla model)
- Attach relevant logs (with personal information redacted)

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation as needed
7. Commit with clear messages
8. Push to your fork
9. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install pytest pytest-cov

# Run tests
pytest
```

### Coding Standards

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and small
- Handle errors gracefully with proper logging
- Never commit sensitive data (API keys, locations, etc.)

### Testing

- Write unit tests for new features
- Ensure existing tests pass
- Test with both real Tesla API and mock data
- Verify TAK server compatibility

### Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions
- Update CHANGELOG.md for notable changes
- Include examples where appropriate

## Release Process

### Automated Release
1. Update version in `teslaontarget/__init__.py` and `setup.py`
2. Update CHANGELOG.md with release notes
3. Commit changes: `git commit -am "Release v1.0.0"`
4. Create and push tag:
   ```bash
   git tag v1.0.0
   git push origin main v1.0.0
   ```
5. GitHub Actions will automatically:
   - Build and push Docker images to ghcr.io
   - Create GitHub release with changelog
   - Tag images with version numbers

### Docker Images
- Images are automatically built on every push to main
- Tagged releases create versioned images
- Pull requests create temporary images for testing
- Multi-architecture builds for amd64 and arm64

## Questions?

Feel free to open an issue for any questions about contributing.
# Contributing to Inkbird Irrigation Integration

Thank you for your interest in contributing! Here's how you can help.

## Reporting Issues

Found a bug? Please open an issue on [GitHub Issues](https://github.com/ac-uy/ha-inkbird-irrigation/issues) with:

- **Description**: What's the problem?
- **Steps to reproduce**: How can we replicate it?
- **Expected behavior**: What should happen?
- **Actual behavior**: What actually happens?
- **Logs**: Include relevant Home Assistant logs (Settings → System → Logs)
- **Environment**: HA version, device model, firmware version

## Feature Requests

Have an idea? Open an issue with the `enhancement` label and describe:

- **Use case**: Why is this needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Any other approaches?

## Development

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ac-uy/ha-inkbird-irrigation.git
   cd ha-inkbird-irrigation
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install tinytuya
   ```

### Testing

Scan for devices on your network:
```bash
python -m tinytuya scan
```

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and testable

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation changes
- **refactor**: Code refactoring
- **chore**: Build, dependencies, or tooling changes

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly
5. Commit with conventional commit messages
6. Push to your fork
7. Open a Pull Request

## IIC-800 Support

If you have an IIC-800-WIFI (8-zone model), we'd love help testing compatibility. The DP mapping is likely similar but with 8 zones instead of 6.

## Questions?

Open an issue or reach out on the [Home Assistant Community Forum](https://community.home-assistant.io/).

Thank you for contributing! 💧

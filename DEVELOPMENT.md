# Development Guide

This document provides information about the development workflow and code quality tools used in this project.

## Code Quality Tools

The project uses several code quality tools to maintain code consistency and catch potential issues:

### Formatting & Linting

- **Black**: Automatic code formatter for Python
  - Line length: 88 characters
  - Target Python version: 3.13

- **isort**: Import statement organizer
  - Profile: black (compatible with Black formatting)

- **flake8**: Linter for code quality
  - Ignores common style issues handled by Black
  - Excludes build artifacts and dependencies

### Type Checking

- **mypy**: Static type checker
  - Gradual typing approach (currently permissive)
  - Configured to ignore missing imports for external libraries

## Setup

### Initial Setup

```bash
# Run the development setup script
./scripts/dev-setup.sh
```

This will:
- Install all dependencies including development tools
- Make scripts executable
- Run initial quality checks

### Manual Setup

```bash
# Install base dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Make scripts executable
chmod +x scripts/*.sh
```

## Development Workflow

### Daily Development

1. **Format code**: `./scripts/format-code.sh`
   - Runs Black and isort to format all Python files

2. **Check quality**: `./scripts/check-quality.sh`
   - Runs Black, isort, flake8, and mypy
   - Exits with error code if any issues are found

### Individual Tools

```bash
# Format code with Black
uv run black .

# Sort imports with isort
uv run isort .

# Run flake8 linter
uv run flake8 .

# Run mypy type checker
uv run mypy backend/
```

## Configuration

All tool configurations are centralized in `pyproject.toml`:

- `[tool.black]` - Black formatting settings
- `[tool.isort]` - Import sorting settings
- `[tool.mypy]` - Type checking configuration
- `[tool.flake8]` - Linting rules and exclusions

## Pre-commit Integration (Optional)

For a better development experience, you can set up pre-commit hooks to automatically run quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml (if not exists)
# Then install hooks
pre-commit install
```

## IDE Integration

### VS Code

Install these extensions for optimal development:
- Black Formatter
- isort
- flake8
- MyPy

Configure in `.vscode/settings.json`:

```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true
}
```

### PyCharm

Configure in Settings → Tools → External Tools:
- Add Black, isort, flake8 as external tools
- Set up keyboard shortcuts for quick access

## Quality Standards

The project aims to maintain:

- **Consistent formatting**: All code formatted with Black
- **Clean imports**: Properly sorted and organized imports
- **Type safety**: Gradually improving type coverage
- **Code complexity**: Functions with complexity ≤ 10
- **No unused imports**: Clean import statements

## Troubleshooting

### Common Issues

1. **Black conflicts**: If Black reformats your code unexpectedly, run `./scripts/format-code.sh` to fix all files at once.

2. **Import ordering**: Use isort to automatically organize imports rather than manual sorting.

3. **Type checking errors**: Add type annotations or use `# type: ignore` for external library issues.

4. **Complexity warnings**: Consider breaking down complex functions into smaller, more focused functions.

### Getting Help

- Check the configuration in `pyproject.toml`
- Run tools individually to see specific error messages
- Consult tool documentation for advanced configuration options
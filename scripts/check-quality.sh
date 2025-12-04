#!/bin/bash
# Code quality check script

set -e  # Exit on any error

echo "🔍 Running code quality checks..."

echo -e "\n📝 Checking code formatting with Black..."
if command -v uv &> /dev/null; then
    uv run black --check --diff .
else
    black --check --diff .
fi

echo -e "\n🔤 Checking import sorting with isort..."
if command -v uv &> /dev/null; then
    uv run isort --check-only --diff .
else
    isort --check-only --diff .
fi

echo -e "\n🧹 Linting with flake8..."
if command -v uv &> /dev/null; then
    uv run flake8 .
else
    flake8 .
fi

echo -e "\n🏷️  Type checking with mypy..."
if command -v uv &> /dev/null; then
    uv run mypy backend/
else
    mypy backend/
fi

echo -e "\n✅ All quality checks passed!"
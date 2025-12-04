#!/bin/bash
# Code formatting script

set -e  # Exit on any error

echo "🎨 Formatting code..."

echo -e "\n📝 Formatting with Black..."
if command -v uv &> /dev/null; then
    uv run black .
else
    black .
fi

echo -e "\n🔤 Sorting imports with isort..."
if command -v uv &> /dev/null; then
    uv run isort .
else
    isort .
fi

echo -e "\n✅ Code formatting complete!"
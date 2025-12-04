#!/bin/bash
# Development environment setup script

set -e  # Exit on any error

echo "🛠️  Setting up development environment..."

echo -e "\n📦 Installing base dependencies..."
if command -v uv &> /dev/null; then
    uv sync
    echo -e "\n📦 Installing development dependencies..."
    uv sync --group dev
else
    echo "❌ uv not found. Please install uv first: https://docs.astral.sh/uv/"
    exit 1
fi

echo -e "\n🔐 Making scripts executable..."
chmod +x scripts/*.sh

echo -e "\n🧪 Running initial code quality checks..."
./scripts/check-quality.sh || {
    echo -e "\n⚠️  Some quality checks failed. Run './scripts/format-code.sh' to auto-fix formatting issues."
}

echo -e "\n✅ Development environment setup complete!"
echo -e "\n📋 Available commands:"
echo -  "  ./scripts/format-code.sh     - Format all code"
echo -  "  ./scripts/check-quality.sh   - Run quality checks"
echo -  "  ./run.sh                     - Start the application"
#!/bin/bash
# Run all code quality checks

set -e  # Exit on first error

echo "========================================="
echo "Running Code Quality Checks"
echo "========================================="
echo ""

echo "1. Checking import organization (isort)..."
uv run isort --check-only backend/ main.py
echo "✓ Import organization check passed!"
echo ""

echo "2. Checking code formatting (black)..."
uv run black --check backend/ main.py
echo "✓ Code formatting check passed!"
echo ""

echo "3. Running linter (flake8)..."
uv run flake8 backend/ main.py
echo "✓ Linting check passed!"
echo ""

echo "4. Running type checker (mypy)..."
uv run mypy backend/ main.py
echo "✓ Type checking passed!"
echo ""

echo "========================================="
echo "✓ All quality checks passed!"
echo "========================================="

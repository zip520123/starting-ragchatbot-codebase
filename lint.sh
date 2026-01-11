#!/bin/bash
# Run linting checks with flake8

echo "Running flake8..."
uv run flake8 backend/ main.py

if [ $? -eq 0 ]; then
    echo "✓ No linting issues found!"
else
    echo "✗ Linting issues detected. Please fix them."
    exit 1
fi

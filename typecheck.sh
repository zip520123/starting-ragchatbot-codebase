#!/bin/bash
# Run type checking with mypy

echo "Running mypy..."
uv run mypy backend/ main.py

if [ $? -eq 0 ]; then
    echo "✓ No type errors found!"
else
    echo "✗ Type errors detected. Please review them."
    exit 1
fi

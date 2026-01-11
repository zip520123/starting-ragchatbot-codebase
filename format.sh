#!/bin/bash
# Format code with isort and black

echo "Running isort..."
uv run isort backend/ main.py

echo "Running black..."
uv run black backend/ main.py

echo "✓ Code formatting complete!"

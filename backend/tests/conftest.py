"""Shared fixtures for RAG system tests."""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import SearchResults


@pytest.fixture
def mock_search_results():
    """Factory fixture to create SearchResults with custom data."""
    def _create(documents=None, metadata=None, distances=None, error=None):
        return SearchResults(
            documents=documents or [],
            metadata=metadata or [],
            distances=distances or [],
            error=error
        )
    return _create


@pytest.fixture
def sample_search_results(mock_search_results):
    """Sample search results with realistic course data."""
    return mock_search_results(
        documents=[
            "MCP servers allow AI models to access external tools and data sources.",
            "To create an MCP server, you need to implement the server protocol."
        ],
        metadata=[
            {"course_title": "MCP: Build Rich-Context AI Apps", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "MCP: Build Rich-Context AI Apps", "lesson_number": 2, "chunk_index": 5}
        ],
        distances=[0.25, 0.35]
    )


@pytest.fixture
def empty_search_results(mock_search_results):
    """Empty search results."""
    return mock_search_results()


@pytest.fixture
def error_search_results(mock_search_results):
    """Search results with error."""
    return mock_search_results(error="No course found matching 'nonexistent'")


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing tools."""
    store = Mock()
    store.max_results = 5

    # Default search behavior
    store.search.return_value = SearchResults(
        documents=["Sample content about MCP servers."],
        metadata=[{"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0}],
        distances=[0.2]
    )

    # Default lesson link behavior
    store.get_lesson_link.return_value = "https://example.com/lesson1"

    return store


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager for testing AI generator."""
    manager = Mock()
    manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "course_name": {"type": "string"},
                    "lesson_number": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    ]
    manager.execute_tool.return_value = "Search result: MCP servers provide external tool access."
    manager.get_last_sources.return_value = ["[MCP Course - Lesson 1](https://example.com)"]
    manager.reset_sources.return_value = None
    return manager


@pytest.fixture
def mock_anthropic_response_text():
    """Mock Anthropic API response with direct text."""
    response = Mock()
    response.stop_reason = "end_turn"

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "MCP servers enable AI models to access external tools."

    response.content = [text_block]
    return response


@pytest.fixture
def mock_anthropic_response_tool_use():
    """Mock Anthropic API response with tool use."""
    response = Mock()
    response.stop_reason = "tool_use"

    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.id = "tool_123"
    tool_block.name = "search_course_content"
    tool_block.input = {"query": "MCP servers"}

    response.content = [tool_block]
    return response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response_text):
    """Mock Anthropic client."""
    client = Mock()
    client.messages.create.return_value = mock_anthropic_response_text
    return client

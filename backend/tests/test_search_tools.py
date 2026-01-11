"""Tests for CourseSearchTool execute method outputs."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test suite for CourseSearchTool.execute() method."""

    def test_execute_returns_formatted_results(self, mock_vector_store):
        """Test that execute returns properly formatted search results."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content about MCP protocol."],
            metadata=[
                {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.2],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="MCP protocol")

        # Assert
        assert "[MCP Course - Lesson 1]" in result
        assert "Content about MCP protocol." in result
        mock_vector_store.search.assert_called_once_with(
            query="MCP protocol", course_name=None, lesson_number=None
        )

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test execute with course_name filter."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Filtered content."],
            metadata=[
                {
                    "course_title": "Specific Course",
                    "lesson_number": 2,
                    "chunk_index": 0,
                }
            ],
            distances=[0.15],
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="topic", course_name="Specific Course")

        # Assert
        mock_vector_store.search.assert_called_once_with(
            query="topic", course_name="Specific Course", lesson_number=None
        )
        assert "[Specific Course - Lesson 2]" in result

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test execute with lesson_number filter."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Lesson specific content."],
            metadata=[{"course_title": "Course", "lesson_number": 3, "chunk_index": 0}],
            distances=[0.1],
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="topic", lesson_number=3)

        # Assert
        mock_vector_store.search.assert_called_once_with(
            query="topic", course_name=None, lesson_number=3
        )

    def test_execute_with_both_filters(self, mock_vector_store):
        """Test execute with both course_name and lesson_number filters."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Specific content."],
            metadata=[
                {"course_title": "MCP Course", "lesson_number": 2, "chunk_index": 0}
            ],
            distances=[0.05],
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="servers", course_name="MCP", lesson_number=2)

        # Assert
        mock_vector_store.search.assert_called_once_with(
            query="servers", course_name="MCP", lesson_number=2
        )

    def test_execute_returns_error_message_on_search_error(self, mock_vector_store):
        """Test that execute returns error message when search fails."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="No course found matching 'nonexistent'",
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="topic", course_name="nonexistent")

        # Assert
        assert result == "No course found matching 'nonexistent'"

    def test_execute_returns_no_results_message_when_empty(self, mock_vector_store):
        """Test that execute returns appropriate message for empty results."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="obscure topic")

        # Assert
        assert "No relevant content found" in result

    def test_execute_empty_results_with_course_filter_message(self, mock_vector_store):
        """Test empty results message includes course filter info."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="topic", course_name="MCP Course")

        # Assert
        assert "No relevant content found" in result
        assert "in course 'MCP Course'" in result

    def test_execute_empty_results_with_lesson_filter_message(self, mock_vector_store):
        """Test empty results message includes lesson filter info."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="topic", lesson_number=5)

        # Assert
        assert "No relevant content found" in result
        assert "in lesson 5" in result

    def test_execute_tracks_sources_with_links(self, mock_vector_store):
        """Test that execute properly tracks sources with markdown links."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content here."],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.2],
        )
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/test-lesson-1"
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        tool.execute(query="test")

        # Assert
        assert len(tool.last_sources) == 1
        assert "[Test Course - Lesson 1]" in tool.last_sources[0]
        assert "(https://example.com/test-lesson-1)" in tool.last_sources[0]

    def test_execute_tracks_sources_without_links(self, mock_vector_store):
        """Test source tracking when no lesson link is available."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content here."],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.2],
        )
        mock_vector_store.get_lesson_link.return_value = None
        tool = CourseSearchTool(mock_vector_store)

        # Act
        tool.execute(query="test")

        # Assert
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0] == "Test Course - Lesson 1"

    def test_execute_formats_multiple_results(self, mock_vector_store):
        """Test formatting of multiple search results."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["First result.", "Second result.", "Third result."],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Course B", "lesson_number": 2, "chunk_index": 1},
                {"course_title": "Course A", "lesson_number": 3, "chunk_index": 2},
            ],
            distances=[0.1, 0.2, 0.3],
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="test")

        # Assert
        assert "[Course A - Lesson 1]" in result
        assert "[Course B - Lesson 2]" in result
        assert "[Course A - Lesson 3]" in result
        assert "First result." in result
        assert "Second result." in result
        assert "Third result." in result
        assert len(tool.last_sources) == 3

    def test_execute_handles_missing_lesson_number(self, mock_vector_store):
        """Test formatting when lesson_number is None in metadata."""
        # Arrange
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content without lesson."],
            metadata=[
                {
                    "course_title": "General Course",
                    "lesson_number": None,
                    "chunk_index": 0,
                }
            ],
            distances=[0.2],
        )
        tool = CourseSearchTool(mock_vector_store)

        # Act
        result = tool.execute(query="general")

        # Assert
        assert "[General Course]" in result
        assert "Lesson" not in result.split("\n")[0]  # No lesson in header


class TestCourseSearchToolDefinition:
    """Test suite for CourseSearchTool tool definition."""

    def test_get_tool_definition_has_required_fields(self, mock_vector_store):
        """Test that tool definition has all required Anthropic fields."""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["name"] == "search_course_content"

    def test_get_tool_definition_schema_structure(self, mock_vector_store):
        """Test input schema has correct structure."""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()
        schema = definition["input_schema"]

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]


class TestToolManager:
    """Test suite for ToolManager."""

    def test_register_tool(self, mock_vector_store):
        """Test tool registration."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_execute_tool(self, mock_vector_store):
        """Test tool execution through manager."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Test content."],
            metadata=[{"course_title": "Test", "lesson_number": 1, "chunk_index": 0}],
            distances=[0.1],
        )
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test")

        assert "Test content." in result

    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store):
        """Test retrieving sources after search."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content."],
            metadata=[{"course_title": "Test", "lesson_number": 1, "chunk_index": 0}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com"
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) == 1

    def test_reset_sources(self, mock_vector_store):
        """Test resetting sources."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content."],
            metadata=[{"course_title": "Test", "lesson_number": 1, "chunk_index": 0}],
            distances=[0.1],
        )
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        manager.reset_sources()
        sources = manager.get_last_sources()

        assert sources == []

"""Integration tests that reveal issues with mock vs real AI generator."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMockAIGeneratorBehavior:
    """Tests that reveal MockAIGenerator limitations."""

    def test_mock_ai_generator_ignores_tools(self):
        """Test that MockAIGenerator does not execute tools - THIS IS THE ISSUE."""
        from unittest.mock import Mock

        from mock_ai_generator import MockAIGenerator
        from search_tools import CourseSearchTool, ToolManager

        # Setup
        mock_response = "Static mock response"
        mock_sources = ["[Mock Source](http://example.com)"]
        mock_ai = MockAIGenerator(mock_response, mock_sources)

        mock_vector_store = Mock()
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        tools = tool_manager.get_tool_definitions()

        # Act - Call generate_response with tools
        result = mock_ai.generate_response(
            query="What are MCP servers?", tools=tools, tool_manager=tool_manager
        )

        # Assert - MockAIGenerator returns static response, ignoring the query
        assert result == mock_response  # Always returns same thing
        # The vector store was NEVER called - tools are not used
        mock_vector_store.search.assert_not_called()

    def test_mock_ai_generator_sets_sources_without_search(self):
        """Test that MockAIGenerator sets sources without actually searching."""
        from unittest.mock import Mock

        from mock_ai_generator import MockAIGenerator
        from search_tools import CourseSearchTool, ToolManager

        mock_sources = ["[Fake Source](http://fake.com)"]
        mock_ai = MockAIGenerator("Response", mock_sources)

        mock_vector_store = Mock()
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        # Act
        mock_ai.generate_response(
            query="Any query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Assert - Sources are set directly without search
        assert tool_manager.get_last_sources() == mock_sources
        # But vector store was never queried
        mock_vector_store.search.assert_not_called()

    def test_mock_ai_response_is_query_independent(self):
        """Test that MockAIGenerator returns same response regardless of query."""
        from mock_ai_generator import MockAIGenerator

        mock_ai = MockAIGenerator("Fixed response about cats")

        # Different queries should give different responses in a real system
        response1 = mock_ai.generate_response(query="What is MCP?")
        response2 = mock_ai.generate_response(query="How do I cook pasta?")
        response3 = mock_ai.generate_response(query="What is quantum physics?")

        # But MockAIGenerator returns the same thing for all queries
        assert response1 == response2 == response3 == "Fixed response about cats"


class TestAppConfiguration:
    """Tests that check app configuration."""

    def test_app_uses_real_ai_generator_with_api_key(self):
        """Test that app.py uses real AIGenerator when API key is available."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            app_content = f.read()

        # App should import real AIGenerator
        assert "from ai_generator import AIGenerator" in app_content
        # App should check for API key
        assert "config.ANTHROPIC_API_KEY" in app_content
        # App should use real AIGenerator when key is present
        assert "AIGenerator(api_key=" in app_content

    def test_app_falls_back_to_mock_without_api_key(self):
        """Test that app.py falls back to MockAIGenerator when no API key."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            app_content = f.read()

        # Should have fallback to mock
        assert "MockAIGenerator" in app_content
        # Should NOT have hardcoded cat facts anymore
        assert "Cats are fascinating creatures" not in app_content
        assert "placekitten" not in app_content


class TestRealAIGeneratorContract:
    """Tests that verify AIGenerator contract that MockAIGenerator should follow."""

    def test_ai_generator_interface_compatibility(self):
        """Test that MockAIGenerator has same interface as AIGenerator."""
        import inspect

        from mock_ai_generator import MockAIGenerator

        # Check MockAIGenerator has generate_response method
        assert hasattr(MockAIGenerator, "generate_response")

        # Check method signature
        sig = inspect.signature(MockAIGenerator.generate_response)
        params = list(sig.parameters.keys())

        assert "query" in params
        assert "conversation_history" in params
        assert "tools" in params
        assert "tool_manager" in params

    def test_mock_should_support_tool_execution(self):
        """
        Test documenting that MockAIGenerator SHOULD support tool execution.

        Currently it doesn't, which means:
        1. Search queries return static responses
        2. Course outline queries return static responses
        3. The tool system is completely bypassed

        FIX: Either use real AIGenerator or update MockAIGenerator to:
        - Parse the query to determine if tools should be used
        - Actually call tool_manager.execute_tool() when appropriate
        """
        from unittest.mock import Mock

        from mock_ai_generator import MockAIGenerator
        from search_tools import CourseSearchTool, ToolManager
        from vector_store import SearchResults

        # Setup a mock that would return real results
        mock_vector_store = Mock()
        mock_vector_store.search.return_value = SearchResults(
            documents=["MCP servers enable AI to access external tools."],
            metadata=[
                {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://real-link.com"

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        mock_ai = MockAIGenerator("Static response ignoring all context")

        # Even with real tool setup, MockAIGenerator ignores it
        result = mock_ai.generate_response(
            query="What are MCP servers?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # This demonstrates the problem:
        assert "MCP servers enable AI" not in result  # Real content is NOT in response
        assert (
            result == "Static response ignoring all context"
        )  # Static response instead

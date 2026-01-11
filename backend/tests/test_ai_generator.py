"""Tests for AIGenerator tool calling functionality."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator


class TestAIGeneratorToolCalling:
    """Test suite for AIGenerator's tool calling behavior."""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator with mocked Anthropic client."""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )
            generator.client = mock_anthropic.return_value
            return generator

    def test_generate_response_without_tools(self, ai_generator):
        """Test response generation without tools (direct answer)."""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "This is a direct answer."
        mock_response.content = [text_block]

        ai_generator.client.messages.create.return_value = mock_response

        # Act
        result = ai_generator.generate_response(query="What is Python?")

        # Assert
        assert result == "This is a direct answer."
        ai_generator.client.messages.create.assert_called_once()

    def test_generate_response_with_tools_available(
        self, ai_generator, mock_tool_manager
    ):
        """Test that tools are passed to API when available."""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response with tools available."
        mock_response.content = [text_block]

        ai_generator.client.messages.create.return_value = mock_response
        tools = mock_tool_manager.get_tool_definitions()

        # Act
        result = ai_generator.generate_response(
            query="Search for MCP", tools=tools, tool_manager=mock_tool_manager
        )

        # Assert
        call_kwargs = ai_generator.client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_generate_response_triggers_tool_use(self, ai_generator, mock_tool_manager):
        """Test that tool_use stop_reason triggers tool execution."""
        # Arrange - First response requests tool use
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_abc123"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "MCP servers"}
        tool_response.content = [tool_block]

        # Second response is the final answer
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "MCP servers enable external tool access."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]

        tools = mock_tool_manager.get_tool_definitions()

        # Act
        result = ai_generator.generate_response(
            query="What are MCP servers?", tools=tools, tool_manager=mock_tool_manager
        )

        # Assert
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="MCP servers"
        )
        assert result == "MCP servers enable external tool access."
        assert ai_generator.client.messages.create.call_count == 2

    def test_tool_execution_passes_correct_parameters(
        self, ai_generator, mock_tool_manager
    ):
        """Test that tool execution receives all input parameters."""
        # Arrange
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_xyz"
        tool_block.name = "search_course_content"
        tool_block.input = {
            "query": "authentication",
            "course_name": "Security Course",
            "lesson_number": 3,
        }
        tool_response.content = [tool_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Authentication info from Security Course."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]

        # Act
        ai_generator.generate_response(
            query="Tell me about authentication",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="authentication",
            course_name="Security Course",
            lesson_number=3,
        )

    def test_tool_result_included_in_follow_up_message(
        self, ai_generator, mock_tool_manager
    ):
        """Test that tool results are properly formatted in follow-up API call."""
        # Arrange
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_123"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [tool_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Final answer."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        # Act
        ai_generator.generate_response(
            query="Test query",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert - Check the second call includes tool results
        second_call = ai_generator.client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        # Should have: user message, assistant tool_use, user tool_result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Check tool result format
        tool_result_content = messages[2]["content"]
        assert len(tool_result_content) == 1
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["tool_use_id"] == "tool_123"
        assert tool_result_content[0]["content"] == "Tool execution result"

    def test_conversation_history_included_in_system_prompt(self, ai_generator):
        """Test that conversation history is added to system prompt."""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response with history."
        mock_response.content = [text_block]

        ai_generator.client.messages.create.return_value = mock_response
        history = "User: What is MCP?\nAssistant: MCP is Model Context Protocol."

        # Act
        ai_generator.generate_response(
            query="Tell me more", conversation_history=history
        )

        # Assert
        call_kwargs = ai_generator.client.messages.create.call_args[1]
        assert history in call_kwargs["system"]
        assert "Previous conversation:" in call_kwargs["system"]

    def test_no_tool_execution_without_tool_manager(self, ai_generator):
        """Test that tool_use is not processed without tool_manager."""
        # Arrange
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_123"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [tool_block]

        ai_generator.client.messages.create.return_value = tool_response

        # Act - Call without tool_manager
        result = ai_generator.generate_response(
            query="Test", tools=[{"name": "search_course_content"}], tool_manager=None
        )

        # Assert - Only 1 API call made, tool_use not processed
        # Returns empty string since no text block in response
        assert ai_generator.client.messages.create.call_count == 1
        assert result == ""


class TestAIGeneratorSystemPrompt:
    """Test suite for AIGenerator system prompt configuration."""

    def test_system_prompt_mentions_search_tool(self):
        """Test that system prompt mentions search_course_content tool."""
        assert "search_course_content" in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_mentions_outline_tool(self):
        """Test that system prompt mentions get_course_outline tool."""
        assert "get_course_outline" in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_includes_usage_guidelines(self):
        """Test that system prompt includes tool usage guidelines."""
        prompt = AIGenerator.SYSTEM_PROMPT
        assert "Tool Usage" in prompt or "tool" in prompt.lower()

    def test_system_prompt_includes_response_protocol(self):
        """Test that system prompt includes response formatting guidelines."""
        prompt = AIGenerator.SYSTEM_PROMPT
        assert "Response Protocol" in prompt or "response" in prompt.lower()


class TestAIGeneratorConfiguration:
    """Test suite for AIGenerator configuration."""

    def test_base_params_configuration(self):
        """Test that base API parameters are correctly configured."""
        with patch("ai_generator.anthropic.Anthropic"):
            generator = AIGenerator(api_key="test", model="claude-sonnet-4-20250514")

        assert generator.base_params["model"] == "claude-sonnet-4-20250514"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    def test_custom_model_configuration(self):
        """Test that custom model is properly set."""
        with patch("ai_generator.anthropic.Anthropic"):
            generator = AIGenerator(api_key="test", model="custom-model")

        assert generator.model == "custom-model"
        assert generator.base_params["model"] == "custom-model"

    def test_max_tool_rounds_constant(self):
        """Test that MAX_TOOL_ROUNDS is set to 2."""
        assert AIGenerator.MAX_TOOL_ROUNDS == 2


class TestSequentialToolCalling:
    """Test suite for sequential tool calling functionality."""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator with mocked Anthropic client."""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )
            generator.client = mock_anthropic.return_value
            return generator

    def test_two_sequential_tool_calls(self, ai_generator, mock_tool_manager):
        """Test Claude makes two sequential tool calls before final response."""
        # Arrange - First tool call
        tool_response_1 = Mock()
        tool_response_1.stop_reason = "tool_use"
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "tool_1"
        tool_block_1.name = "get_course_outline"
        tool_block_1.input = {"course_name": "MCP Course"}
        tool_response_1.content = [tool_block_1]

        # Second tool call
        tool_response_2 = Mock()
        tool_response_2.stop_reason = "tool_use"
        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.id = "tool_2"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "MCP servers"}
        tool_response_2.content = [tool_block_2]

        # Final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Answer based on both tool results."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response_1,
            tool_response_2,
            final_response,
        ]

        # Act
        result = ai_generator.generate_response(
            query="Find related content",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert
        assert result == "Answer based on both tool results."
        assert ai_generator.client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_max_rounds_enforced(self, ai_generator, mock_tool_manager):
        """Test that after 2 rounds, final call is made without tools."""
        # Arrange - Two tool calls that would continue if allowed
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [tool_block]

        # Final response after max rounds
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Final answer after max rounds."
        final_response.content = [text_block]

        # Two tool responses followed by final (forced after max rounds)
        ai_generator.client.messages.create.side_effect = [
            tool_response,
            tool_response,
            final_response,
        ]

        # Act
        result = ai_generator.generate_response(
            query="Test query",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert - 3 API calls: 2 tool rounds + 1 final
        assert ai_generator.client.messages.create.call_count == 3
        assert result == "Final answer after max rounds."

        # Verify final call has no tools
        final_call = ai_generator.client.messages.create.call_args_list[2]
        assert "tools" not in final_call[1]

    def test_tools_included_in_second_api_call(self, ai_generator, mock_tool_manager):
        """Test that second API call includes tools (allows further tool use)."""
        # Arrange
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [tool_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Final answer."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]
        tools = mock_tool_manager.get_tool_definitions()

        # Act
        ai_generator.generate_response(
            query="Test", tools=tools, tool_manager=mock_tool_manager
        )

        # Assert - Second call should have tools
        second_call = ai_generator.client.messages.create.call_args_list[1]
        assert "tools" in second_call[1]
        assert second_call[1]["tools"] == tools

    def test_messages_accumulate_correctly(self, ai_generator, mock_tool_manager):
        """Test that messages accumulate correctly across rounds."""
        # Arrange - Two tool calls
        tool_response_1 = Mock()
        tool_response_1.stop_reason = "tool_use"
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "tool_1"
        tool_block_1.name = "get_course_outline"
        tool_block_1.input = {"course_name": "Test"}
        tool_response_1.content = [tool_block_1]

        tool_response_2 = Mock()
        tool_response_2.stop_reason = "tool_use"
        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.id = "tool_2"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "related"}
        tool_response_2.content = [tool_block_2]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Complete answer."
        final_response.content = [text_block]

        ai_generator.client.messages.create.side_effect = [
            tool_response_1,
            tool_response_2,
            final_response,
        ]
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        # Act
        ai_generator.generate_response(
            query="Initial query",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert - Check messages in final call
        final_call = ai_generator.client.messages.create.call_args_list[2]
        messages = final_call[1]["messages"]

        # Should have 5 messages: user, assistant(tool1), user(result1), assistant(tool2), user(result2)
        assert len(messages) == 5
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Initial query"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"

    def test_tool_execution_error_terminates(self, ai_generator, mock_tool_manager):
        """Test that tool execution error terminates loop gracefully."""
        # Arrange
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [tool_block]

        ai_generator.client.messages.create.return_value = tool_response
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")

        # Act
        result = ai_generator.generate_response(
            query="Test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert - Only 1 API call (loop terminated on error)
        assert ai_generator.client.messages.create.call_count == 1
        assert "issue" in result.lower() or "error" in result.lower()

    def test_tool_execution_error_returns_partial_text(
        self, ai_generator, mock_tool_manager
    ):
        """Test that tool error returns text if available in response."""
        # Arrange - Response has both text and tool_use
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Let me search for that."
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "tool_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_response.content = [text_block, tool_block]

        ai_generator.client.messages.create.return_value = tool_response
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")

        # Act
        result = ai_generator.generate_response(
            query="Test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager,
        )

        # Assert - Should return the text from response
        assert result == "Let me search for that."


class TestSystemPromptUpdates:
    """Test suite for updated system prompt with sequential tool calling."""

    def test_system_prompt_mentions_two_tool_calls(self):
        """Test that system prompt mentions 2 sequential tool calls allowed."""
        assert "2 sequential tool calls" in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_does_not_mention_one_tool_limit(self):
        """Test that old single tool call limit is removed."""
        assert "One tool call per query maximum" not in AIGenerator.SYSTEM_PROMPT

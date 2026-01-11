"""Tests for RAG system query handling."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRAGSystemQueryHandling:
    """Test suite for RAGSystem.query() content-related question handling."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 10
        return config

    @pytest.fixture
    def mock_ai_generator(self):
        """Create mock AI generator."""
        generator = Mock()
        generator.generate_response.return_value = "This is the AI response about MCP."
        return generator

    @pytest.fixture
    def rag_system(self, mock_config, mock_ai_generator):
        """Create RAGSystem with mocked dependencies."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.SessionManager") as mock_sm,
        ):

            # Setup mock vector store
            mock_vector_store = Mock()
            mock_vector_store.max_results = 5
            mock_vs.return_value = mock_vector_store

            # Setup mock session manager
            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history.return_value = None
            mock_session_manager.create_session.return_value = "test-session-123"
            mock_sm.return_value = mock_session_manager

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai_generator)
            system.vector_store = mock_vector_store
            system.session_manager = mock_session_manager

            return system

    def test_query_returns_response_and_sources(self, rag_system, mock_ai_generator):
        """Test that query returns both response and sources."""
        # Act
        response, sources = rag_system.query("What is MCP?")

        # Assert
        assert response == "This is the AI response about MCP."
        assert isinstance(sources, list)

    def test_query_passes_tools_to_ai_generator(self, rag_system, mock_ai_generator):
        """Test that query passes tool definitions to AI generator."""
        # Act
        rag_system.query("What is MCP?")

        # Assert
        call_kwargs = mock_ai_generator.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) > 0

    def test_query_passes_tool_manager(self, rag_system, mock_ai_generator):
        """Test that query passes tool_manager to AI generator."""
        # Act
        rag_system.query("Search for authentication")

        # Assert
        call_kwargs = mock_ai_generator.generate_response.call_args[1]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is not None

    def test_query_formats_prompt_correctly(self, rag_system, mock_ai_generator):
        """Test that query formats the prompt with the user question."""
        # Act
        rag_system.query("How do MCP servers work?")

        # Assert
        call_kwargs = mock_ai_generator.generate_response.call_args[1]
        assert "How do MCP servers work?" in call_kwargs["query"]

    def test_query_retrieves_sources_from_tool_manager(
        self, rag_system, mock_ai_generator
    ):
        """Test that sources are retrieved from tool manager after query."""
        # Arrange
        rag_system.tool_manager.get_last_sources = Mock(
            return_value=["[MCP Course - Lesson 1](https://example.com)"]
        )

        # Act
        response, sources = rag_system.query("What is MCP?")

        # Assert
        rag_system.tool_manager.get_last_sources.assert_called_once()
        assert len(sources) == 1
        assert "MCP Course" in sources[0]

    def test_query_resets_sources_after_retrieval(self, rag_system, mock_ai_generator):
        """Test that sources are reset after being retrieved."""
        # Arrange
        rag_system.tool_manager.reset_sources = Mock()

        # Act
        rag_system.query("What is MCP?")

        # Assert
        rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_with_session_retrieves_history(self, rag_system, mock_ai_generator):
        """Test that query retrieves conversation history for session."""
        # Arrange
        rag_system.session_manager.get_conversation_history.return_value = (
            "Previous conversation"
        )

        # Act
        rag_system.query("Follow up question", session_id="session-123")

        # Assert
        rag_system.session_manager.get_conversation_history.assert_called_with(
            "session-123"
        )
        call_kwargs = mock_ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "Previous conversation"

    def test_query_without_session_no_history(self, rag_system, mock_ai_generator):
        """Test that query without session_id has no history."""
        # Act
        rag_system.query("New question")

        # Assert
        call_kwargs = mock_ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None

    def test_query_updates_session_history(self, rag_system, mock_ai_generator):
        """Test that query adds exchange to session history."""
        # Arrange
        rag_system.session_manager.add_exchange = Mock()

        # Act
        rag_system.query("What is MCP?", session_id="session-456")

        # Assert
        rag_system.session_manager.add_exchange.assert_called_once()
        call_args = rag_system.session_manager.add_exchange.call_args[0]
        assert call_args[0] == "session-456"
        assert "What is MCP?" in call_args[1]
        assert call_args[2] == "This is the AI response about MCP."

    def test_query_does_not_update_history_without_session(
        self, rag_system, mock_ai_generator
    ):
        """Test that query without session_id doesn't update history."""
        # Arrange
        rag_system.session_manager.add_exchange = Mock()

        # Act
        rag_system.query("What is MCP?")

        # Assert
        rag_system.session_manager.add_exchange.assert_not_called()


class TestRAGSystemToolRegistration:
    """Test suite for RAGSystem tool registration."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 10
        return config

    @pytest.fixture
    def mock_ai_generator(self):
        """Create mock AI generator."""
        return Mock()

    def test_search_tool_is_registered(self, mock_config, mock_ai_generator):
        """Test that CourseSearchTool is registered."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.SessionManager"),
        ):

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai_generator)

            assert "search_course_content" in system.tool_manager.tools

    def test_outline_tool_is_registered(self, mock_config, mock_ai_generator):
        """Test that CourseOutlineTool is registered."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.SessionManager"),
        ):

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai_generator)

            assert "get_course_outline" in system.tool_manager.tools

    def test_tool_definitions_available(self, mock_config, mock_ai_generator):
        """Test that tool definitions are available for API calls."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.SessionManager"),
        ):

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai_generator)

            definitions = system.tool_manager.get_tool_definitions()

            assert len(definitions) == 2
            tool_names = [d["name"] for d in definitions]
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names


class TestRAGSystemIntegration:
    """Integration-style tests for RAG system query flow."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 10
        return config

    def test_end_to_end_query_flow(self, mock_config):
        """Test complete query flow from user question to response."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.SessionManager") as mock_sm,
        ):

            # Setup mocks
            mock_vector_store = Mock()
            mock_vector_store.max_results = 5
            mock_vs.return_value = mock_vector_store

            mock_session = Mock()
            mock_session.get_conversation_history.return_value = None
            mock_sm.return_value = mock_session

            # Create mock AI generator that simulates tool use
            mock_ai = Mock()
            mock_ai.generate_response.return_value = (
                "MCP servers provide external tool access for AI models."
            )

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai)

            # Execute query
            response, sources = system.query("What are MCP servers?")

            # Verify response
            assert "MCP" in response
            assert isinstance(sources, list)

            # Verify AI generator was called with correct structure
            call_kwargs = mock_ai.generate_response.call_args[1]
            assert "query" in call_kwargs
            assert "tools" in call_kwargs
            assert "tool_manager" in call_kwargs

    def test_query_with_empty_sources(self, mock_config):
        """Test query handling when no sources are found."""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vs,
            patch("rag_system.SessionManager") as mock_sm,
        ):

            mock_vs.return_value = Mock(max_results=5)
            mock_sm.return_value = Mock(
                get_conversation_history=Mock(return_value=None)
            )

            mock_ai = Mock()
            mock_ai.generate_response.return_value = (
                "I couldn't find specific information about that topic."
            )

            from rag_system import RAGSystem

            system = RAGSystem(mock_config, mock_ai)

            # Ensure tool manager returns empty sources
            system.tool_manager.get_last_sources = Mock(return_value=[])

            response, sources = system.query("Unknown topic")

            assert len(sources) == 0
            assert response is not None

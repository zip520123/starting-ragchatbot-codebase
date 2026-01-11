"""Shared fixtures for RAG system tests."""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import SearchResults


# =============================================================================
# API Testing Fixtures
# =============================================================================

@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API testing."""
    rag = Mock()
    rag.query.return_value = ("This is a test response about MCP.", ["[MCP Course - Lesson 1](https://example.com)"])
    rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["MCP Course", "Python Basics", "Advanced AI"]
    }

    # Mock session manager
    session_manager = Mock()
    session_manager.create_session.return_value = "test-session-abc123"
    rag.session_manager = session_manager

    return rag


@pytest.fixture
def mock_ai_generator_for_api():
    """Mock AIGenerator for API testing."""
    generator = Mock()
    generator.generate_response.return_value = "This is a test response."
    return generator


@pytest.fixture
def mock_config_for_api():
    """Mock config for API testing."""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.CHROMA_PATH = "./test_chroma"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 10
    return config


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked dependencies.

    This fixture creates a minimal FastAPI app that mirrors the real app's
    endpoints but uses mocked RAGSystem to avoid static file mounting issues.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test Course Materials RAG System")

    # Pydantic models (same as app.py)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Store mock in app state
    app.state.rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = app.state.rag_system.session_manager.create_session()

            answer, sources = app.state.rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = app.state.rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System", "status": "running"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test app."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


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

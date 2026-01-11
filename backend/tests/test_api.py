"""Tests for FastAPI endpoints."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestQueryEndpoint:
    """Test suite for POST /api/query endpoint."""

    def test_query_returns_200_with_valid_request(self, test_client):
        """Test successful query returns 200 status code."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200

    def test_query_returns_answer_in_response(self, test_client):
        """Test query response includes answer field."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_query_returns_sources_in_response(self, test_client):
        """Test query response includes sources field."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_query_returns_session_id(self, test_client):
        """Test query response includes session_id."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_query_creates_session_when_not_provided(self, test_client, test_app):
        """Test that a new session is created when session_id is not provided."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        data = response.json()
        # Should have created a session
        test_app.state.rag_system.session_manager.create_session.assert_called_once()
        assert data["session_id"] == "test-session-abc123"

    def test_query_uses_provided_session_id(self, test_client, test_app):
        """Test that provided session_id is used."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?", "session_id": "my-existing-session"}
        )

        data = response.json()
        assert data["session_id"] == "my-existing-session"
        # Should NOT have created a new session
        test_app.state.rag_system.session_manager.create_session.assert_not_called()

    def test_query_calls_rag_system_with_correct_args(self, test_client, test_app):
        """Test that RAG system query is called with correct arguments."""
        test_client.post(
            "/api/query",
            json={"query": "Tell me about MCP servers", "session_id": "session-xyz"}
        )

        test_app.state.rag_system.query.assert_called_once_with(
            "Tell me about MCP servers",
            "session-xyz"
        )

    def test_query_returns_422_for_missing_query(self, test_client):
        """Test that missing query field returns 422 validation error."""
        response = test_client.post(
            "/api/query",
            json={}
        )

        assert response.status_code == 422

    def test_query_returns_422_for_empty_body(self, test_client):
        """Test that empty request body returns 422."""
        response = test_client.post(
            "/api/query",
            content="",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_returns_500_on_rag_system_error(self, test_client, test_app):
        """Test that RAG system errors return 500 status code."""
        test_app.state.rag_system.query.side_effect = Exception("Database connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_query_response_structure(self, test_client):
        """Test the complete structure of query response."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        data = response.json()
        # Verify all required fields are present
        assert set(data.keys()) == {"answer", "sources", "session_id"}
        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)


class TestCoursesEndpoint:
    """Test suite for GET /api/courses endpoint."""

    def test_courses_returns_200(self, test_client):
        """Test courses endpoint returns 200 status code."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200

    def test_courses_returns_total_courses(self, test_client):
        """Test courses response includes total_courses field."""
        response = test_client.get("/api/courses")

        data = response.json()
        assert "total_courses" in data
        assert isinstance(data["total_courses"], int)

    def test_courses_returns_course_titles(self, test_client):
        """Test courses response includes course_titles field."""
        response = test_client.get("/api/courses")

        data = response.json()
        assert "course_titles" in data
        assert isinstance(data["course_titles"], list)

    def test_courses_returns_correct_data(self, test_client):
        """Test courses returns data from RAG system analytics."""
        response = test_client.get("/api/courses")

        data = response.json()
        assert data["total_courses"] == 3
        assert "MCP Course" in data["course_titles"]
        assert "Python Basics" in data["course_titles"]
        assert "Advanced AI" in data["course_titles"]

    def test_courses_calls_get_course_analytics(self, test_client, test_app):
        """Test that get_course_analytics is called."""
        test_client.get("/api/courses")

        test_app.state.rag_system.get_course_analytics.assert_called_once()

    def test_courses_returns_500_on_error(self, test_client, test_app):
        """Test that analytics errors return 500 status code."""
        test_app.state.rag_system.get_course_analytics.side_effect = Exception("ChromaDB error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "ChromaDB error" in response.json()["detail"]

    def test_courses_response_structure(self, test_client):
        """Test the complete structure of courses response."""
        response = test_client.get("/api/courses")

        data = response.json()
        # Verify all required fields are present
        assert set(data.keys()) == {"total_courses", "course_titles"}


class TestRootEndpoint:
    """Test suite for GET / endpoint."""

    def test_root_returns_200(self, test_client):
        """Test root endpoint returns 200 status code."""
        response = test_client.get("/")

        assert response.status_code == 200

    def test_root_returns_status_message(self, test_client):
        """Test root endpoint returns status information."""
        response = test_client.get("/")

        data = response.json()
        assert "status" in data
        assert data["status"] == "running"

    def test_root_returns_system_info(self, test_client):
        """Test root endpoint returns system information."""
        response = test_client.get("/")

        data = response.json()
        assert "message" in data
        assert "RAG System" in data["message"]


class TestAPIErrorHandling:
    """Test suite for API error handling."""

    def test_invalid_json_returns_422(self, test_client):
        """Test that invalid JSON returns 422 status code."""
        response = test_client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_wrong_content_type_handling(self, test_client):
        """Test handling of non-JSON content type."""
        response = test_client.post(
            "/api/query",
            content="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # FastAPI returns 422 for wrong content type
        assert response.status_code == 422

    def test_nonexistent_endpoint_returns_404(self, test_client):
        """Test that nonexistent endpoints return 404."""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed_returns_405(self, test_client):
        """Test that wrong HTTP method returns 405."""
        # GET is not allowed on /api/query
        response = test_client.get("/api/query")

        assert response.status_code == 405


class TestQueryWithDifferentInputs:
    """Test suite for query endpoint with various input scenarios."""

    def test_query_with_long_text(self, test_client):
        """Test query handles long input text."""
        long_query = "What is " + "MCP " * 100 + "servers?"

        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == 200

    def test_query_with_special_characters(self, test_client):
        """Test query handles special characters."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP? How does it work? (including examples)"}
        )

        assert response.status_code == 200

    def test_query_with_unicode(self, test_client):
        """Test query handles unicode characters."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP? 你好 مرحبا 🚀"}
        )

        assert response.status_code == 200

    def test_query_with_empty_string(self, test_client):
        """Test query with empty string."""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Empty query should still be processed (validation is application-specific)
        assert response.status_code == 200

    def test_query_with_whitespace_only(self, test_client):
        """Test query with whitespace-only string."""
        response = test_client.post(
            "/api/query",
            json={"query": "   "}
        )

        assert response.status_code == 200


class TestConcurrentSessions:
    """Test suite for session management in API."""

    def test_different_sessions_are_independent(self, test_client, test_app):
        """Test that different session IDs are handled independently."""
        # First query with session A
        test_client.post(
            "/api/query",
            json={"query": "First question", "session_id": "session-A"}
        )

        # Second query with session B
        test_client.post(
            "/api/query",
            json={"query": "Second question", "session_id": "session-B"}
        )

        # Verify both calls were made with correct session IDs
        calls = test_app.state.rag_system.query.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("First question", "session-A")
        assert calls[1][0] == ("Second question", "session-B")

    def test_same_session_maintains_context(self, test_client, test_app):
        """Test that same session ID is passed consistently."""
        session_id = "persistent-session"

        # Multiple queries with same session
        for i in range(3):
            test_client.post(
                "/api/query",
                json={"query": f"Question {i}", "session_id": session_id}
            )

        # All calls should have the same session ID
        calls = test_app.state.rag_system.query.call_args_list
        for call in calls:
            assert call[0][1] == session_id

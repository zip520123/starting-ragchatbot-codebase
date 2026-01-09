class MockAIGenerator:
    """Mock AIGenerator for testing without real API calls."""

    def __init__(self, mock_response="This is a mock response."):
        self.mock_response = mock_response
        self.last_query = None
        self.call_count = 0

    def generate_response(self, query, conversation_history=None, tools=None, tool_manager=None):
        """Return mock response and track call information."""
        self.last_query = query
        self.call_count += 1
        return self.mock_response

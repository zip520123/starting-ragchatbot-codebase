class MockAIGenerator:
    """Mock AIGenerator for testing without real API calls."""

    def __init__(self, mock_response="This is a mock response.", mock_sources=None):
        self.mock_response = mock_response
        self.mock_sources = mock_sources or []
        self.last_query = None
        self.call_count = 0

    def generate_response(self, query, conversation_history=None, tools=None, tool_manager=None):
        """Return mock response and track call information."""
        self.last_query = query
        self.call_count += 1

        # Set mock sources on the tool_manager's search tool
        if tool_manager and self.mock_sources:
            for tool in tool_manager.tools.values():
                if hasattr(tool, 'last_sources'):
                    tool.last_sources = self.mock_sources
                    break

        return self.mock_response

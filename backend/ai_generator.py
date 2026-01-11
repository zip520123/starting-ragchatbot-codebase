import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum number of sequential tool calling rounds per query
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content**: Search for specific content within course materials
2. **get_course_outline**: Get a course's complete structure including title, course link, and all lessons (number and title for each)

Tool Usage:
- Use **get_course_outline** for questions about course structure, what lessons are available, course overview, or "what's in this course"
- Use **search_course_content** for questions about specific content or detailed educational materials
- **Up to 2 sequential tool calls allowed per query**
- Use additional tool calls when first results are insufficient or you need information from different sources
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol for Outline Queries:
- When returning course outline information, include: course title, course link, and the complete lesson list
- For each lesson, include both the lesson number and lesson title
- Present the information in a clear, organized format

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def _execute_tools(self, response, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool_use blocks in a response.

        Args:
            response: The API response containing tool_use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dicts for the next API call

        Raises:
            Exception: If any tool execution fails
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name,
                    **content_block.input
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        return tool_results

    def _extract_text_response(self, response) -> str:
        """
        Extract text content from API response.

        Args:
            response: The API response

        Returns:
            Text from the first text block, or empty string if none found
        """
        for content_block in response.content:
            if content_block.type == "text":
                return content_block.text
        return ""

    def _handle_tool_error(self, response, error: Exception) -> str:
        """
        Handle tool execution errors gracefully.

        Args:
            response: The response that requested tool use
            error: The exception that occurred

        Returns:
            Any available text content or an error message
        """
        # Try to extract any text content from the response
        text_response = self._extract_text_response(response)
        if text_response:
            return text_response

        # Return a user-friendly error message
        return f"I encountered an issue while searching for information: {str(error)}"

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional multi-round tool usage.

        Supports up to MAX_TOOL_ROUNDS (2) sequential tool calls per query.
        Each round allows Claude to reason about previous tool results and
        optionally make another tool call.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages with user query
        messages = [{"role": "user", "content": query}]

        # Track current round
        current_round = 0

        # Main loop - continues until termination condition met
        while current_round < self.MAX_TOOL_ROUNDS:
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content
            }

            # Include tools if available (allows Claude to make tool calls)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Make API call
            response = self.client.messages.create(**api_params)

            # TERMINATION CONDITION (b): No tool_use in response
            if response.stop_reason != "tool_use":
                return self._extract_text_response(response)

            # TERMINATION CONDITION (c): No tool_manager to execute tools
            if not tool_manager:
                return self._extract_text_response(response)

            # Execute tools and update messages
            try:
                tool_results = self._execute_tools(response, tool_manager)
            except Exception as e:
                # TERMINATION CONDITION (c): Tool execution failed
                return self._handle_tool_error(response, e)

            # Accumulate messages for next round
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Increment round counter
            current_round += 1

        # TERMINATION CONDITION (a): Max rounds reached
        # Make final API call WITHOUT tools to force text response
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        final_response = self.client.messages.create(**final_params)
        return self._extract_text_response(final_response)
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import List, Dict, Any
import anthropic

from ai_generator import AIGenerator


class TestAIGenerator:
    """Test cases for AIGenerator class"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        client = Mock(spec=anthropic.Anthropic)
        return client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """AIGenerator instance with mocked client"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            return AIGenerator(
                api_key="test_key",
                model="claude-sonnet-4-20250514",
                base_url="https://api.anthropic.com"
            )

    @pytest.fixture
    def sample_tools(self):
        """Sample tool definitions"""
        return [
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

    @pytest.fixture
    def mock_tool_manager(self):
        """Mock tool manager"""
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
        return manager

    @pytest.fixture
    def mock_claude_response_no_tools(self):
        """Mock Claude response without tool usage"""
        response = Mock()
        response.stop_reason = "end_turn"
        response.content = [Mock(text="This is a direct response about machine learning.")]
        return response

    @pytest.fixture
    def mock_claude_response_with_tools(self):
        """Mock Claude response with tool usage"""
        response = Mock()
        response.stop_reason = "tool_use"

        # Create tool use block
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.input = {
            "query": "neural networks",
            "course_name": "Machine Learning",
            "lesson_number": 1
        }
        tool_use_block.id = "toolu_123"

        response.content = [tool_use_block]
        return response

    @pytest.fixture
    def mock_claude_final_response(self):
        """Mock Claude final response after tool execution"""
        response = Mock()
        response.stop_reason = "end_turn"
        response.content = [Mock(text="Based on the search results, neural networks are a key component of machine learning.")]
        return response

    def test_init(self):
        """Test AIGenerator initialization"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            generator = AIGenerator(
                api_key="test_key",
                model="claude-sonnet-4",
                base_url="https://api.anthropic.com"
            )

        mock_anthropic.assert_called_once_with(
            api_key="test_key",
            base_url="https://api.anthropic.com"
        )
        assert generator.model == "claude-sonnet-4"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    def test_generate_response_direct_answer(self, ai_generator, mock_anthropic_client, mock_claude_response_no_tools):
        """Test generating response without tool usage"""
        # Setup
        mock_anthropic_client.messages.create.return_value = mock_claude_response_no_tools

        # Execute
        response = ai_generator.generate_response("What is machine learning?")

        # Verify API call
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args[1]

        assert call_args["model"] == "claude-sonnet-4-20250514"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert call_args["messages"][0]["role"] == "user"
        assert "What is machine learning?" in call_args["messages"][0]["content"]
        assert "course materials" in call_args["system"].lower()

        # Verify response
        assert response == "This is a direct response about machine learning."

    def test_generate_response_with_conversation_history(self, ai_generator, mock_anthropic_client, mock_claude_response_no_tools):
        """Test generating response with conversation history"""
        # Setup
        mock_anthropic_client.messages.create.return_value = mock_claude_response_no_tools
        history = "User: What is AI?\nAssistant: AI is artificial intelligence..."

        # Execute
        response = ai_generator.generate_response(
            "What about neural networks?",
            conversation_history=history
        )

        # Verify API call includes history
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert history in call_args["system"]
        assert "Previous conversation" in call_args["system"]

    def test_generate_response_with_tools(self, ai_generator, mock_anthropic_client, mock_claude_response_with_tools, mock_tool_manager, mock_claude_final_response):
        """Test generating response with tool usage"""
        # Setup
        mock_anthropic_client.messages.create.side_effect = [
            mock_claude_response_with_tools,  # First call: requests tool usage
            mock_claude_final_response        # Second call: final response
        ]

        mock_tool_manager.execute_tool.return_value = "Found information about neural networks in ML course..."

        # Execute
        response = ai_generator.generate_response(
            "Tell me about neural networks",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify first API call (tool request)
        first_call = mock_anthropic_client.messages.create.call_args_list[0][1]
        assert "tools" in first_call
        assert first_call["tool_choice"]["type"] == "auto"

        # Verify tool execution
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="neural networks",
            course_name="Machine Learning",
            lesson_number=1
        )

        # Verify second API call (final response)
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        assert len(second_call["messages"]) == 3  # user + assistant(tool_use) + user(tool_result)

        # Verify tool result message structure
        tool_result_message = second_call["messages"][2]
        assert tool_result_message["role"] == "user"
        assert len(tool_result_message["content"]) == 1
        assert tool_result_message["content"][0]["type"] == "tool_result"
        assert tool_result_message["content"][0]["tool_use_id"] == "toolu_123"
        assert "Found information about neural networks" in tool_result_message["content"][0]["content"]

        # Verify final response
        assert "neural networks" in response.lower()

    def test_generate_response_tool_execution_error(self, ai_generator, mock_anthropic_client, mock_claude_response_with_tools, mock_tool_manager, mock_claude_final_response):
        """Test tool execution errors are handled properly"""
        # Setup
        mock_anthropic_client.messages.create.side_effect = [
            mock_claude_response_with_tools,
            mock_claude_final_response
        ]

        mock_tool_manager.execute_tool.return_value = "Error: Failed to connect to vector store"

        # Execute
        response = ai_generator.generate_response(
            "Search for something",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify tool error is passed to Claude
        call_args = mock_anthropic_client.messages.create.call_args_list[1][1]
        tool_result = call_args["messages"][2]["content"][0]["content"]
        assert "Error: Failed to connect to vector store" in tool_result

    def test_generate_response_multiple_tools(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test handling multiple tool calls in one response"""
        # Setup
        tool_use_block1 = Mock()
        tool_use_block1.type = "tool_use"
        tool_use_block1.name = "search_course_content"
        tool_use_block1.input = {"query": "python basics"}
        tool_use_block1.id = "toolu_456"

        tool_use_block2 = Mock()
        tool_use_block2.type = "tool_use"
        tool_use_block2.name = "search_course_content"
        tool_use_block2.input = {"query": "advanced python", "course_name": "Programming"}
        tool_use_block2.id = "toolu_789"

        tool_request_response = Mock()
        tool_request_response.stop_reason = "tool_use"
        tool_request_response.content = [tool_use_block1, tool_use_block2]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Here's information about Python basics and advanced topics.")]

        mock_anthropic_client.messages.create.side_effect = [
            tool_request_response,
            final_response
        ]

        mock_tool_manager.execute_tool.side_effect = [
            "Python basics content...",
            "Advanced Python content..."
        ]

        # Execute
        response = ai_generator.generate_response(
            "Tell me about Python",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="python basics")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="advanced python", course_name="Programming")

        # Verify both tool results were included in second call
        second_call = mock_anthropic_client.messages.create.call_args_list[1][1]
        tool_results = second_call["messages"][2]["content"]
        assert len(tool_results) == 2
        assert tool_results[0]["tool_use_id"] == "toolu_456"
        assert tool_results[1]["tool_use_id"] == "toolu_789"

    def test_generate_response_api_error(self, ai_generator, mock_anthropic_client):
        """Test handling of Claude API errors"""
        # Setup
        mock_anthropic_client.messages.create.side_effect = Exception("API connection failed")

        # Execute and verify exception is raised
        with pytest.raises(Exception, match="API connection failed"):
            ai_generator.generate_response("Test query")

    def test_system_prompt_structure(self, ai_generator, mock_anthropic_client, mock_claude_response_no_tools):
        """Test that system prompt is correctly structured"""
        # Setup
        mock_anthropic_client.messages.create.return_value = mock_claude_response_no_tools

        # Execute
        ai_generator.generate_response("Test query")

        # Verify system prompt structure
        call_args = mock_anthropic_client.messages.create.call_args[1]
        system_content = call_args["system"]

        # Check for key components
        assert "course materials" in system_content.lower()
        assert "search tool" in system_content.lower()
        assert "anthropic" in system_content.lower()
        assert "educational" in system_content.lower()
        assert "brief" in system_content.lower()
        assert "concise" in system_content.lower()

    def test_generate_response_with_history_and_tools(self, ai_generator, mock_anthropic_client, mock_claude_response_with_tools, mock_tool_manager, mock_claude_final_response):
        """Test generating response with both conversation history and tools"""
        # Setup
        mock_anthropic_client.messages.create.side_effect = [
            mock_claude_response_with_tools,
            mock_claude_final_response
        ]

        mock_tool_manager.execute_tool.return_value = "Tool result"

        history = "User: What is AI?\nAssistant: AI is artificial intelligence..."

        # Execute
        response = ai_generator.generate_response(
            "Now about ML",
            conversation_history=history,
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify both history and tools are included
        first_call = mock_anthropic_client.messages.create.call_args_list[0][1]
        system_content = first_call["system"]
        assert history in system_content
        assert "tools" in first_call

    def test_generate_response_no_tool_manager(self, ai_generator, mock_anthropic_client, mock_claude_response_with_tools):
        """Test response when tool_use is returned but no tool_manager is provided"""
        # Setup
        mock_anthropic_client.messages.create.return_value = mock_claude_response_with_tools

        # Execute
        response = ai_generator.generate_response(
            "Search query",
            tools=sample_tools,
            tool_manager=None
        )

        # Should return direct response without tool execution
        mock_anthropic_client.messages.create.assert_called_once()
        assert response is not None

    # Sequential Tool Calling Tests

    def test_sequential_tool_execution_two_rounds(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test typical 2-round sequential tool execution"""
        # Round 1: First tool call
        first_tool_response = Mock()
        first_tool_response.stop_reason = "tool_use"

        tool_use_block1 = Mock()
        tool_use_block1.type = "tool_use"
        tool_use_block1.name = "search_course_content"
        tool_use_block1.input = {"query": "machine learning"}
        tool_use_block1.id = "toolu_001"
        first_tool_response.content = [tool_use_block1]

        # Round 1: Tool result + continue request
        intermediate_response = Mock()
        intermediate_response.stop_reason = "end_turn"
        intermediate_response.content = [Mock(text="Found some machine learning content. Let me search for more specific information.")]

        # Round 2: Second tool call
        second_tool_response = Mock()
        second_tool_response.stop_reason = "tool_use"

        tool_use_block2 = Mock()
        tool_use_block2.type = "tool_use"
        tool_use_block2.name = "search_course_content"
        tool_use_block2.input = {"query": "neural networks", "course_name": "Machine Learning Course"}
        tool_use_block2.id = "toolu_002"
        second_tool_response.content = [tool_use_block2]

        # Final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Comprehensive information about machine learning and neural networks found in the courses.")]

        # Configure mock responses
        mock_anthropic_client.messages.create.side_effect = [
            first_tool_response,  # Initial request for tools
            intermediate_response,  # Response to first tool results
            second_tool_response,  # Request for second round of tools
            final_response  # Final answer
        ]

        mock_tool_manager.execute_tool.side_effect = [
            "Found basic machine learning content...",
            "Found detailed neural networks information..."
        ]

        # Execute
        response = ai_generator.generate_response(
            "Tell me about machine learning and neural networks",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify 4 API calls were made (2 tool requests + 2 responses)
        assert mock_anthropic_client.messages.create.call_count == 4

        # Verify tool execution sequence
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="machine learning")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="neural networks", course_name="Machine Learning Course")

        # Verify final response
        assert "comprehensive information" in response.lower()

    def test_sequential_tool_execution_early_termination(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test that Claude can stop after 1 round when satisfied"""
        # Setup: One tool call followed by final response (no second tool request)
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.input = {"query": "python basics"}
        tool_use_block.id = "toolu_early"
        tool_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="I found all the Python basics information you need.")]

        mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]
        mock_tool_manager.execute_tool.return_value = "Comprehensive Python basics content found..."

        # Execute
        response = ai_generator.generate_response(
            "Tell me about Python basics",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Verify only 2 API calls (1 tool request + 1 final response)
        assert mock_anthropic_client.messages.create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1
        assert "python basics information" in response.lower()

    def test_sequential_tool_execution_max_rounds_enforcement(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test that system stops at 2 rounds even if Claude wants more"""
        # Mock Claude wanting to make more than 2 tool calls
        tool_responses = []
        tool_use_blocks = []

        for i in range(3):  # 3 tool requests (should be limited to 2)
            response = Mock()
            response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.input = {"query": f"query_round_{i+1}"}
            tool_block.id = f"toolu_{i:03d}"
            response.content = [tool_block]

            tool_responses.append(response)
            tool_use_blocks.append(tool_block)

        # Intermediate responses for each round
        intermediate_responses = [Mock(stop_reason="end_turn", content=[Mock(text=f"Intermediate result {i}")]) for i in range(3)]

        # Final response after hitting max rounds
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Final answer after max rounds")]

        # Flatten the response sequence: tool1 + result1 + tool2 + result2 + tool3 + result3 + final
        mock_sequence = []
        for i in range(3):
            mock_sequence.extend([tool_responses[i], intermediate_responses[i]])
        mock_sequence.append(final_response)

        mock_anthropic_client.messages.create.side_effect = mock_sequence
        mock_tool_manager.execute_tool.side_effect = [f"Result {i}" for i in range(3)]

        # Execute
        response = ai_generator.generate_response(
            "Complex multi-round query",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Should have made at least 5 calls but not all 7 (should stop at max rounds)
        assert mock_anthropic_client.messages.create.call_count >= 5

        # Should not execute more than 2 tools
        assert mock_tool_manager.execute_tool.call_count <= 2

    def test_sequential_tool_execution_error_handling(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test graceful error handling during sequential execution"""
        # First tool call succeeds
        first_tool_response = Mock()
        first_tool_response.stop_reason = "tool_use"

        tool_use_block1 = Mock()
        tool_use_block1.type = "tool_use"
        tool_use_block1.name = "search_course_content"
        tool_use_block1.input = {"query": "database design"}
        tool_use_block1.id = "toolu_error_1"
        first_tool_response.content = [tool_use_block1]

        # Second tool call fails with API error
        mock_anthropic_client.messages.create.side_effect = [
            first_tool_response,  # Request first tool
            Exception("API connection failed")  # API error on follow-up
        ]

        mock_tool_manager.execute_tool.return_value = "Found database design content..."

        # Execute
        response = ai_generator.generate_response(
            "Tell me about database design",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Should handle error gracefully and provide partial results
        assert "error" in response.lower() or "database design" in response.lower()
        assert mock_tool_manager.execute_tool.call_count == 1

    def test_sequential_tool_execution_conversation_safety(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test conversation length safety check"""
        # Test with very long conversation context
        long_tool_result = "Result: " + "x" * 10000  # Very long result

        tool_response = Mock()
        tool_response.stop_reason = "tool_use"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.input = {"query": "test query"}
        tool_use_block.id = "toolu_safety"
        tool_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Final response after safety check")]

        mock_anthropic_client.messages.create.side_effect = [tool_response, final_response]
        mock_tool_manager.execute_tool.return_value = long_tool_result

        # Execute
        response = ai_generator.generate_response(
            "Test query",
            tools=sample_tools,
            tool_manager=mock_tool_manager
        )

        # Should complete execution without errors
        assert response is not None
        assert mock_anthropic_client.messages.create.call_count >= 2

    def test_enhanced_tool_manager_sequential_tracking(self):
        """Test enhanced ToolManager sequential source tracking"""
        from search_tools import ToolManager, CourseSearchTool
        from vector_store import VectorStore

        # Create mock vector store and tools
        mock_vector_store = Mock()
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)

        # Register the tool
        tool_manager.register_tool(search_tool)

        # Mock the search results with sources
        mock_results = Mock()
        mock_results.error = None
        mock_results.is_empty.return_value = False
        mock_results.documents = ["Content about databases"]
        mock_results.metadata = [{"course_title": "Database Course", "lesson_number": 1}]

        mock_vector_store.search.return_value = mock_results

        # Execute multiple searches
        tool_manager.execute_tool("search_course_content", query="databases")
        tool_manager.execute_tool("search_course_content", query="SQL", course_name="Database Course")

        # Verify sequential tracking
        all_sources = tool_manager.get_all_sources()
        assert len(all_sources) >= 1  # Should have sources from multiple calls
        assert "Database Course" in str(all_sources)

        call_history = tool_manager.get_call_history()
        assert len(call_history) == 2
        assert call_history[0]['tool'] == "search_course_content"
        assert call_history[0]['params']['query'] == "databases"
        assert call_history[1]['params']['query'] == "SQL"

        # Test sequential summary
        summary = tool_manager.get_sequential_summary()
        assert "Executed 2 tool call(s)" in summary
        assert "databases" in summary
        assert "SQL" in summary

# Sample tools fixture for testing
sample_tools = [
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
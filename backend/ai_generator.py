import anthropic
from typing import List, Optional, Dict, Any
import time

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool for questions about specific course content or detailed educational materials
- You may make up to 2 sequential searches to build comprehensive answers
- Start with broad searches, then refine based on results for more targeted information
- Examples of multi-round workflows:
  * Search for course outline → Search specific lesson content within that course
  * Search for general topic → Search for advanced coverage in different courses
  * Search for course content → Search for related topics or prerequisites
- Synthesize search results into accurate, fact-based responses
- If searches yield no results, state this clearly

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"

All responses must be:
1. **Educational** - Maintain instructional value and comprehensive coverage
2. **Clear** - Use accessible language
3. **Example-supported** - Include relevant examples when they aid understanding
4. **Well-structured** - Organize information from multiple searches coherently
Provide complete answers that utilize all relevant search results.
"""
    
    def __init__(self, api_key: str, model: str, base_url: str = "https://open.bigmodel.cn/api/anthropic"):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
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
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle sequential execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        return self._handle_sequential_tool_execution(
            initial_response, base_params, tool_manager, max_rounds=2
        )

    def _handle_sequential_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, max_rounds: int = 2):
        """
        Handle sequential tool execution with configurable maximum rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool execution rounds

        Returns:
            Final response text after sequential tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's initial tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        current_response = initial_response
        round_count = 0

        # Execute tools sequentially, allowing Claude to refine searches
        while current_response.stop_reason == "tool_use" and round_count < max_rounds:
            # Safety check: don't exceed conversation length limits
            if self._check_conversation_length_safety(messages):
                break

            # Execute all tool calls in current response
            tool_results = []
            execution_success = True

            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result
                        })
                    except Exception as e:
                        # Handle individual tool execution errors gracefully
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error executing tool: {str(e)}"
                        })
                        execution_success = False

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # If tool execution failed and we have results from previous rounds,
            # try to answer with what we have
            if not execution_success and round_count > 0:
                break

            # Get next response from Claude (without tools this time to avoid infinite loops)
            followup_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": None  # Remove tools to force Claude to respond with final answer
            }

            try:
                next_response = self.client.messages.create(**followup_params)
                round_count += 1

                # Check if Claude wants to make another tool call
                if next_response.stop_reason == "tool_use" and round_count < max_rounds:
                    # Continue with another round of tool execution
                    # Re-add tools for this round only
                    followup_params["tools"] = base_params.get("tools", [])
                    followup_params["tool_choice"] = {"type": "auto"}
                    next_response = self.client.messages.create(**followup_params)

                    if next_response.stop_reason == "tool_use":
                        # Add Claude's new tool use request and continue the loop
                        messages.append({"role": "assistant", "content": next_response.content})
                        current_response = next_response
                        continue

                # Claude provided final response (no more tool calls)
                return next_response.content[0].text

            except Exception as e:
                # Handle API errors gracefully
                if round_count == 0:
                    # No successful tool executions, return error message
                    return f"I encountered an error while searching: {str(e)}. Please try rephrasing your question."
                else:
                    # We have some results, try to provide partial answer
                    return f"I encountered an error during my search, but here's what I found: {self._summarize_available_results(messages)}"

        # If we exit the loop without a final response, create one
        if round_count >= max_rounds:
            # Hit max rounds, force Claude to respond with what we have
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            try:
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text
            except Exception as e:
                return f"Reached maximum search rounds. Based on my searches: {self._summarize_available_results(messages)}"

        # Default fallback
        return "I completed my searches but was unable to generate a final response."

    def _check_conversation_length_safety(self, messages: List[Dict[str, Any]], max_chars: int = 15000) -> bool:
        """
        Check if conversation is getting too long to avoid token limits.

        Args:
            messages: Current message history
            max_chars: Maximum character limit before truncation

        Returns:
            True if conversation is too long, False otherwise
        """
        total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
        return total_chars > max_chars

    def _summarize_available_results(self, messages: List[Dict[str, Any]]) -> str:
        """
        Extract and summarize search results from message history.

        Args:
            messages: Current message history

        Returns:
            Summary of available search results
        """
        results = []
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                for content in msg["content"]:
                    if content.get("type") == "tool_result" and not content.get("content", "").startswith("Error"):
                        results.append(content["content"])

        if results:
            return " ".join(results[:3])  # Return first 3 results to avoid length issues
        return "No search results were successfully retrieved."
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
import time
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.
        
        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter
            
        Returns:
            Formatted search results or error message
        """
        
        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )
        
        # Handle errors
        if results.error:
            return results.error
        
        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."
        
        # Format and return results
        return self._format_results(results)
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')
            lesson_link = meta.get('lesson_link')

            # Build context header with clickable lesson link if available
            header = f"[{course_title}"
            if lesson_num is not None:
                if lesson_link:
                    # Create clickable lesson link
                    lesson_html = f'<a href="{lesson_link}" target="_blank" class="lesson-link">Lesson {lesson_num}</a>'
                    header += f" - {lesson_html}"
                else:
                    header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI (plain text version)
            source = course_title
            if lesson_num is not None:
                source += f" - Lesson {lesson_num}"
            sources.append(source)

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)

class ToolManager:
    """Manages available tools for the AI with enhanced source tracking for sequential calls"""

    def __init__(self):
        self.tools = {}
        self.all_sources = []  # Track all sources across sequential calls
        self.call_history = []  # Track all tool executions in sequence

    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"

        # Record the tool call for sequential tracking
        call_record = {
            'tool': tool_name,
            'params': kwargs,
            'timestamp': time.time()
        }
        self.call_history.append(call_record)

        # Execute the tool
        result = self.tools[tool_name].execute(**kwargs)

        # Collect sources from this execution
        tool_sources = self.tools[tool_name].last_sources if hasattr(self.tools[tool_name], 'last_sources') else []

        # Add to all_sources with deduplication
        for source in tool_sources:
            if source not in self.all_sources:
                self.all_sources.append(source)

        return result

    def get_last_sources(self) -> list:
        """Get sources from the most recent search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def get_all_sources(self) -> list:
        """Get all sources from sequential tool executions"""
        return self.all_sources.copy()

    def get_call_history(self) -> list:
        """Get the history of all tool executions in sequence"""
        return self.call_history.copy()

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []

        # Also reset sequential tracking
        self.all_sources.clear()
        self.call_history.clear()

    def get_sequential_summary(self) -> str:
        """Get a summary of sequential tool execution for context"""
        if not self.call_history:
            return ""

        summary_parts = []
        summary_parts.append(f"Executed {len(self.call_history)} tool call(s):")

        for i, call in enumerate(self.call_history, 1):
            tool_name = call['tool']
            params = call['params']

            call_desc = f"{i}. {tool_name}"
            if 'query' in params:
                call_desc += f" - '{params['query']}'"
            if 'course_name' in params:
                call_desc += f" (course: {params['course_name']})"
            if 'lesson_number' in params:
                call_desc += f" (lesson: {params['lesson_number']})"

            summary_parts.append(call_desc)

        summary_parts.append(f"Sources from {len(self.all_sources)} locations")

        return "\n".join(summary_parts)
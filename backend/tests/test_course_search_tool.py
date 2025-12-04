import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from search_tools import CourseSearchTool, SearchResults


class TestCourseSearchTool:
    """Test cases for CourseSearchTool.execute method"""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store for testing"""
        store = Mock()
        return store

    @pytest.fixture
    def course_search_tool(self, mock_vector_store):
        """CourseSearchTool instance with mocked dependencies"""
        return CourseSearchTool(mock_vector_store)

    @pytest.fixture
    def sample_search_results(self):
        """Sample successful search results"""
        return SearchResults(
            documents=[
                "Machine learning is a subset of artificial intelligence that focuses on neural networks.",
                "Deep learning uses multi-layered neural networks to process complex patterns."
            ],
            metadata=[
                {
                    "course_title": "Introduction to Machine Learning",
                    "lesson_number": 1,
                    "lesson_link": "https://example.com/lesson1"
                },
                {
                    "course_title": "Advanced Neural Networks",
                    "lesson_number": 3,
                    "lesson_link": "https://example.com/lesson3"
                }
            ],
            distances=[0.1, 0.2]
        )

    def test_execute_success_basic_search(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test successful basic search without filters"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = course_search_tool.execute("neural networks")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="neural networks",
            course_name=None,
            lesson_number=None
        )

        assert "Introduction to Machine Learning" in result
        assert "Advanced Neural Networks" in result
        assert "neural networks" in result.lower()
        assert "Lesson 1" in result
        assert "Lesson 3" in result

    def test_execute_success_with_course_filter(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test successful search with course name filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = course_search_tool.execute("deep learning", course_name="Machine Learning")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="deep learning",
            course_name="Machine Learning",
            lesson_number=None
        )
        assert "Machine Learning" in result

    def test_execute_success_with_lesson_filter(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test successful search with lesson number filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = course_search_tool.execute("algorithms", lesson_number=2)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="algorithms",
            course_name=None,
            lesson_number=2
        )
        assert "Lesson 2" in result

    def test_execute_success_with_both_filters(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test successful search with both course and lesson filters"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = course_search_tool.execute("neural networks", course_name="ML Course", lesson_number=1)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="neural networks",
            course_name="ML Course",
            lesson_number=1
        )

    def test_execute_empty_results(self, course_search_tool, mock_vector_store):
        """Test handling of empty search results"""
        # Setup
        empty_results = SearchResults.empty("No results found")
        mock_vector_store.search.return_value = empty_results

        # Execute
        result = course_search_tool.execute("nonexistent topic")

        # Verify
        assert result == "No results found"

    def test_execute_no_matching_course_filter(self, course_search_tool, mock_vector_store):
        """Test when no course matches the filter"""
        # Setup
        error_results = SearchResults.empty("No course found matching 'Nonexistent Course'")
        mock_vector_store.search.return_value = error_results

        # Execute
        result = course_search_tool.execute("python", course_name="Nonexistent Course")

        # Verify
        assert "No course found matching 'Nonexistent Course'" in result

    def test_execute_no_matching_lesson_filter(self, course_search_tool, mock_vector_store):
        """Test when no lesson matches the filter"""
        # Setup
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        # Execute
        result = course_search_tool.execute("python", lesson_number=99)

        # Verify
        assert "No relevant content found in lesson 99" in result

    def test_execute_search_error(self, course_search_tool, mock_vector_store):
        """Test handling of search errors"""
        # Setup
        error_results = SearchResults.empty("Search error: Connection failed")
        mock_vector_store.search.return_value = error_results

        # Execute
        result = course_search_tool.execute("test query")

        # Verify
        assert "Search error: Connection failed" in result

    def test_execute_vector_store_exception(self, course_search_tool, mock_vector_store):
        """Test handling when vector store raises an exception"""
        # Setup
        mock_vector_store.search.side_effect = Exception("Vector store crashed")

        # Execute
        result = course_search_tool.execute("test query")

        # Verify
        assert "Search error: Vector store crashed" in result

    def test_format_results_with_lesson_links(self, course_search_tool):
        """Test result formatting when lesson links are available"""
        # Setup
        results = SearchResults(
            documents=["Content about neural networks"],
            metadata=[{
                "course_title": "ML Course",
                "lesson_number": 1,
                "lesson_link": "https://example.com/ml-lesson1"
            }],
            distances=[0.1]
        )

        # Execute
        result = course_search_tool._format_results(results)

        # Verify
        assert '<a href="https://example.com/ml-lesson1" target="_blank" class="lesson-link">Lesson 1</a>' in result
        assert "Content about neural networks" in result

    def test_format_results_without_lesson_links(self, course_search_tool):
        """Test result formatting when lesson links are not available"""
        # Setup
        results = SearchResults(
            documents=["Content about algorithms"],
            metadata=[{
                "course_title": "CS Course",
                "lesson_number": 2,
                "lesson_link": None
            }],
            distances=[0.1]
        )

        # Execute
        result = course_search_tool._format_results(results)

        # Verify
        assert "CS Course - Lesson 2" in result
        assert "Content about algorithms" in result
        assert 'target="_blank"' not in result

    def test_format_results_without_lesson_number(self, course_search_tool):
        """Test result formatting when lesson number is not available"""
        # Setup
        results = SearchResults(
            documents=["General course content"],
            metadata=[{
                "course_title": "Intro Course",
                "lesson_number": None,
                "lesson_link": None
            }],
            distances=[0.1]
        )

        # Execute
        result = course_search_tool._format_results(results)

        # Verify
        assert "[Intro Course]" in result
        assert "General course content" in result
        assert "Lesson" not in result

    def test_source_tracking(self, course_search_tool, mock_vector_store, sample_search_results):
        """Test that sources are properly tracked for UI"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        course_search_tool.execute("test query")

        # Verify sources are tracked
        sources = course_search_tool.last_sources
        assert len(sources) == 2
        assert "Introduction to Machine Learning - Lesson 1" in sources
        assert "Advanced Neural Networks - Lesson 3" in sources

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is properly structured"""
        # Execute
        tool_def = course_search_tool.get_tool_definition()

        # Verify
        assert tool_def["name"] == "search_course_content"
        assert "course materials" in tool_def["description"].lower()
        assert "query" in tool_def["input_schema"]["properties"]
        assert "course_name" in tool_def["input_schema"]["properties"]
        assert "lesson_number" in tool_def["input_schema"]["properties"]
        assert "query" in tool_def["input_schema"]["required"]
        assert tool_def["input_schema"]["required"] == ["query"]
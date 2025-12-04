"""Integration tests for the RAG system to identify why content-related queries return 'query failed'"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock

# We need to test the actual integration between components
from rag_system import RAGSystem
from config import Config


class TestRAGSystemIntegration:
    """Integration tests to identify failure points in the RAG system"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.CHROMA_PATH = tempfile.mkdtemp()  # Create temp directory for tests
        config.ANTHROPIC_API_KEY = "test_key"
        config.ANTHROPIC_MODEL = "claude-sonnet-4"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 2
        return config

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all the external dependencies"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor') as mock_dp, \
             patch('rag_system.SessionManager') as mock_sm:

            # Configure mocks
            mock_vs.return_value = Mock()
            mock_ai.return_value = Mock()
            mock_dp.return_value = Mock()
            mock_sm.return_value = Mock()

            yield {
                'VectorStore': mock_vs,
                'AIGenerator': mock_ai,
                'DocumentProcessor': mock_dp,
                'SessionManager': mock_sm
            }

    def test_rag_system_initialization(self, mock_config, mock_dependencies):
        """Test RAG system initialization with mocked dependencies"""
        # This should not raise an exception
        rag_system = RAGSystem(mock_config)

        # Verify components are initialized
        assert rag_system.config == mock_config
        mock_dependencies['VectorStore'].assert_called_once()
        mock_dependencies['AIGenerator'].assert_called_once()
        mock_dependencies['DocumentProcessor'].assert_called_once()
        mock_dependencies['SessionManager'].assert_called_once()

    def test_vector_store_initialization_failure(self, mock_config, mock_dependencies):
        """Test what happens when VectorStore fails to initialize"""
        # Make VectorStore raise an exception
        mock_dependencies['VectorStore'].side_effect = Exception("ChromaDB connection failed")

        # The system should handle this gracefully
        with pytest.raises(Exception, match="ChromaDB connection failed"):
            RAGSystem(mock_config)

    def test_ai_generator_initialization_failure(self, mock_config, mock_dependencies):
        """Test what happens when AIGenerator fails to initialize"""
        # Make AIGenerator raise an exception
        mock_dependencies['AIGenerator'].side_effect = Exception("Invalid API key")

        # The system should handle this gracefully
        with pytest.raises(Exception, match="Invalid API key"):
            RAGSystem(mock_config)

    def test_query_processing_with_mocked_components(self, mock_config, mock_dependencies):
        """Test query processing when components are mocked"""
        rag_system = RAGSystem(mock_config)

        # Mock the query response
        expected_response = "Test response"
        mock_dependencies['AIGenerator'].return_value.generate_response.return_value = expected_response

        # Execute a query
        result = rag_system.query("test query")

        # Verify the query was processed
        assert result == expected_response
        mock_dependencies['AIGenerator'].return_value.generate_response.assert_called_once_with(
            "test query",
            conversation_history=None,
            tools=mock_dependencies['AIGenerator'].return_value.get_tool_definitions.return_value,
            tool_manager=rag_system.tool_manager
        )

    def test_query_processing_with_conversation_history(self, mock_config, mock_dependencies):
        """Test query processing with conversation history"""
        rag_system = RAGSystem(mock_config)

        # Mock the query response
        expected_response = "Test response with history"
        mock_dependencies['AIGenerator'].return_value.generate_response.return_value = expected_response

        # Create mock conversation history
        history = "Previous conversation content"

        # Execute a query with history
        result = rag_system.query("test query", session_id="test_session")

        # Verify the query was processed with history
        assert result == expected_response

        # Verify session manager was called
        mock_dependencies['SessionManager'].return_value.get_conversation_history.assert_called_once_with("test_session")

    def test_query_processing_failure(self, mock_config, mock_dependencies):
        """Test what happens when query processing fails"""
        rag_system = RAGSystem(mock_config)

        # Make the AI generator raise an exception
        mock_dependencies['AIGenerator'].return_value.generate_response.side_effect = Exception("AI processing failed")

        # The system should handle this gracefully
        with pytest.raises(Exception, match="AI processing failed"):
            rag_system.query("test query")

    def test_course_statistics(self, mock_config, mock_dependencies):
        """Test getting course statistics"""
        rag_system = RAGSystem(mock_config)

        # Mock statistics
        expected_stats = {
            "total_courses": 10,
            "course_titles": ["Course 1", "Course 2"]
        }
        mock_dependencies['VectorStore'].return_value.get_course_analytics.return_value = expected_stats

        # Get statistics
        stats = rag_system.get_course_statistics()

        # Verify statistics
        assert stats == expected_stats
        mock_dependencies['VectorStore'].return_value.get_course_analytics.assert_called_once()

    def test_document_processing_workflow(self, mock_config, mock_dependencies):
        """Test the document processing workflow"""
        rag_system = RAGSystem(mock_config)

        # Mock course data
        courses = ["Course 1 content", "Course 2 content"]
        course_chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]

        mock_dependencies['DocumentProcessor'].return_value.process_course_folder.return_value = (courses, course_chunks)
        mock_dependencies['VectorStore'].return_value.add_course_content.return_value = None

        # Process documents
        result = rag_system.process_documents("/mock/path")

        # Verify document processing
        assert result == (courses, course_chunks)
        mock_dependencies['DocumentProcessor'].return_value.process_course_folder.assert_called_once_with("/mock/path")
        mock_dependencies['VectorStore'].return_value.add_course_content.assert_called_once_with(courses, course_chunks)

    def test_document_processing_failure(self, mock_config, mock_dependencies):
        """Test what happens when document processing fails"""
        rag_system = RAGSystem(mock_config)

        # Make document processor raise an exception
        mock_dependencies['DocumentProcessor'].return_value.process_course_folder.side_effect = Exception("Document processing failed")

        # The system should handle this gracefully
        with pytest.raises(Exception, match="Document processing failed"):
            rag_system.process_documents("/mock/path")


class TestRealWorldScenarios:
    """Test scenarios that might cause 'query failed' responses"""

    def test_missing_environment_variables(self):
        """Test what happens when required environment variables are missing"""
        # Create config without API key
        config = Mock(spec=Config)
        config.ANTHROPIC_API_KEY = None  # Missing API key
        config.CHROMA_PATH = tempfile.mkdtemp()

        with patch('rag_system.VectorStore') as mock_vs:
            # This should fail due to missing API key
            with pytest.raises(Exception):
                RAGSystem(config)

    def test_invalid_chroma_path(self):
        """Test what happens when ChromaDB path is invalid"""
        # Create config with invalid path
        config = Mock(spec=Config)
        config.ANTHROPIC_API_KEY = "test_key"
        config.CHROMA_PATH = "/invalid/path/that/does/not/exist"

        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator'):

            # Make VectorStore fail due to invalid path
            mock_vs.side_effect = Exception("Invalid ChromaDB path")

            # This should fail due to invalid path
            with pytest.raises(Exception, match="Invalid ChromaDB path"):
                RAGSystem(config)

    def test_empty_vector_store(self):
        """Test what happens when vector store is empty"""
        # Create config
        config = Mock(spec=Config)
        config.ANTHROPIC_API_KEY = "test_key"
        config.CHROMA_PATH = tempfile.mkdtemp()

        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor') as mock_dp, \
             patch('rag_system.SessionManager') as mock_sm:

            # Create RAG system
            rag_system = RAGSystem(config)

            # Mock empty vector store
            mock_vs.return_value.search.return_value = ([], [])  # No results

            # Mock AI response
            mock_ai.return_value.generate_response.return_value = "No relevant content found"

            # Execute query
            result = rag_system.query("test query")

            # Should handle empty results gracefully
            assert result == "No relevant content found"

    def test_embedding_model_failure(self):
        """Test what happens when embedding model fails"""
        config = Mock(spec=Config)
        config.ANTHROPIC_API_KEY = "test_key"
        config.CHROMA_PATH = tempfile.mkdtemp()
        config.EMBEDDING_MODEL = "invalid_model"

        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.DocumentProcessor') as mock_dp, \
             patch('rag_system.SessionManager') as mock_sm:

            # Make VectorStore fail due to invalid embedding model
            mock_vs.side_effect = Exception("Invalid embedding model")

            # This should fail due to invalid embedding model
            with pytest.raises(Exception, match="Invalid embedding model"):
                RAGSystem(config)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
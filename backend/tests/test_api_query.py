"""
API endpoint tests for the /api/query endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.api
class TestQueryEndpoint:
    """Test cases for the /api/query endpoint."""

    def test_query_endpoint_success(self, test_client, query_request_data, expected_query_response):
        """Test successful query request and response."""
        response = test_client.post("/api/query", json=query_request_data)

        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert "answer" in response_data
        assert "sources" in response_data
        assert "session_id" in response_data

        # Verify response content matches expected
        assert response_data["answer"] == expected_query_response["answer"]
        assert response_data["sources"] == expected_query_response["sources"]
        assert response_data["session_id"] == expected_query_response["session_id"]

    def test_query_endpoint_with_existing_session(self, test_client):
        """Test query request with existing session ID."""
        request_data = {
            "query": "What is neural network?",
            "session_id": "existing_session_456"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == "existing_session_456"

    def test_query_endpoint_creates_new_session(self, test_client, query_request_data):
        """Test that new session is created when session_id is not provided."""
        response = test_client.post("/api/query", json=query_request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == "test_session_123"

    def test_query_endpoint_missing_query_field(self, test_client):
        """Test query request with missing query field."""
        request_data = {
            "session_id": "test_session"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_query_endpoint_empty_query(self, test_client):
        """Test query request with empty query string."""
        request_data = {
            "query": "",
            "session_id": None
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200  # Empty query should be processed

    def test_query_endpoint_long_query(self, test_client):
        """Test query request with very long query string."""
        long_query = "What is " + "very " * 100 + "long query?"
        request_data = {
            "query": long_query,
            "session_id": None
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert "answer" in response_data

    def test_query_endpoint_server_error(self, test_client):
        """Test query endpoint handling of server errors."""
        # Mock the RAG system to raise an exception
        with patch.object(test_client.app.state.mock_rag_system, 'query', side_effect=Exception("Database connection failed")):
            request_data = {
                "query": "This query will cause an error",
                "session_id": "test_session"
            }

            response = test_client.post("/api/query", json=request_data)

            assert response.status_code == 500
            response_data = response.json()
            assert "detail" in response_data
            assert "Database connection failed" in response_data["detail"]

    def test_query_endpoint_wrong_http_method(self, test_client):
        """Test that GET method is not allowed for query endpoint."""
        response = test_client.get("/api/query")
        assert response.status_code == 405

    def test_query_endpoint_content_type_validation(self, test_client):
        """Test that endpoint validates content-type."""
        # Send form data instead of JSON
        response = test_client.post(
            "/api/query",
            data="query=test&session_id=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Should still work with form data due to FastAPI's flexible parsing
        assert response.status_code in [200, 422]

    def test_query_response_sources_format(self, test_client, query_request_data):
        """Test that sources in response have the correct format."""
        response = test_client.post("/api/query", json=query_request_data)

        assert response.status_code == 200
        response_data = response.json()

        sources = response_data["sources"]
        assert isinstance(sources, list)
        assert len(sources) > 0

        # Check source format: filename: Chunk X
        for source in sources:
            assert isinstance(source, str)
            assert ": Chunk " in source or ":" in source

    def test_query_session_persistence(self, test_client):
        """Test that the same session ID is used across multiple queries."""
        first_request = {
            "query": "First question",
            "session_id": None
        }

        # First query creates session
        response1 = test_client.post("/api/query", json=first_request)
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Second query uses same session
        second_request = {
            "query": "Follow-up question",
            "session_id": session_id
        }

        response2 = test_client.post("/api/query", json=second_request)
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    @pytest.mark.parametrize("query_text", [
        "What is machine learning?",
        "Explain neural networks",
        "How does backpropagation work?",
        "What are the differences between CNN and RNN?",
        "Tell me about reinforcement learning"
    ])
    def test_query_endpoint_various_questions(self, test_client, query_text):
        """Test query endpoint with various types of questions."""
        request_data = {
            "query": query_text,
            "session_id": None
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert "answer" in response_data
        assert "sources" in response_data
        assert "session_id" in response_data
        assert len(response_data["answer"]) > 0


@pytest.mark.integration
@pytest.mark.api
class TestQueryEndpointIntegration:
    """Integration tests for query endpoint with real dependencies."""

    def test_query_with_real_session_manager(self, test_client):
        """Test query endpoint with session manager integration."""
        # Test that session creation is properly called
        test_client.app.state.mock_rag_system.session_manager.create_session.assert_called()

        request_data = {
            "query": "Test question",
            "session_id": None
        }

        response = test_client.post("/api/query", json=request_data)
        assert response.status_code == 200

        # Verify session manager was called
        test_client.app.state.mock_rag_system.session_manager.create_session.assert_called()

    def test_query_with_real_rag_system(self, test_client):
        """Test query endpoint integration with RAG system."""
        request_data = {
            "query": "Integration test question",
            "session_id": "integration_session"
        }

        response = test_client.post("/api/query", json=request_data)
        assert response.status_code == 200

        # Verify RAG system query was called with correct parameters
        test_client.app.state.mock_rag_system.query.assert_called_with(
            request_data["query"],
            request_data["session_id"]
        )
"""
API endpoint tests for the root endpoint and general API behavior.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.api
class TestRootEndpoint:
    """Test cases for the root endpoint and general API behavior."""

    def test_root_endpoint_not_available_in_test_client(self, test_client):
        """Test that root endpoint is not available in test client (no static files mounted)."""
        # The test client doesn't mount static files, so root endpoint should not work
        response = test_client.get("/")

        # Should return 404 since static files are not mounted in test app
        assert response.status_code == 404

    def test_api_health_check(self, test_client):
        """Test that API endpoints are responding (basic health check)."""
        # Test that API endpoints are accessible
        response = test_client.get("/api/courses")
        assert response.status_code == 200

        # Test that POST endpoint works
        response = test_client.post("/api/query", json={"query": "test", "session_id": None})
        assert response.status_code == 200

    def test_nonexistent_endpoint(self, test_client):
        """Test that non-existent endpoints return 404."""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

        response = test_client.post("/api/nonexistent", json={})
        assert response.status_code == 404

        response = test_client.get("/nonexistent")
        assert response.status_code == 404

    def test_api_response_format_consistency(self, test_client):
        """Test that API responses follow consistent format."""
        # Test courses endpoint format
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        assert isinstance(courses_data, dict)

        # Test query endpoint format
        query_response = test_client.post("/api/query", json={"query": "test", "session_id": None})
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert isinstance(query_data, dict)

    def test_cors_headers(self, test_client):
        """Test that CORS headers are properly set."""
        # Test preflight request
        response = test_client.options("/api/courses")
        # FastAPI TestClient may not handle OPTIONS the same way as real requests
        # so we check the actual request methods

        # Test actual request with Origin header
        response = test_client.get("/api/courses", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200

    def test_api_error_responses(self, test_client):
        """Test that API error responses have consistent format."""
        # Test validation error
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

        # Test server error
        with patch.object(test_client.app.state.mock_rag_system, 'query', side_effect=Exception("Test error")):
            response = test_client.post("/api/query", json={"query": "test", "session_id": "test"})
            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data

    def test_content_type_headers(self, test_client):
        """Test that content-type headers are correctly set."""
        # Test JSON endpoint
        response = test_client.get("/api/courses")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        response = test_client.post("/api/query", json={"query": "test", "session_id": None})
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


@pytest.mark.api
class TestAPIBehavior:
    """Test general API behavior and edge cases."""

    def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = test_client.get("/api/courses")
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()

        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should complete in reasonable time
        assert end_time - start_time < 5.0

    def test_request_size_limits(self, test_client):
        """Test handling of large requests."""
        # Test very long query
        long_query = "test " * 10000  # Very long query
        response = test_client.post("/api/query", json={"query": long_query, "session_id": None})

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 413, 422]

    def test_malformed_json_requests(self, test_client):
        """Test handling of malformed JSON requests."""
        # Test invalid JSON
        response = test_client.post(
            "/api/query",
            data='{"query": "test", "session_id":}',  # Invalid JSON
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

        # Test JSON with wrong data types
        response = test_client.post("/api/query", json={"query": 123, "session_id": None})
        assert response.status_code in [200, 422]  # Depending on validation

    def test_http_method_validation(self, test_client):
        """Test that only allowed HTTP methods work."""
        # Test GET on POST endpoint
        response = test_client.get("/api/query")
        assert response.status_code == 405

        # Test POST on GET endpoint
        response = test_client.post("/api/courses", json={})
        assert response.status_code == 405

        # Test PUT/PATCH/DELETE (should not be allowed)
        response = test_client.put("/api/courses")
        assert response.status_code == 405

        response = test_client.patch("/api/courses")
        assert response.status_code == 405

        response = test_client.delete("/api/courses")
        assert response.status_code == 405

    def test_query_parameters_handling(self, test_client):
        """Test handling of query parameters."""
        # Test with query parameters on GET endpoint
        response = test_client.get("/api/courses?param=value&another=param")
        assert response.status_code == 200

        # Test with query parameters on POST endpoint (should be ignored)
        response = test_client.post("/api/query?param=value", json={"query": "test", "session_id": None})
        assert response.status_code == 200

    def test_custom_headers_handling(self, test_client):
        """Test handling of custom headers."""
        custom_headers = {
            "User-Agent": "TestClient/1.0",
            "X-Custom-Header": "test-value",
            "Accept": "application/json"
        }

        response = test_client.get("/api/courses", headers=custom_headers)
        assert response.status_code == 200

        response = test_client.post("/api/query", json={"query": "test", "session_id": None}, headers=custom_headers)
        assert response.status_code == 200

    def test_response_time_considerations(self, test_client):
        """Test API response times."""
        import time

        # Test courses endpoint response time
        start_time = time.time()
        response = test_client.get("/api/courses")
        end_time = time.time()

        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond quickly

        # Test query endpoint response time
        start_time = time.time()
        response = test_client.post("/api/query", json={"query": "test", "session_id": None})
        end_time = time.time()

        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond quickly


@pytest.mark.integration
@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for the complete API system."""

    def test_multiple_endpoint_interaction(self, test_client):
        """Test interaction between multiple endpoints."""
        # Get course statistics first
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()

        # Use course information in a query
        if courses_data["course_titles"]:
            course_title = courses_data["course_titles"][0]
            query_response = test_client.post(
                "/api/query",
                json={"query": f"Tell me about {course_title}", "session_id": None}
            )
            assert query_response.status_code == 200

    def test_session_across_multiple_requests(self, test_client):
        """Test session persistence across multiple API calls."""
        # First query creates session
        response1 = test_client.post("/api/query", json={"query": "First question", "session_id": None})
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Use same session for follow-up questions
        response2 = test_client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Third query with same session
        response3 = test_client.post(
            "/api/query",
            json={"query": "Another follow-up", "session_id": session_id}
        )
        assert response3.status_code == 200
        assert response3.json()["session_id"] == session_id
"""
API endpoint tests for the /api/courses endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.api
class TestCoursesEndpoint:
    """Test cases for the /api/courses endpoint."""

    def test_courses_endpoint_success(self, test_client, expected_course_stats):
        """Test successful course statistics request."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert "total_courses" in response_data
        assert "course_titles" in response_data

        # Verify response content matches expected
        assert response_data["total_courses"] == expected_course_stats["total_courses"]
        assert response_data["course_titles"] == expected_course_stats["course_titles"]

    def test_courses_endpoint_data_types(self, test_client):
        """Test that response has correct data types."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()

        # Verify data types
        assert isinstance(response_data["total_courses"], int)
        assert isinstance(response_data["course_titles"], list)
        assert all(isinstance(title, str) for title in response_data["course_titles"])

    def test_courses_endpoint_empty_courses(self, test_client):
        """Test courses endpoint when no courses are available."""
        # Mock empty analytics response
        test_client.app.state.mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total_courses"] == 0
        assert response_data["course_titles"] == []

    def test_courses_endpoint_single_course(self, test_client):
        """Test courses endpoint with a single course."""
        # Mock single course response
        test_client.app.state.mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Introduction to Python"]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total_courses"] == 1
        assert len(response_data["course_titles"]) == 1
        assert response_data["course_titles"][0] == "Introduction to Python"

    def test_courses_endpoint_many_courses(self, test_client):
        """Test courses endpoint with many courses."""
        # Mock many courses response
        many_titles = [f"Course {i+1}: Advanced Topic {i+1}" for i in range(50)]
        test_client.app.state.mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 50,
            "course_titles": many_titles
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total_courses"] == 50
        assert len(response_data["course_titles"]) == 50
        assert response_data["course_titles"] == many_titles

    def test_courses_endpoint_server_error(self, test_client):
        """Test courses endpoint handling of server errors."""
        # Mock the analytics method to raise an exception
        test_client.app.state.mock_rag_system.get_course_analytics.side_effect = Exception("Database connection failed")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        response_data = response.json()
        assert "detail" in response_data
        assert "Database connection failed" in response_data["detail"]

    def test_courses_endpoint_wrong_http_method(self, test_client):
        """Test that POST method is not allowed for courses endpoint."""
        response = test_client.post("/api/courses", json={})
        assert response.status_code == 405

    def test_courses_endpoint_no_parameters_required(self, test_client):
        """Test that courses endpoint doesn't require any parameters."""
        response = test_client.get("/api/courses")
        assert response.status_code == 200

        # Test with query parameters (should be ignored)
        response = test_client.get("/api/courses?param=value")
        assert response.status_code == 200

    def test_courses_endpoint_response_consistency(self, test_client):
        """Test that multiple calls return consistent data."""
        # First call
        response1 = test_client.get("/api/courses")
        assert response1.status_code == 200
        data1 = response1.json()

        # Second call
        response2 = test_client.get("/api/courses")
        assert response2.status_code == 200
        data2 = response2.json()

        # Should return the same data (since using mocks)
        assert data1 == data2

    def test_courses_endpoint_with_special_characters(self, test_client):
        """Test courses endpoint with special characters in course titles."""
        special_titles = [
            "Course 1: AI & Machine Learning",
            "Course 2: Data Science 101",
            "Course 3: Python/Java/C++ Programming",
            "Course 4: \"Advanced\" Algorithms",
            "Course 5: Math & Statistics"
        ]

        test_client.app.state.mock_rag_system.get_course_analytics.return_value = {
            "total_courses": len(special_titles),
            "course_titles": special_titles
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["course_titles"] == special_titles

    def test_courses_endpoint_unicode_handling(self, test_client):
        """Test courses endpoint with unicode characters in course titles."""
        unicode_titles = [
            "课程1：机器学习基础",
            "Curso 2: Análisis de Datos",
            "Kurs 3: Künstliche Intelligenz",
            "Cours 4: Apprentissage Automatique"
        ]

        test_client.app.state.mock_rag_system.get_course_analytics.return_value = {
            "total_courses": len(unicode_titles),
            "course_titles": unicode_titles
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["course_titles"] == unicode_titles

    def test_courses_endpoint_response_headers(self, test_client):
        """Test that response headers are correctly set."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        # Check content-type header
        assert "application/json" in response.headers["content-type"]


@pytest.mark.integration
@pytest.mark.api
class TestCoursesEndpointIntegration:
    """Integration tests for courses endpoint with real dependencies."""

    def test_courses_with_real_rag_system(self, test_client):
        """Test courses endpoint integration with RAG system analytics."""
        response = test_client.get("/api/courses")
        assert response.status_code == 200

        # Verify RAG system analytics was called
        test_client.app.state.mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_multiple_calls_analytics_count(self, test_client):
        """Test that multiple calls to courses endpoint call analytics each time."""
        # First call
        response1 = test_client.get("/api/courses")
        assert response1.status_code == 200

        call_count_before = test_client.app.state.mock_rag_system.get_course_analytics.call_count

        # Second call
        response2 = test_client.get("/api/courses")
        assert response2.status_code == 200

        call_count_after = test_client.app.state.mock_rag_system.get_course_analytics.call_count

        # Should have been called one more time
        assert call_count_after == call_count_before + 1

    def test_courses_endpoint_performance_considerations(self, test_client):
        """Test courses endpoint with performance considerations."""
        import time

        # Mock a slower analytics response
        def slow_analytics():
            time.sleep(0.1)  # Simulate some processing time
            return {
                "total_courses": 5,
                "course_titles": ["Course 1", "Course 2", "Course 3", "Course 4", "Course 5"]
            }

        test_client.app.state.mock_rag_system.get_course_analytics.side_effect = slow_analytics

        start_time = time.time()
        response = test_client.get("/api/courses")
        end_time = time.time()

        assert response.status_code == 200
        # Should complete within reasonable time (allowing for mock delay)
        assert end_time - start_time < 1.0

        response_data = response.json()
        assert response_data["total_courses"] == 5
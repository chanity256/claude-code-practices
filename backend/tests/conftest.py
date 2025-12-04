"""
Pytest configuration and shared fixtures for RAG system testing.
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import sys
import os

# Add the backend directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app import app
from rag_system import RAGSystem
from config import config


@pytest.fixture
def test_client():
    """Create a FastAPI test client without static file mounting."""
    # Create a new FastAPI app for testing without static files
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    test_app = FastAPI(title="Test RAG System", root_path="")

    # Add middleware
    test_app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Mock RAG system for testing
    mock_rag_system = Mock(spec=RAGSystem)

    # Mock session manager
    mock_rag_system.session_manager = Mock()
    mock_rag_system.session_manager.create_session.return_value = "test_session_123"

    # Mock query method
    mock_rag_system.query.return_value = (
        "This is a test answer about machine learning.",
        ["course1_script.txt: Chunk 1", "course2_script.txt: Chunk 3"]
    )

    # Mock analytics
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course 1: Introduction", "Course 2: Advanced Topics"]
    }

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Store mock in app state for access in endpoints
    test_app.state.mock_rag_system = mock_rag_system

    # Define endpoints inline
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = test_app.state.mock_rag_system.session_manager.create_session()

            answer, sources = test_app.state.mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = test_app.state.mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return TestClient(test_app)


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for unit tests."""
    mock_rag = Mock(spec=RAGSystem)

    # Mock session manager
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test_session_123"
    mock_rag.session_manager.get_session.return_value = {
        "messages": [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
    }

    # Mock query method with different scenarios
    def mock_query(query, session_id):
        if "error" in query.lower():
            raise Exception("Mock error for testing")
        return (
            f"Mock answer for: {query}",
            [f"source_{i}.txt: Chunk {i}" for i in range(3)]
        )

    mock_rag.query.side_effect = mock_query

    # Mock analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Course 1", "Course 2", "Course 3"],
        "total_chunks": 150
    }

    return mock_rag


@pytest.fixture
def sample_documents():
    """Create sample document data for testing."""
    return {
        "course1": {
            "title": "Introduction to Machine Learning",
            "content": """
            Machine learning is a subset of artificial intelligence that focuses on algorithms
            that can learn from data. The main types include supervised learning, unsupervised
            learning, and reinforcement learning.

            In supervised learning, we train models on labeled data. The algorithm learns to
            map inputs to outputs based on example input-output pairs.
            """,
            "filename": "course1_ml_intro.txt"
        },
        "course2": {
            "title": "Deep Learning Fundamentals",
            "content": """
            Deep learning is a subfield of machine learning that uses neural networks with
            multiple layers. These networks can automatically learn hierarchical representations
            of data.

            Convolutional Neural Networks (CNNs) are particularly effective for image processing
            tasks, while Recurrent Neural Networks (RNNs) excel at sequential data.
            """,
            "filename": "course2_deep_learning.txt"
        }
    }


@pytest.fixture
def temp_docs_dir(sample_documents):
    """Create a temporary directory with sample documents."""
    temp_dir = tempfile.mkdtemp()
    docs_dir = Path(temp_dir) / "docs"
    docs_dir.mkdir()

    # Create sample document files
    for course_data in sample_documents.values():
        file_path = docs_dir / course_data["filename"]
        file_path.write_text(course_data["content"])

    yield docs_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store for testing."""
    mock_store = Mock()
    mock_store.add_documents.return_value = {"added": 10, "skipped": 0}
    mock_store.search.return_value = [
        {
            "content": "Machine learning is a subset of artificial intelligence",
            "metadata": {"source": "course1_ml_intro.txt", "chunk_id": 0}
        },
        {
            "content": "Deep learning uses neural networks with multiple layers",
            "metadata": {"source": "course2_deep_learning.txt", "chunk_id": 1}
        }
    ]
    mock_store.get_stats.return_value = {
        "total_documents": 2,
        "total_chunks": 15
    }
    return mock_store


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager for testing."""
    mock_manager = Mock()
    mock_manager.create_session.return_value = "test_session_456"
    mock_manager.get_session.return_value = {
        "session_id": "test_session_456",
        "messages": [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is..."}
        ]
    }
    mock_manager.update_session.return_value = None
    return mock_manager


@pytest.fixture
def query_request_data():
    """Sample query request data for API testing."""
    return {
        "query": "What is the difference between supervised and unsupervised learning?",
        "session_id": None
    }


@pytest.fixture
def expected_query_response():
    """Expected query response structure for API testing."""
    return {
        "answer": "This is a test answer about machine learning.",
        "sources": ["course1_script.txt: Chunk 1", "course2_script.txt: Chunk 3"],
        "session_id": "test_session_123"
    }


@pytest.fixture
def expected_course_stats():
    """Expected course statistics response for API testing."""
    return {
        "total_courses": 2,
        "course_titles": ["Course 1: Introduction", "Course 2: Advanced Topics"]
    }
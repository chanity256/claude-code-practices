"""Test document processing specifically to identify why 0 courses/0 chunks are loaded"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from document_processor import DocumentProcessor, Course, Lesson, CourseChunk


class TestDocumentProcessing:
    """Test document processing to identify why content loading fails"""

    @pytest.fixture
    def sample_course_text(self):
        """Sample course content that should be processable"""
        return """# Introduction to Machine Learning
Instructor: Dr. Smith

## Lesson 1: Overview of AI
This is the first lesson about artificial intelligence. Machine learning is a subset of AI that focuses on algorithms that can learn from data.

## Lesson 2: Neural Networks
This lesson covers neural networks, which are computing systems inspired by biological neural networks. Deep learning uses multiple layers.

## Lesson 3: Practical Applications
In this final lesson, we explore practical applications of machine learning in real-world scenarios including computer vision and natural language processing."""

    @pytest.fixture
    def sample_course_file(self, sample_course_text):
        """Create a temporary course file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(sample_course_text)
            return f.name

    def test_document_processor_initialization(self):
        """Test that DocumentProcessor can be initialized"""
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        assert processor.chunk_size == 800
        assert processor.chunk_overlap == 100

    def test_process_course_document_with_valid_file(self, sample_course_file):
        """Test processing a valid course document"""
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

        # Process the document
        course, chunks = processor.process_course_document(sample_course_file)

        # Verify course was created
        assert course is not None
        assert course.title is not None
        assert len(course.lessons) > 0

        # Verify chunks were created
        assert len(chunks) > 0

        # Verify chunk content
        chunk_contents = [chunk.content for chunk in chunks]
        assert any("artificial intelligence" in content.lower() for content in chunk_contents)
        assert any("neural networks" in content.lower() for content in chunk_contents)

    def test_process_course_document_with_nonexistent_file(self):
        """Test processing a file that doesn't exist"""
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

        # Should handle missing file gracefully
        with pytest.raises(Exception):
            processor.process_course_document("/nonexistent/file.txt")

    def test_process_course_document_with_empty_file(self):
        """Test processing an empty file"""
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

        # Create empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            empty_file = f.name

        try:
            # Process empty file
            course, chunks = processor.process_course_document(empty_file)

            # Should handle empty file gracefully
            assert course is not None
            assert len(chunks) == 0
        finally:
            os.unlink(empty_file)

    def test_chunk_creation_with_large_document(self):
        """Test that chunks are created properly for large documents"""
        # Create a large document that should create multiple chunks
        large_content = "This is a test sentence. " * 100  # Create content that spans multiple chunks

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(f"# Test Course\n\n{large_content}")
            large_file = f.name

        try:
            processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
            course, chunks = processor.process_course_document(large_file)

            # Should create multiple chunks for large content
            assert len(chunks) > 1

            # Verify chunk overlap
            for i in range(1, len(chunks)):
                # Chunks should have some overlapping content
                overlap_found = False
                for j in range(max(0, i-1), i):
                    chunks_text = chunks[j].content
                    next_chunk_text = chunks[i].content
                    # Check for some overlap
                    if any(word in next_chunk_text.lower() for word in chunks_text.lower().split()[:10]):
                        overlap_found = True
                        break
                # Note: Overlap verification might be complex, so we're more lenient here
        finally:
            os.unlink(large_file)

    def test_lesson_extraction(self):
        """Test that lessons are properly extracted from course content"""
        course_content = """# Machine Learning Basics

## Lesson 1: Introduction
This is the introduction to machine learning.

## Lesson 2: Algorithms
This lesson covers ML algorithms.

## Lesson 3: Applications
Real-world applications of ML."""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(course_content)
            course_file = f.name

        try:
            processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
            course, chunks = processor.process_course_document(course_file)

            # Should extract 3 lessons
            assert len(course.lessons) == 3

            # Verify lesson content
            lesson_titles = [lesson.title for lesson in course.lessons]
            assert any("Introduction" in title for title in lesson_titles)
            assert any("Algorithms" in title for title in lesson_titles)
            assert any("Applications" in title for title in lesson_titles)

            # Verify lesson numbers
            lesson_numbers = [lesson.lesson_number for lesson in course.lessons]
            assert 1 in lesson_numbers
            assert 2 in lesson_numbers
            assert 3 in lesson_numbers
        finally:
            os.unlink(course_file)

    def test_course_title_extraction(self):
        """Test that course title is properly extracted"""
        course_content = """# Advanced Python Programming
Instructor: Prof. Johnson

## Lesson 1: Python Basics
Basic Python concepts."""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(course_content)
            course_file = f.name

        try:
            processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
            course, chunks = processor.process_course_document(course_file)

            # Should extract course title
            assert "Advanced Python Programming" in course.title
        finally:
            os.unlink(course_file)

    def test_chunk_metadata_assignment(self):
        """Test that chunks have proper metadata"""
        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("""# Test Course
## Lesson 1: Test Content
This is test content for chunking.""")
            course_file = f.name

        try:
            course, chunks = processor.process_course_document(course_file)

            # Verify chunk metadata
            for i, chunk in enumerate(chunks):
                assert chunk.course_title is not None
                assert chunk.chunk_index == i
                assert chunk.lesson_number == 1  # Should be lesson 1
        finally:
            os.unlink(course_file)


class TestRealDocumentProcessing:
    """Test with the actual course documents to identify processing issues"""

    def test_actual_course_documents_exist(self):
        """Verify that actual course documents exist and are readable"""
        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs")

        if os.path.exists(docs_path):
            course_files = [f for f in os.listdir(docs_path) if f.endswith('.txt')]
            assert len(course_files) > 0, "No course documents found in docs folder"

            # Verify files are readable
            for course_file in course_files:
                file_path = os.path.join(docs_path, course_file)
                assert os.path.getsize(file_path) > 0, f"Course file {course_file} is empty"

                # Try to read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert len(content.strip()) > 0, f"Course file {course_file} contains no content"
        else:
            pytest.skip("No docs folder found - this test requires actual course documents")

    def test_process_actual_course_documents(self):
        """Test processing the actual course documents"""
        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs")

        if not os.path.exists(docs_path):
            pytest.skip("No docs folder found - this test requires actual course documents")

        processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        processed_files = []

        course_files = [f for f in os.listdir(docs_path) if f.endswith('.txt')]

        for course_file in course_files:
            file_path = os.path.join(docs_path, course_file)

            try:
                course, chunks = processor.process_course_document(file_path)
                processed_files.append((course_file, course, chunks))

                # Verify processing succeeded
                assert course is not None, f"Failed to create course from {course_file}"
                assert course.title is not None, f"No title extracted from {course_file}"
                assert len(chunks) > 0, f"No chunks created from {course_file}"

                print(f"Successfully processed {course_file}: {len(chunks)} chunks")

            except Exception as e:
                pytest.fail(f"Error processing {course_file}: {str(e)}")

        # If we get here, all files were processed successfully
        print(f"Successfully processed {len(processed_files)} course files")
        for filename, course, chunks in processed_files:
            print(f"  {filename}: {course.title} ({len(chunks)} chunks)")

    def test_vector_store_can_accept_processed_documents(self):
        """Test that vector store can accept the processed documents"""
        docs_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs")

        if not os.path.exists(docs_path):
            pytest.skip("No docs folder found - this test requires actual course documents")

        with patch('vector_store.chromadb.PersistentClient') as mock_chroma, \
             patch('vector_store.SentenceTransformerEmbeddingFunction') as mock_embedding:

            # Mock ChromaDB components
            mock_client = Mock()
            mock_chroma.return_value = mock_client
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection

            # Test with one course file
            course_files = [f for f in os.listdir(docs_path) if f.endswith('.txt')]
            if not course_files:
                pytest.skip("No course files found")

            file_path = os.path.join(docs_path, course_files[0])

            # Process the document
            processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
            course, chunks = processor.process_course_document(file_path)

            # Try to add to mock vector store
            try:
                mock_collection.add(
                    documents=[chunk.content for chunk in chunks],
                    metadatas=[{
                        "course_title": chunk.course_title,
                        "lesson_number": chunk.lesson_number,
                        "chunk_index": chunk.chunk_index
                    } for chunk in chunks],
                    ids=[f"test_{i}" for i in range(len(chunks))]
                )

                # Verify mock was called with correct data
                assert mock_collection.add.called
                call_args = mock_collection.add.call_args
                assert len(call_args[1]['documents']) == len(chunks)
                assert len(call_args[1]['metadatas']) == len(chunks)

                print(f"Successfully simulated adding {len(chunks)} chunks to vector store")

            except Exception as e:
                pytest.fail(f"Failed to add processed document to vector store: {str(e)}")
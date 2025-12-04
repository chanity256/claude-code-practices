#!/usr/bin/env python3
"""Debug script to identify why documents aren't being loaded"""

import os
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from document_processor import DocumentProcessor
from vector_store import VectorStore
from config import config

def debug_document_loading():
    """Debug the document loading process step by step"""

    print("=== Document Loading Debug ===")

    # 1. Check docs directory
    docs_path = "../docs"
    print(f"1. Checking docs directory: {docs_path}")
    print(f"   Exists: {os.path.exists(docs_path)}")

    if os.path.exists(docs_path):
        files = os.listdir(docs_path)
        print(f"   Files found: {files}")

        course_files = [f for f in files if f.lower().endswith(('.txt', '.pdf', '.docx'))]
        print(f"   Course files: {course_files}")
    else:
        print("   ERROR: docs directory doesn't exist!")
        return

    # 2. Check ChromaDB path
    print(f"\n2. Checking ChromaDB path: {config.CHROMA_PATH}")
    print(f"   Exists: {os.path.exists(config.CHROMA_PATH)}")

    try:
        # 3. Test document processor directly
        print(f"\n3. Testing document processor...")
        processor = DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP)

        for course_file in course_files[:2]:  # Test first 2 files
            file_path = os.path.join(docs_path, course_file)
            print(f"   Processing: {course_file}")

            try:
                course, chunks = processor.process_course_document(file_path)
                print(f"     Course title: {course.title if course else 'None'}")
                print(f"     Number of lessons: {len(course.lessons) if course else 0}")
                print(f"     Number of chunks: {len(chunks)}")

                if chunks:
                    print(f"     First chunk preview: {chunks[0].content[:100]}...")

            except Exception as e:
                print(f"     ERROR processing {course_file}: {e}")

        # 4. Test vector store
        print(f"\n4. Testing vector store...")
        try:
            vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)

            # Check existing courses
            existing_titles = vector_store.get_existing_course_titles()
            print(f"   Existing course titles in vector store: {existing_titles}")

            course_count = vector_store.get_course_count()
            print(f"   Course count in vector store: {course_count}")

            # Test adding a course
            if course_files:
                test_file = os.path.join(docs_path, course_files[0])
                course, chunks = processor.process_course_document(test_file)

                if course and chunks:
                    print(f"   Attempting to add course: {course.title}")
                    print(f"   With {len(chunks)} chunks")

                    # Check if course already exists
                    if course.title in existing_titles:
                        print(f"   Course already exists - skipping")
                    else:
                        print(f"   Adding new course to vector store...")
                        vector_store.add_course_metadata(course)
                        vector_store.add_course_content(chunks)
                        print(f"   Course added successfully")

                        # Verify it was added
                        new_count = vector_store.get_course_count()
                        print(f"   New course count: {new_count}")

        except Exception as e:
            print(f"   ERROR with vector store: {e}")
            import traceback
            traceback.print_exc()

        # 5. Check environment variables
        print(f"\n5. Environment variables:")
        print(f"   ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
        print(f"   ANTHROPIC_BASE_URL: {os.getenv('ANTHROPIC_BASE_URL', 'NOT SET')}")

    except Exception as e:
        print(f"ERROR during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_document_loading()
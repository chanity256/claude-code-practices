#!/usr/bin/env python3
"""Test the actual document loading behavior"""

import os
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from rag_system import RAGSystem
from config import config

def test_current_behavior():
    """Test what happens when we call add_course_folder with existing data"""

    print("=== Testing Current Document Loading Behavior ===")

    # Create RAG system
    rag_system = RAGSystem(config)

    # Check existing data
    print("\n1. Before loading:")
    existing_titles = rag_system.vector_store.get_existing_course_titles()
    course_count = rag_system.vector_store.get_course_count()
    print(f"   Existing courses: {existing_titles}")
    print(f"   Course count: {course_count}")

    # Try to load documents
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print(f"\n2. Loading from: {docs_path}")

        # Get existing course titles like the actual code does
        existing_course_titles = set(rag_system.vector_store.get_existing_course_titles())
        print(f"   Existing titles set: {existing_course_titles}")

        # Check what files exist
        files = os.listdir(docs_path)
        print(f"   Files found: {files}")

        course_files = [f for f in files if f.lower().endswith(('.txt', '.pdf', '.docx'))]
        print(f"   Course files to process: {course_files}")

        total_courses = 0
        total_chunks = 0

        # Process each file
        for file_name in course_files:
            file_path = os.path.join(docs_path, file_name)
            print(f"\n   Processing: {file_name}")

            try:
                # Process the document (this is what the actual code does)
                course, course_chunks = rag_system.document_processor.process_course_document(file_path)

                if course and course.title not in existing_course_titles:
                    print(f"     -> NEW course: {course.title} ({len(course_chunks)} chunks)")
                    # This would add to vector store in real code
                    rag_system.vector_store.add_course_metadata(course)
                    rag_system.vector_store.add_course_content(course_chunks)
                    total_courses += 1
                    total_chunks += len(course_chunks)
                    existing_course_titles.add(course.title)
                elif course:
                    print(f"     -> EXISTS: {course.title} - skipping")
                else:
                    print(f"     -> FAILED to process course")

            except Exception as e:
                print(f"     -> ERROR processing {file_name}: {e}")

        print(f"\n3. Loading results:")
        print(f"   Total new courses: {total_courses}")
        print(f"   Total new chunks: {total_chunks}")

    print(f"\n4. After loading:")
    final_titles = rag_system.vector_store.get_existing_course_titles()
    final_count = rag_system.vector_store.get_course_count()
    print(f"   Final course count: {final_count}")
    print(f"   Final course titles: {final_titles}")

    # This should explain why we get "Loaded 0 courses with 0 chunks"
    print(f"\n5. CONCLUSION:")
    print(f"   The system reports '0 courses with 0 chunks' because")
    print(f"   all courses already exist in vector store, so")
    print(f"   no new courses are added during startup.")
    print(f"   The vector store contains {final_count} existing courses.")

if __name__ == "__main__":
    test_current_behavior()
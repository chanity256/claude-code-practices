# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) Chatbot** for educational course materials. The system allows users to ask questions about course content and receives intelligent, context-aware responses powered by Anthropic's Claude AI and semantic search.

## Architecture

### Core Components

**Backend (`/backend/`)**: FastAPI-based Python server with modular RAG system:
- `app.py` - Main FastAPI application with API endpoints
- `rag_system.py` - Core orchestrator coordinating all RAG components
- `vector_store.py` - ChromaDB vector storage for semantic search
- `document_processor.py` - Document parsing and chunking (800-char chunks, 100-char overlap)
- `ai_generator.py` - Claude AI integration (claude-sonnet-4-20250514)
- `session_manager.py` - Conversation context and session persistence
- `search_tools.py` - Tool-based semantic search implementation
- `config.py` - Centralized configuration with dataclass settings

**Frontend (`/frontend/`)**: Simple vanilla HTML/CSS/JavaScript chat interface

**Data Storage**:
- `/docs/` - Course material documents (course1_script.txt through course4_script.txt)
- `/backend/chroma_db/` - Vector embeddings for semantic search

### Key Design Patterns

**Tool-Based Search**: Uses a tool manager pattern where the AI can call search functions to find relevant course materials, enabling more accurate source attribution.

**Session Management**: Maintains conversation context (last 2 exchanges) for follow-up questions.

**Incremental Document Loading**: Avoids reprocessing existing courses by tracking course titles in vector store metadata.

## Development Commands

### Setup
```bash
# Install uv package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync

# Set up environment variables
# Create .env file with:
#   ANTHROPIC_API_KEY=your_api_key_here
#   ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
```

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Development URLs
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Configuration

Key settings in `backend/config.py`:
- **Chunk Size**: 800 characters with 100-character overlap for document processing
- **Embedding Model**: `all-MiniLM-L6-v2` for semantic search
- **AI Model**: `claude-sonnet-4-20250514` for response generation
- **Max Results**: 5 search results returned per query
- **Session History**: Last 2 conversation exchanges maintained

## API Endpoints

- `POST /api/query` - Main query endpoint with session management
- `GET /api/courses` - Course statistics and analytics
- Static file serving from `/frontend/` with development no-cache headers

## Working with Course Documents

Course documents should be placed in `/docs/` directory. Supported formats: `.txt`, `.pdf`, `.docx`.

The system automatically:
- Detects new courses by title to avoid reprocessing
- Chunks documents into manageable pieces for vector storage
- Creates semantic embeddings for intelligent search
- Maintains source attribution for responses

## Key Dependencies

- `chromadb==1.0.15` - Vector database for semantic search
- `anthropic==0.58.2` - Claude AI API integration
- `sentence-transformers==5.0.0` - Text embeddings
- `fastapi==0.116.1` - Web framework
- `uvicorn==0.35.0` - ASGI server
- `python-multipart==0.0.20` - File upload support
- `python-dotenv==1.1.1` - Environment variable management

## Important Implementation Notes

- **CORS Configuration**: Allows all origins for development convenience
- **Environment Variables**: Requires `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` in `.env` file
- **Vector Store Persistence**: ChromaDB data persists between sessions in `/backend/chroma_db/`
- **Error Handling**: Comprehensive try-catch blocks with user-friendly error messages
- **Development Headers**: Custom static file serving disables caching for frontend development

## Testing and Debugging

The system includes debug prints for:
- Document loading progress
- Course addition statistics
- Error tracking during document processing

For debugging AI responses, check the tool manager's source retrieval and session conversation history in the session manager.
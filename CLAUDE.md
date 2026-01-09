# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important

- Always use uv to run the server
- Always use uv to manage all dependencies

## Commands

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Run the server (must run from backend directory)
cd backend && uv run uvicorn app:app --reload --port 8000

# Or use the shell script from root
./run.sh

# Git commands
git status
git add .
git commit -m "message"
git push
```

The web interface is at `http://localhost:8000` and API docs at `http://localhost:8000/docs`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials with a FastAPI backend and vanilla JS frontend.

### Data Flow

1. **Document Ingestion** (on startup): `docs/` folder → `DocumentProcessor` (chunks text) → `VectorStore` (stores in ChromaDB)

2. **Query Processing**: User question → `/api/query` → `RAGSystem.query()` → AI decides whether to search → `VectorStore.search()` → AI generates response with context

### Key Components

- **backend/rag_system.py**: Orchestrator that coordinates all components
- **backend/ai_generator.py**: Anthropic Claude integration with tool use support
- **backend/vector_store.py**: ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks)
- **backend/search_tools.py**: `CourseSearchTool` that AI can invoke for semantic search
- **backend/document_processor.py**: Parses course documents and splits into chunks
- **backend/session_manager.py**: Manages conversation history per session
- **frontend/**: Static HTML/JS/CSS served by FastAPI

### Configuration

All settings in `backend/config.py`:
- Model: `claude-sonnet-4-20250514`
- Embeddings: `all-MiniLM-L6-v2` (SentenceTransformer)
- Chunk size: 800 chars with 100 overlap
- Max search results: 5

### API Endpoints

- `POST /api/query` - Main chat endpoint (takes `query` and optional `session_id`)
- `GET /api/courses` - Returns course catalog statistics

# RAG Financial Assistant

A React frontend and FastAPI backend application for financial document analysis using Retrieval-Augmented Generation (RAG).

## Project Structure

```
├── frontend/          # React TypeScript application
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/           # FastAPI Python application
│   ├── app/
│   ├── tests/
│   └── requirements.txt
└── docker-compose.dev.yml  # Development services
```

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose (for databases)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Start development services (PostgreSQL and Redis):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

6. Run the FastAPI server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The React app will be available at http://localhost:3000

## API Documentation

Once the backend is running, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Workflow

1. Start the development services: `docker-compose -f docker-compose.dev.yml up -d`
2. Start the FastAPI backend: `cd backend && python -m uvicorn app.main:app --reload`
3. Start the React frontend: `cd frontend && npm run dev`
4. Access the application at http://localhost:3000

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for embeddings and chat
- `PINECONE_API_KEY`: Pinecone vector database API key
- `REDIS_URL`: Redis connection string

## Next Steps

This is the initial project structure. Future tasks will implement:
- Company validation and search
- SEC document ingestion
- Vector database integration
- RAG query processing
- Chat interface components
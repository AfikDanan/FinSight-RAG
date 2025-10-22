from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import API routers
from app.api.companies import router as companies_router

# Create FastAPI application
app = FastAPI(
    title="RAG Financial Assistant API",
    description="API for financial document analysis and chat interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "RAG Financial Assistant API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-financial-assistant"}

# Include API routers
app.include_router(companies_router)

@app.get("/api/status")
async def api_status():
    return {
        "api_version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "companies": "/api/companies",
            "chat": "/api/chat",
            "documents": "/api/documents"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
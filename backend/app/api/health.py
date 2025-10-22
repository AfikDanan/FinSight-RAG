"""
Health check endpoints for monitoring database and system status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db, get_database_health, check_database_connection
from app.repositories import get_repo_manager, RepositoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.
    
    Returns:
        Simple health status
    """
    return {"status": "healthy", "service": "RAG Financial Assistant API"}


@router.get("/database")
async def database_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Database health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Database health information
        
    Raises:
        HTTPException: If database is unhealthy
    """
    try:
        health_info = get_database_health()
        
        if health_info["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Database is unhealthy")
        
        return health_info
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database health check failed")


@router.get("/detailed")
async def detailed_health_check(
    repo_manager: RepositoryManager = Depends(get_repo_manager)
) -> Dict[str, Any]:
    """
    Detailed health check with database statistics.
    
    Args:
        repo_manager: Repository manager
        
    Returns:
        Detailed health information
    """
    try:
        # Basic database health
        db_health = get_database_health()
        
        # Get basic statistics
        company_count = repo_manager.company.count()
        document_count = repo_manager.document.count()
        chunk_count = repo_manager.document_chunk.count()
        
        # Get processing statistics
        processed_docs = repo_manager.document.count({"processing_status": "completed"})
        pending_docs = repo_manager.document.count({"processing_status": "pending"})
        failed_docs = repo_manager.document.count({"processing_status": "failed"})
        
        return {
            "status": "healthy" if db_health["status"] == "healthy" else "degraded",
            "database": db_health,
            "statistics": {
                "companies": company_count,
                "documents": document_count,
                "document_chunks": chunk_count,
                "processed_documents": processed_docs,
                "pending_documents": pending_docs,
                "failed_documents": failed_docs
            },
            "processing_health": {
                "processing_rate": (processed_docs / document_count * 100) if document_count > 0 else 0,
                "failure_rate": (failed_docs / document_count * 100) if document_count > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": {"status": "unknown"},
            "statistics": {},
            "processing_health": {}
        }


@router.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for container orchestration.
    
    Returns:
        Readiness status
    """
    try:
        # Check database connection
        if not check_database_connection():
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {
            "status": "ready",
            "checks": {
                "database": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/liveness")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for container orchestration.
    
    Returns:
        Liveness status
    """
    return {"status": "alive", "service": "RAG Financial Assistant API"}
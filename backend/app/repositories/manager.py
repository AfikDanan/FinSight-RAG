"""
Repository manager for coordinating database operations across multiple repositories.
Provides a unified interface for accessing all repositories with proper session management.
"""

from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.repositories.company import CompanyRepository
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository

logger = logging.getLogger(__name__)


class RepositoryManager:
    """
    Manager class that provides access to all repositories with shared database session.
    Ensures consistent transaction management across multiple repository operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository manager with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._company_repo: Optional[CompanyRepository] = None
        self._document_repo: Optional[DocumentRepository] = None
        self._document_chunk_repo: Optional[DocumentChunkRepository] = None
    
    @property
    def company(self) -> CompanyRepository:
        """Get company repository instance."""
        if self._company_repo is None:
            self._company_repo = CompanyRepository(self.db)
        return self._company_repo
    
    @property
    def document(self) -> DocumentRepository:
        """Get document repository instance."""
        if self._document_repo is None:
            self._document_repo = DocumentRepository(self.db)
        return self._document_repo
    
    @property
    def document_chunk(self) -> DocumentChunkRepository:
        """Get document chunk repository instance."""
        if self._document_chunk_repo is None:
            self._document_chunk_repo = DocumentChunkRepository(self.db)
        return self._document_chunk_repo
    
    def commit(self):
        """Commit the current transaction."""
        try:
            self.db.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            self.db.rollback()
            raise
    
    def rollback(self):
        """Rollback the current transaction."""
        try:
            self.db.rollback()
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise
    
    def close(self):
        """Close the database session."""
        try:
            self.db.close()
            logger.debug("Database session closed")
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
            raise


def get_repository_manager(db: Session = None) -> RepositoryManager:
    """
    Get repository manager instance.
    
    Args:
        db: Optional database session. If not provided, will use dependency injection.
        
    Returns:
        RepositoryManager instance
    """
    if db is None:
        db = next(get_db())
    
    return RepositoryManager(db)


# Dependency function for FastAPI
def get_repo_manager(db: Session = None) -> RepositoryManager:
    """
    FastAPI dependency function to get repository manager.
    
    Args:
        db: Database session from dependency injection
        
    Returns:
        RepositoryManager instance
    """
    return RepositoryManager(db)
"""
Document repository for database operations related to financial documents.
Provides specialized methods for document-specific queries and operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import logging

from app.models.database import Document, Company
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document model with specialized document operations.
    """
    
    def __init__(self, db: Session):
        super().__init__(Document, db)
    
    def get_by_accession_number(self, accession_number: str) -> Optional[Document]:
        """
        Get document by SEC accession number.
        
        Args:
            accession_number: SEC accession number
            
        Returns:
            Document instance or None if not found
        """
        try:
            return self.db.query(Document).filter(
                Document.accession_number == accession_number
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting document by accession number {accession_number}: {e}")
            raise
    
    def get_by_ticker(
        self, 
        ticker: str, 
        filing_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Document]:
        """
        Get documents for a specific company ticker.
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Optional filing type filter (10-K, 10-Q, etc.)
            limit: Maximum number of results
            
        Returns:
            List of documents for the company
        """
        try:
            query = self.db.query(Document).filter(Document.ticker == ticker.upper())
            
            if filing_type:
                query = query.filter(Document.filing_type == filing_type)
            
            return query.order_by(desc(Document.filed_date)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting documents for ticker {ticker}: {e}")
            raise
    
    def get_recent_documents(
        self, 
        days: int = 30, 
        filing_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """
        Get recently filed documents.
        
        Args:
            days: Number of days to look back
            filing_type: Optional filing type filter
            limit: Maximum number of results
            
        Returns:
            List of recent documents
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = self.db.query(Document).filter(Document.filed_date >= cutoff_date)
            
            if filing_type:
                query = query.filter(Document.filing_type == filing_type)
            
            return query.order_by(desc(Document.filed_date)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent documents: {e}")
            raise
    
    def get_processed_documents(
        self, 
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """
        Get successfully processed documents.
        
        Args:
            ticker: Optional ticker filter
            limit: Maximum number of results
            
        Returns:
            List of processed documents
        """
        try:
            query = self.db.query(Document).filter(
                Document.processing_status == "completed"
            )
            
            if ticker:
                query = query.filter(Document.ticker == ticker.upper())
            
            return query.order_by(desc(Document.processed_at)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting processed documents: {e}")
            raise
    
    def get_pending_documents(self, limit: int = 100) -> List[Document]:
        """
        Get documents pending processing.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of pending documents
        """
        try:
            return self.db.query(Document).filter(
                Document.processing_status.in_(["pending", "processing"])
            ).order_by(Document.created_at).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting pending documents: {e}")
            raise
    
    def get_failed_documents(self, limit: int = 100) -> List[Document]:
        """
        Get documents that failed processing.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of failed documents
        """
        try:
            return self.db.query(Document).filter(
                Document.processing_status == "failed"
            ).order_by(desc(Document.created_at)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting failed documents: {e}")
            raise
    
    def get_documents_by_period(
        self, 
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Document]:
        """
        Get documents for a company within a specific period.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start of period
            end_date: End of period
            
        Returns:
            List of documents in the period
        """
        try:
            return self.db.query(Document).filter(
                and_(
                    Document.ticker == ticker.upper(),
                    Document.period_end >= start_date,
                    Document.period_end <= end_date
                )
            ).order_by(Document.period_end).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting documents by period for {ticker}: {e}")
            raise
    
    def get_latest_filing(
        self, 
        ticker: str, 
        filing_type: str
    ) -> Optional[Document]:
        """
        Get the most recent filing of a specific type for a company.
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Filing type (10-K, 10-Q, etc.)
            
        Returns:
            Latest document or None if not found
        """
        try:
            return self.db.query(Document).filter(
                and_(
                    Document.ticker == ticker.upper(),
                    Document.filing_type == filing_type
                )
            ).order_by(desc(Document.filed_date)).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest {filing_type} for {ticker}: {e}")
            raise
    
    def update_processing_status(
        self, 
        document_id: str, 
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """
        Update document processing status.
        
        Args:
            document_id: Document ID
            status: New processing status
            error_message: Optional error message for failed status
            
        Returns:
            Updated document or None if not found
        """
        try:
            document = self.get(document_id)
            if not document:
                return None
            
            document.processing_status = status
            if error_message:
                document.processing_error = error_message
            
            if status == "completed":
                document.processed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Updated processing status for document {document_id}: {status}")
            return document
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing status for document {document_id}: {e}")
            self.db.rollback()
            raise
    
    def get_documents_with_chunks(
        self, 
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """
        Get documents that have associated chunks.
        
        Args:
            ticker: Optional ticker filter
            limit: Maximum number of results
            
        Returns:
            List of documents with chunks
        """
        try:
            query = self.db.query(Document).filter(
                Document.chunks.any(),
                Document.processing_status == "completed"
            )
            
            if ticker:
                query = query.filter(Document.ticker == ticker.upper())
            
            return query.order_by(desc(Document.processed_at)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting documents with chunks: {e}")
            raise
    
    def get_filing_statistics(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Get filing statistics for a company or all companies.
        
        Args:
            ticker: Optional ticker filter
            
        Returns:
            Dictionary with filing statistics
        """
        try:
            query = self.db.query(Document)
            
            if ticker:
                query = query.filter(Document.ticker == ticker.upper())
            
            total_documents = query.count()
            processed_documents = query.filter(Document.processing_status == "completed").count()
            pending_documents = query.filter(Document.processing_status.in_(["pending", "processing"])).count()
            failed_documents = query.filter(Document.processing_status == "failed").count()
            
            # Get filing type breakdown
            filing_types = self.db.query(
                Document.filing_type,
                func.count(Document.id).label('count')
            )
            
            if ticker:
                filing_types = filing_types.filter(Document.ticker == ticker.upper())
            
            filing_type_stats = {
                result.filing_type: result.count 
                for result in filing_types.group_by(Document.filing_type).all()
            }
            
            return {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'pending_documents': pending_documents,
                'failed_documents': failed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                'filing_types': filing_type_stats
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting filing statistics: {e}")
            raise
    
    def cleanup_old_failed_documents(self, days: int = 30) -> int:
        """
        Clean up old failed documents.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of documents cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = self.db.query(Document).filter(
                and_(
                    Document.processing_status == "failed",
                    Document.created_at < cutoff_date
                )
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted_count} old failed documents")
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up old failed documents: {e}")
            self.db.rollback()
            raise
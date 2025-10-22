"""
Document chunk repository for database operations related to document chunks.
Provides specialized methods for chunk-specific queries and operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from app.models.database import DocumentChunk, Document
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """
    Repository for DocumentChunk model with specialized chunk operations.
    """
    
    def __init__(self, db: Session):
        super().__init__(DocumentChunk, db)
    
    def get_by_document_id(
        self, 
        document_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """
        Get chunks for a specific document.
        
        Args:
            document_id: Document ID
            skip: Number of chunks to skip
            limit: Maximum number of chunks
            
        Returns:
            List of document chunks
        """
        try:
            return self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunks for document {document_id}: {e}")
            raise
    
    def get_by_pinecone_id(self, pinecone_id: str) -> Optional[DocumentChunk]:
        """
        Get chunk by Pinecone vector ID.
        
        Args:
            pinecone_id: Pinecone vector ID
            
        Returns:
            Document chunk or None if not found
        """
        try:
            return self.db.query(DocumentChunk).filter(
                DocumentChunk.pinecone_id == pinecone_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunk by Pinecone ID {pinecone_id}: {e}")
            raise
    
    def get_by_content_hash(self, content_hash: str) -> Optional[DocumentChunk]:
        """
        Get chunk by content hash (for deduplication).
        
        Args:
            content_hash: SHA-256 hash of content
            
        Returns:
            Document chunk or None if not found
        """
        try:
            return self.db.query(DocumentChunk).filter(
                DocumentChunk.content_hash == content_hash
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunk by content hash: {e}")
            raise
    
    def get_chunks_by_section(
        self, 
        document_id: str,
        section: str,
        subsection: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Get chunks from a specific document section.
        
        Args:
            document_id: Document ID
            section: Section name
            subsection: Optional subsection name
            
        Returns:
            List of chunks from the section
        """
        try:
            query = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.section == section
                )
            )
            
            if subsection:
                query = query.filter(DocumentChunk.subsection == subsection)
            
            return query.order_by(DocumentChunk.chunk_index).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunks by section {section}: {e}")
            raise
    
    def get_financial_data_chunks(
        self, 
        document_id: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """
        Get chunks containing financial data.
        
        Args:
            document_id: Optional document ID filter
            ticker: Optional ticker filter
            limit: Maximum number of chunks
            
        Returns:
            List of financial data chunks
        """
        try:
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.is_financial_data == True
            )
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            if ticker:
                query = query.join(Document).filter(Document.ticker == ticker.upper())
            
            return query.order_by(desc(DocumentChunk.confidence_score)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting financial data chunks: {e}")
            raise
    
    def get_table_chunks(
        self, 
        document_id: Optional[str] = None,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """
        Get chunks containing tabular data.
        
        Args:
            document_id: Optional document ID filter
            limit: Maximum number of chunks
            
        Returns:
            List of table chunks
        """
        try:
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.is_table == True
            )
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            return query.order_by(desc(DocumentChunk.confidence_score)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting table chunks: {e}")
            raise
    
    def search_chunks_by_content(
        self, 
        search_term: str,
        ticker: Optional[str] = None,
        section: Optional[str] = None,
        limit: int = 50
    ) -> List[DocumentChunk]:
        """
        Search chunks by content text.
        
        Args:
            search_term: Text to search for
            ticker: Optional ticker filter
            section: Optional section filter
            limit: Maximum number of results
            
        Returns:
            List of matching chunks
        """
        try:
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.content.ilike(f"%{search_term}%")
            )
            
            if ticker:
                query = query.join(Document).filter(Document.ticker == ticker.upper())
            
            if section:
                query = query.filter(DocumentChunk.section == section)
            
            return query.order_by(desc(DocumentChunk.confidence_score)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error searching chunks by content: {e}")
            raise
    
    def get_chunks_by_page_range(
        self, 
        document_id: str,
        start_page: int,
        end_page: int
    ) -> List[DocumentChunk]:
        """
        Get chunks within a specific page range.
        
        Args:
            document_id: Document ID
            start_page: Starting page number
            end_page: Ending page number
            
        Returns:
            List of chunks in the page range
        """
        try:
            return self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.page_number >= start_page,
                    DocumentChunk.page_number <= end_page
                )
            ).order_by(DocumentChunk.page_number, DocumentChunk.chunk_index).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunks by page range: {e}")
            raise
    
    def get_high_confidence_chunks(
        self, 
        document_id: Optional[str] = None,
        min_confidence: float = 0.8,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """
        Get chunks with high confidence scores.
        
        Args:
            document_id: Optional document ID filter
            min_confidence: Minimum confidence threshold
            limit: Maximum number of chunks
            
        Returns:
            List of high-confidence chunks
        """
        try:
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.confidence_score >= min_confidence
            )
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            return query.order_by(desc(DocumentChunk.confidence_score)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting high confidence chunks: {e}")
            raise
    
    def update_pinecone_id(self, chunk_id: str, pinecone_id: str) -> Optional[DocumentChunk]:
        """
        Update Pinecone vector ID for a chunk.
        
        Args:
            chunk_id: Chunk ID
            pinecone_id: Pinecone vector ID
            
        Returns:
            Updated chunk or None if not found
        """
        try:
            chunk = self.get(chunk_id)
            if not chunk:
                return None
            
            chunk.pinecone_id = pinecone_id
            self.db.commit()
            self.db.refresh(chunk)
            
            logger.info(f"Updated Pinecone ID for chunk {chunk_id}")
            return chunk
        except SQLAlchemyError as e:
            logger.error(f"Error updating Pinecone ID for chunk {chunk_id}: {e}")
            self.db.rollback()
            raise
    
    def get_chunk_statistics(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about document chunks.
        
        Args:
            document_id: Optional document ID filter
            
        Returns:
            Dictionary with chunk statistics
        """
        try:
            query = self.db.query(DocumentChunk)
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            total_chunks = query.count()
            financial_chunks = query.filter(DocumentChunk.is_financial_data == True).count()
            table_chunks = query.filter(DocumentChunk.is_table == True).count()
            
            # Average statistics
            avg_stats = self.db.query(
                func.avg(DocumentChunk.word_count).label('avg_word_count'),
                func.avg(DocumentChunk.character_count).label('avg_char_count'),
                func.avg(DocumentChunk.confidence_score).label('avg_confidence')
            )
            
            if document_id:
                avg_stats = avg_stats.filter(DocumentChunk.document_id == document_id)
            
            stats_result = avg_stats.first()
            
            # Section breakdown
            section_stats = self.db.query(
                DocumentChunk.section,
                func.count(DocumentChunk.id).label('count')
            )
            
            if document_id:
                section_stats = section_stats.filter(DocumentChunk.document_id == document_id)
            
            section_breakdown = {
                result.section: result.count 
                for result in section_stats.group_by(DocumentChunk.section).all()
                if result.section
            }
            
            return {
                'total_chunks': total_chunks,
                'financial_chunks': financial_chunks,
                'table_chunks': table_chunks,
                'avg_word_count': float(stats_result.avg_word_count) if stats_result.avg_word_count else 0,
                'avg_character_count': float(stats_result.avg_char_count) if stats_result.avg_char_count else 0,
                'avg_confidence_score': float(stats_result.avg_confidence) if stats_result.avg_confidence else 0,
                'section_breakdown': section_breakdown
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunk statistics: {e}")
            raise
    
    def delete_chunks_by_document(self, document_id: str) -> int:
        """
        Delete all chunks for a specific document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Number of chunks deleted
        """
        try:
            deleted_count = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}")
            self.db.rollback()
            raise
    
    def get_chunks_without_embeddings(self, limit: int = 100) -> List[DocumentChunk]:
        """
        Get chunks that don't have Pinecone embeddings yet.
        
        Args:
            limit: Maximum number of chunks
            
        Returns:
            List of chunks without embeddings
        """
        try:
            return self.db.query(DocumentChunk).filter(
                DocumentChunk.pinecone_id.is_(None)
            ).order_by(DocumentChunk.created_at).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting chunks without embeddings: {e}")
            raise
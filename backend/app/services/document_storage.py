"""
Document download and storage service for SEC filings.
Handles document retrieval, storage, deduplication, and progress tracking.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Callable, Any, Tuple
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import aiofiles
import mimetypes
from urllib.parse import urlparse
import time

from app.models.database import Document, Company
from app.repositories.document import DocumentRepository
from app.repositories.company import CompanyRepository
from app.services.sec_edgar_scraper import Filing, SECEdgarScraper
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentStorageService:
    """
    Service for downloading and storing SEC filing documents.
    Handles document retrieval, local storage, deduplication, and progress tracking.
    """
    
    def __init__(self, 
                 db: Session,
                 storage_path: str = None,
                 max_concurrent_downloads: int = 3,
                 retry_attempts: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize document storage service.
        
        Args:
            db: Database session
            storage_path: Local storage directory path
            max_concurrent_downloads: Maximum concurrent downloads
            retry_attempts: Number of retry attempts for failed downloads
            retry_delay: Delay between retry attempts in seconds
        """
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.company_repo = CompanyRepository(db)
        
        # Storage configuration
        self.storage_path = Path(storage_path or settings.document_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Download configuration
        self.max_concurrent_downloads = max_concurrent_downloads
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # HTTP client for downloads
        self.client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={
                "User-Agent": f"{settings.app_name} afikdanan@google.com"
            }
        )
        
        # Progress tracking
        self._progress_callbacks: List[Callable] = []
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
    
    def add_progress_callback(self, callback: Callable[[str, int, int], None]):
        """
        Add progress callback for tracking download progress.
        
        Args:
            callback: Function called with (status, current, total) parameters
        """
        self._progress_callbacks.append(callback)
    
    async def _notify_progress(self, status: str, current: int, total: int):
        """Notify all progress callbacks"""
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status, current, total)
                else:
                    callback(status, current, total)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def _generate_file_path(self, filing: Filing) -> Path:
        """
        Generate local file path for a filing.
        
        Args:
            filing: Filing object
            
        Returns:
            Path object for local storage
        """
        # Create directory structure: ticker/year/filing_type/
        year = filing.filing_date.year
        directory = self.storage_path / filing.ticker / str(year) / filing.filing_type
        directory.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: accession_number.extension
        parsed_url = urlparse(filing.document_url)
        filename = Path(parsed_url.path).name
        
        # Ensure we have an extension
        if not filename or '.' not in filename:
            filename = f"{filing.accession_number}.html"
        
        return directory / filename
    
    def _calculate_content_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of document content.
        
        Args:
            content: Document content bytes
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()
    
    async def _download_document_content(self, url: str) -> Tuple[bytes, str]:
        """
        Download document content with retry logic.
        
        Args:
            url: Document URL
            
        Returns:
            Tuple of (content_bytes, content_type)
            
        Raises:
            httpx.HTTPError: If download fails after all retries
        """
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"Downloading document (attempt {attempt + 1}): {url}")
                
                response = await self.client.get(url)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', 'text/html')
                return response.content, content_type
                
            except httpx.HTTPError as e:
                last_exception = e
                logger.warning(f"Download attempt {attempt + 1} failed for {url}: {e}")
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                continue
        
        # All attempts failed
        logger.error(f"Failed to download document after {self.retry_attempts} attempts: {url}")
        raise last_exception
    
    async def _save_document_to_disk(self, content: bytes, file_path: Path) -> int:
        """
        Save document content to disk.
        
        Args:
            content: Document content bytes
            file_path: Local file path
            
        Returns:
            File size in bytes
        """
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            file_size = len(content)
            logger.debug(f"Saved document to {file_path} ({file_size} bytes)")
            return file_size
            
        except Exception as e:
            logger.error(f"Failed to save document to {file_path}: {e}")
            raise
    
    def _detect_document_format(self, content_type: str, file_path: Path) -> str:
        """
        Detect document format from content type and file extension.
        
        Args:
            content_type: HTTP content type
            file_path: File path
            
        Returns:
            Document format string (HTML, PDF, XBRL, TXT)
        """
        # Check content type first
        if 'html' in content_type.lower():
            return 'HTML'
        elif 'pdf' in content_type.lower():
            return 'PDF'
        elif 'xml' in content_type.lower() or 'xbrl' in content_type.lower():
            return 'XBRL'
        elif 'text' in content_type.lower():
            return 'TXT'
        
        # Check file extension
        extension = file_path.suffix.lower()
        if extension == '.html' or extension == '.htm':
            return 'HTML'
        elif extension == '.pdf':
            return 'PDF'
        elif extension == '.xml' or extension == '.xbrl':
            return 'XBRL'
        elif extension == '.txt':
            return 'TXT'
        
        # Default to HTML for SEC filings
        return 'HTML'
    
    async def _check_document_exists(self, filing: Filing) -> Optional[Document]:
        """
        Check if document already exists in database.
        
        Args:
            filing: Filing object
            
        Returns:
            Existing document or None
        """
        try:
            return self.document_repo.get_by_accession_number(filing.accession_number)
        except SQLAlchemyError as e:
            logger.error(f"Error checking document existence: {e}")
            return None
    
    async def _create_document_record(self, 
                                    filing: Filing, 
                                    file_path: Path,
                                    file_size: int,
                                    document_format: str) -> Document:
        """
        Create document record in database.
        
        Args:
            filing: Filing object
            file_path: Local file path
            file_size: File size in bytes
            document_format: Document format
            
        Returns:
            Created document record
        """
        try:
            # Ensure company exists
            company = self.company_repo.get(filing.ticker)
            if not company:
                # Create company record if it doesn't exist
                company = Company(
                    ticker=filing.ticker,
                    name=filing.company_name,
                    cik_str=int(filing.cik)
                )
                company = self.company_repo.create(company)
            
            # Create document record
            document = Document(
                ticker=filing.ticker,
                filing_type=filing.filing_type,
                accession_number=filing.accession_number,
                period_end=filing.period_end,
                filed_date=filing.filing_date,
                document_url=filing.document_url,
                file_path=str(file_path),
                file_size=file_size,
                document_format=document_format,
                processing_status="pending"
            )
            
            return self.document_repo.create(document)
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating document record: {e}")
            raise
    
    async def download_and_store_filing(self, filing: Filing) -> Optional[Document]:
        """
        Download and store a single SEC filing.
        
        Args:
            filing: Filing object to download
            
        Returns:
            Document record or None if failed
        """
        try:
            # Check if document already exists
            existing_doc = await self._check_document_exists(filing)
            if existing_doc:
                logger.info(f"Document already exists: {filing.accession_number}")
                return existing_doc
            
            # Generate file path
            file_path = self._generate_file_path(filing)
            
            # Download document content
            logger.info(f"Downloading filing: {filing.accession_number}")
            content, content_type = await self._download_document_content(filing.document_url)
            
            # Detect document format
            document_format = self._detect_document_format(content_type, file_path)
            
            # Save to disk
            file_size = await self._save_document_to_disk(content, file_path)
            
            # Create database record
            document = await self._create_document_record(
                filing, file_path, file_size, document_format
            )
            
            logger.info(f"Successfully stored document: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to download and store filing {filing.accession_number}: {e}")
            return None
    
    async def download_and_store_filings(self, 
                                       filings: List[Filing],
                                       progress_callback: Optional[Callable] = None) -> List[Document]:
        """
        Download and store multiple SEC filings with concurrency control.
        
        Args:
            filings: List of Filing objects to download
            progress_callback: Optional progress callback function
            
        Returns:
            List of successfully stored Document records
        """
        if not filings:
            return []
        
        logger.info(f"Starting download of {len(filings)} filings")
        
        # Add progress callback if provided
        if progress_callback:
            self.add_progress_callback(progress_callback)
        
        # Track progress
        total_filings = len(filings)
        completed_filings = 0
        successful_documents = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_with_semaphore(filing: Filing) -> Optional[Document]:
            nonlocal completed_filings
            
            async with semaphore:
                try:
                    document = await self.download_and_store_filing(filing)
                    if document:
                        successful_documents.append(document)
                    
                    completed_filings += 1
                    await self._notify_progress("downloading", completed_filings, total_filings)
                    
                    return document
                    
                except Exception as e:
                    logger.error(f"Error downloading filing {filing.accession_number}: {e}")
                    completed_filings += 1
                    await self._notify_progress("downloading", completed_filings, total_filings)
                    return None
        
        # Start initial progress notification
        await self._notify_progress("downloading", 0, total_filings)
        
        # Execute downloads concurrently
        tasks = [download_with_semaphore(filing) for filing in filings]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Final progress notification
        await self._notify_progress("completed", total_filings, total_filings)
        
        logger.info(f"Download completed: {len(successful_documents)}/{total_filings} successful")
        return successful_documents
    
    async def process_company_filings(self, 
                                    ticker: str,
                                    years: int,
                                    filing_types: List[str] = None,
                                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Complete workflow to scrape and store filings for a company.
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years back to scrape (1, 3, or 5)
            filing_types: List of filing types to scrape
            progress_callback: Optional progress callback function
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting filing processing for {ticker} ({years} years)")
            
            # Initialize SEC scraper
            async with SECEdgarScraper() as scraper:
                # Scrape filings
                if progress_callback:
                    await progress_callback("scraping", 0, 100)
                
                filings = await scraper.scrape_filings(ticker, years, filing_types)
                
                if not filings:
                    logger.warning(f"No filings found for {ticker}")
                    return {
                        "ticker": ticker,
                        "status": "completed",
                        "filings_found": 0,
                        "documents_stored": 0,
                        "processing_time": time.time() - start_time,
                        "error": None
                    }
                
                # Download and store documents
                if progress_callback:
                    await progress_callback("downloading", 25, 100)
                
                # Create progress wrapper for download phase
                async def download_progress(status: str, current: int, total: int):
                    # Map download progress to overall progress (25-100%)
                    progress_percent = 25 + int((current / total) * 75)
                    await progress_callback("downloading", progress_percent, 100)
                
                documents = await self.download_and_store_filings(
                    filings, 
                    download_progress if progress_callback else None
                )
                
                # Final progress update
                if progress_callback:
                    await progress_callback("completed", 100, 100)
                
                processing_time = time.time() - start_time
                
                result = {
                    "ticker": ticker,
                    "status": "completed",
                    "filings_found": len(filings),
                    "documents_stored": len(documents),
                    "processing_time": processing_time,
                    "error": None
                }
                
                logger.info(f"Filing processing completed for {ticker}: {result}")
                return result
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to process filings for {ticker}: {str(e)}"
            logger.error(error_msg)
            
            if progress_callback:
                await progress_callback("error", 0, 100)
            
            return {
                "ticker": ticker,
                "status": "failed",
                "filings_found": 0,
                "documents_stored": 0,
                "processing_time": processing_time,
                "error": error_msg
            }
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            # Calculate total storage size
            total_size = 0
            file_count = 0
            
            for file_path in self.storage_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            # Get database statistics
            db_stats = self.document_repo.get_filing_statistics()
            
            return {
                "storage_path": str(self.storage_path),
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "database_stats": db_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {
                "error": str(e)
            }
    
    async def cleanup_orphaned_files(self) -> int:
        """
        Clean up files that don't have corresponding database records.
        
        Returns:
            Number of files cleaned up
        """
        try:
            cleaned_count = 0
            
            for file_path in self.storage_path.rglob('*'):
                if file_path.is_file():
                    # Check if file has corresponding database record
                    relative_path = str(file_path.relative_to(self.storage_path))
                    
                    # Query database for document with this file path
                    document = self.db.query(Document).filter(
                        Document.file_path.like(f"%{relative_path}")
                    ).first()
                    
                    if not document:
                        # File is orphaned, remove it
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Removed orphaned file: {file_path}")
            
            logger.info(f"Cleaned up {cleaned_count} orphaned files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {e}")
            return 0
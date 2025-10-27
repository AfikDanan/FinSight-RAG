"""
Document processing service for managing SEC filing processing workflows.
Handles background task management, progress tracking, and status updates.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List
from enum import Enum
import json
import time

from app.services.document_storage import DocumentStorageService
from app.services.sec_edgar_scraper import SECEdgarScraper
from app.repositories.manager import RepositoryManager
from app.config import settings

logger = logging.getLogger(__name__)


class ProcessingPhase(str, Enum):
    """Processing phases for document workflow"""
    PENDING = "pending"
    SCRAPING = "scraping"
    DOWNLOADING = "downloading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    VECTORIZING = "vectorizing"
    COMPLETE = "complete"
    ERROR = "error"


class ProcessingStatus:
    """Processing status tracking"""
    
    def __init__(self, 
                 ticker: str,
                 time_range: int,
                 job_id: str = None):
        self.job_id = job_id or str(uuid.uuid4())
        self.ticker = ticker.upper()
        self.time_range = time_range
        self.phase = ProcessingPhase.PENDING
        self.progress = 0
        self.documents_found = 0
        self.documents_processed = 0
        self.chunks_created = 0
        self.chunks_vectorized = 0
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.estimated_time_remaining: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary"""
        return {
            "jobId": self.job_id,
            "ticker": self.ticker,
            "timeRange": self.time_range,
            "phase": self.phase.value,
            "progress": self.progress,
            "documentsFound": self.documents_found,
            "documentsProcessed": self.documents_processed,
            "chunksCreated": self.chunks_created,
            "chunksVectorized": self.chunks_vectorized,
            "startedAt": self.started_at.isoformat() + "Z",
            "completedAt": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "errorMessage": self.error_message,
            "estimatedTimeRemaining": self.estimated_time_remaining
        }


class ProcessingService:
    """
    Service for managing document processing workflows.
    Handles background task execution, progress tracking, and status management.
    """
    
    def __init__(self, repository_manager: RepositoryManager):
        self.repo_manager = repository_manager
        
        # In-memory status tracking (in production, this would use Redis)
        self._processing_jobs: Dict[str, ProcessingStatus] = {}
        self._job_tasks: Dict[str, asyncio.Task] = {}
        
        # Processing configuration
        self.supported_filing_types = ["10-K", "10-Q", "8-K", "20-F", "4"]
        
    async def start_processing(self, 
                             ticker: str, 
                             time_range: int,
                             filing_types: List[str] = None) -> ProcessingStatus:
        """
        Start document processing for a company.
        
        Args:
            ticker: Stock ticker symbol
            time_range: Number of years (1, 3, or 5)
            filing_types: Optional list of filing types to process
            
        Returns:
            ProcessingStatus object with job details
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if time_range not in [1, 3, 5]:
            raise ValueError("Time range must be 1, 3, or 5 years")
        
        if filing_types is None:
            filing_types = self.supported_filing_types
        
        # Check if processing is already in progress for this ticker
        existing_job = self._find_active_job(ticker)
        if existing_job:
            logger.info(f"Processing already in progress for {ticker}: {existing_job.job_id}")
            return existing_job
        
        # Create new processing status
        status = ProcessingStatus(ticker, time_range)
        self._processing_jobs[status.job_id] = status
        
        logger.info(f"Starting processing job {status.job_id} for {ticker} ({time_range} years)")
        
        # Start background processing task
        task = asyncio.create_task(
            self._process_company_documents(status, filing_types)
        )
        self._job_tasks[status.job_id] = task
        
        return status
    
    def get_processing_status(self, ticker: str = None, job_id: str = None) -> Optional[ProcessingStatus]:
        """
        Get processing status by ticker or job ID.
        
        Args:
            ticker: Stock ticker symbol
            job_id: Processing job ID
            
        Returns:
            ProcessingStatus or None if not found
        """
        if job_id:
            return self._processing_jobs.get(job_id)
        
        if ticker:
            # Find most recent job for ticker
            ticker = ticker.upper()
            matching_jobs = [
                status for status in self._processing_jobs.values()
                if status.ticker == ticker
            ]
            
            if matching_jobs:
                # Return most recent job
                return max(matching_jobs, key=lambda x: x.started_at)
        
        return None
    
    def cancel_processing(self, job_id: str) -> bool:
        """
        Cancel a processing job.
        
        Args:
            job_id: Processing job ID
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        status = self._processing_jobs.get(job_id)
        if not status:
            return False
        
        if status.phase in [ProcessingPhase.COMPLETE, ProcessingPhase.ERROR]:
            return False
        
        # Cancel the background task
        task = self._job_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        
        # Update status
        status.phase = ProcessingPhase.ERROR
        status.error_message = "Processing cancelled by user"
        status.completed_at = datetime.utcnow()
        
        logger.info(f"Cancelled processing job {job_id}")
        return True
    
    def get_all_jobs(self) -> List[ProcessingStatus]:
        """Get all processing jobs"""
        return list(self._processing_jobs.values())
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        jobs_to_remove = []
        
        for job_id, status in self._processing_jobs.items():
            if (status.phase in [ProcessingPhase.COMPLETE, ProcessingPhase.ERROR] and
                status.completed_at and status.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._processing_jobs[job_id]
            if job_id in self._job_tasks:
                del self._job_tasks[job_id]
        
        logger.info(f"Cleaned up {len(jobs_to_remove)} old processing jobs")
        return len(jobs_to_remove)
    
    def _find_active_job(self, ticker: str) -> Optional[ProcessingStatus]:
        """Find active processing job for ticker"""
        ticker = ticker.upper()
        for status in self._processing_jobs.values():
            if (status.ticker == ticker and 
                status.phase not in [ProcessingPhase.COMPLETE, ProcessingPhase.ERROR]):
                return status
        return None
    
    async def _process_company_documents(self, 
                                       status: ProcessingStatus,
                                       filing_types: List[str]):
        """
        Background task to process company documents.
        
        Args:
            status: ProcessingStatus object to update
            filing_types: List of filing types to process
        """
        try:
            logger.info(f"Starting document processing for {status.ticker}")
            
            # Create progress callback
            async def progress_callback(phase: str, progress: int, total: int = 100):
                await self._update_progress(status, phase, progress, total)
            
            # Get database session (using sync session for now)
            from app.database import SessionLocal
            
            with SessionLocal() as db:
                # Initialize document storage service
                storage_service = DocumentStorageService(
                    db=db,
                    storage_path=settings.document_storage_path
                )
                
                async with storage_service:
                    # Process company filings
                    result = await storage_service.process_company_filings(
                        ticker=status.ticker,
                        years=status.time_range,
                        filing_types=filing_types,
                        progress_callback=progress_callback
                    )
                    
                    # Update final status
                    if result["status"] == "completed":
                        status.phase = ProcessingPhase.COMPLETE
                        status.progress = 100
                        status.documents_found = result["filings_found"]
                        status.documents_processed = result["documents_stored"]
                        status.completed_at = datetime.utcnow()
                        
                        logger.info(f"Processing completed for {status.ticker}: {result}")
                    else:
                        status.phase = ProcessingPhase.ERROR
                        status.error_message = result.get("error", "Unknown error")
                        status.completed_at = datetime.utcnow()
                        
                        logger.error(f"Processing failed for {status.ticker}: {result}")
        
        except asyncio.CancelledError:
            logger.info(f"Processing cancelled for {status.ticker}")
            status.phase = ProcessingPhase.ERROR
            status.error_message = "Processing cancelled"
            status.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Processing error for {status.ticker}: {e}")
            status.phase = ProcessingPhase.ERROR
            status.error_message = str(e)
            status.completed_at = datetime.utcnow()
        
        finally:
            # Clean up task reference
            if status.job_id in self._job_tasks:
                del self._job_tasks[status.job_id]
    
    async def _update_progress(self, 
                             status: ProcessingStatus,
                             phase: str,
                             progress: int,
                             total: int = 100):
        """
        Update processing progress.
        
        Args:
            status: ProcessingStatus object
            phase: Current processing phase
            progress: Current progress value
            total: Total progress value
        """
        try:
            # Map phase names to ProcessingPhase enum
            phase_mapping = {
                "scraping": ProcessingPhase.SCRAPING,
                "downloading": ProcessingPhase.DOWNLOADING,
                "parsing": ProcessingPhase.PARSING,
                "chunking": ProcessingPhase.CHUNKING,
                "vectorizing": ProcessingPhase.VECTORIZING,
                "completed": ProcessingPhase.COMPLETE,
                "error": ProcessingPhase.ERROR
            }
            
            # Update status
            if phase in phase_mapping:
                status.phase = phase_mapping[phase]
            
            # Calculate progress percentage
            status.progress = min(int((progress / total) * 100), 100)
            
            # Estimate time remaining (simple linear estimation)
            if status.progress > 0 and status.progress < 100:
                elapsed_time = (datetime.utcnow() - status.started_at).total_seconds()
                estimated_total_time = elapsed_time / (status.progress / 100)
                status.estimated_time_remaining = int(estimated_total_time - elapsed_time)
            else:
                status.estimated_time_remaining = None
            
            logger.debug(f"Progress update for {status.ticker}: {phase} {status.progress}%")
            
        except Exception as e:
            logger.warning(f"Error updating progress: {e}")


# Global processing service instance (in production, this would be dependency injected)
_processing_service: Optional[ProcessingService] = None


def get_processing_service() -> ProcessingService:
    """Get or create processing service instance"""
    global _processing_service
    
    if _processing_service is None:
        from app.database import SessionLocal
        from app.repositories.manager import RepositoryManager
        
        # Create a dummy repository manager for now
        # In production, this would be properly dependency injected
        db = SessionLocal()
        repo_manager = RepositoryManager(db)
        _processing_service = ProcessingService(repo_manager)
    
    return _processing_service
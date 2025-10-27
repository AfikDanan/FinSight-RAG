from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from app.models.company import (
    CompanyResponse, 
    CompanySearchResponse, 
    CompanyDisambiguationResponse,
    CompanyDetailResponse,
    TickerValidationResponse
)
from pydantic import BaseModel
from app.services.company_service import CompanyService
from app.services.processing_service import get_processing_service, ProcessingService
import uuid

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/companies", tags=["companies"])

# Request/Response models for processing
class CompanyProcessingRequest(BaseModel):
    ticker: str
    timeRange: int  # 1, 3, or 5 years

class CompanyProcessingResponse(BaseModel):
    jobId: str
    ticker: str
    timeRange: int
    status: str
    message: str

# Dependencies
def get_company_service() -> CompanyService:
    return CompanyService()

def get_processing_service_dep() -> ProcessingService:
    return get_processing_service()


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    query: str = Query(..., description="Company name or ticker to search for", min_length=1),
    limit: int = Query(10, description="Maximum number of results to return", ge=1, le=50),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Search for companies by name or ticker symbol with fuzzy matching.
    
    - **query**: Company name or ticker symbol to search for
    - **limit**: Maximum number of results to return (1-50)
    
    Returns a list of matching companies with similarity-based ranking.
    """
    try:
        logger.info(f"Searching companies with query: '{query}', limit: {limit}")
        result = company_service.search_companies(query, limit)
        logger.info(f"Found {result.total_count} companies matching '{query}'")
        return result
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during company search")


@router.get("/disambiguate", response_model=CompanyDisambiguationResponse)
async def disambiguate_company(
    query: str = Query(..., description="Company query that needs disambiguation", min_length=1),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Handle disambiguation when a company query matches multiple companies.
    
    - **query**: Company name or ticker that may match multiple companies
    
    Returns structured disambiguation information with suggestions.
    """
    try:
        logger.info(f"Disambiguating company query: '{query}'")
        result = company_service.disambiguate_company_query(query)
        logger.info(f"Disambiguation result: {len(result.matches)} matches found")
        return result
    except Exception as e:
        logger.error(f"Error disambiguating company: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during disambiguation")


@router.get("/suggestions")
async def get_company_suggestions(
    q: str = Query(..., description="Partial query for autocomplete suggestions", min_length=2),
    limit: int = Query(5, description="Maximum number of suggestions", ge=1, le=10),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Get company suggestions for autocomplete functionality.
    
    - **q**: Partial company name or ticker for suggestions
    - **limit**: Maximum number of suggestions to return
    
    Returns a list of suggested company names and tickers.
    """
    try:
        logger.info(f"Getting suggestions for query: '{q}'")
        suggestions = company_service.get_company_suggestions(q, limit)
        return {"query": q, "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting suggestions")


@router.get("/{ticker}", response_model=CompanyDetailResponse)
async def get_company_by_ticker(
    ticker: str,
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Get detailed company information by ticker symbol.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    
    Returns detailed company information including metadata.
    """
    try:
        logger.info(f"Getting company details for ticker: '{ticker}'")
        
        # Validate ticker format
        is_valid, normalized_ticker = company_service.validate_ticker(ticker)
        if not is_valid:
            raise HTTPException(
                status_code=404, 
                detail=f"Company with ticker '{ticker}' not found"
            )
        
        # Get company data
        company = company_service.get_company_by_ticker(normalized_ticker)
        if not company:
            raise HTTPException(
                status_code=404, 
                detail=f"Company with ticker '{ticker}' not found"
            )
        
        # Convert to detailed response (for now, same as basic response)
        # In future tasks, this will include filing information
        detailed_response = CompanyDetailResponse(
            ticker=company.ticker,
            name=company.name,
            cik_str=company.cik_str,
            exchange=company.exchange,
            sector=company.sector,
            industry=company.industry,
            market_cap=company.market_cap
        )
        
        logger.info(f"Successfully retrieved company details for '{ticker}'")
        return detailed_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company by ticker: {e}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving company details")


@router.get("/validate/{ticker}", response_model=TickerValidationResponse)
async def validate_ticker_get(
    ticker: str,
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Validate if a ticker symbol exists in the system (GET endpoint).
    
    - **ticker**: Stock ticker symbol to validate
    
    Returns validation result with company name and suggestions if invalid.
    """
    try:
        logger.info(f"Validating ticker: '{ticker}'")
        is_valid, normalized_ticker = company_service.validate_ticker(ticker)
        
        if is_valid:
            # Get company details for valid ticker
            company = company_service.get_company_by_ticker(normalized_ticker)
            result = {
                "ticker": normalized_ticker,
                "isValid": True,
                "companyName": company.name if company else None,
                "suggestions": []
            }
        else:
            # Get suggestions for invalid ticker
            search_result = company_service.search_companies(ticker, limit=3)
            suggestions = [comp.ticker for comp in search_result.companies]
            
            result = {
                "ticker": ticker,
                "isValid": False,
                "companyName": None,
                "suggestions": suggestions
            }
        
        logger.info(f"Ticker validation result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating ticker: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during ticker validation")


@router.post("/validate")
async def validate_ticker(
    ticker: str = Query(..., description="Ticker symbol to validate"),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Validate if a ticker symbol exists in the system.
    
    - **ticker**: Stock ticker symbol to validate
    
    Returns validation result and normalized ticker if valid.
    """
    try:
        logger.info(f"Validating ticker: '{ticker}'")
        is_valid, normalized_ticker = company_service.validate_ticker(ticker)
        
        result = {
            "ticker": ticker,
            "is_valid": is_valid,
            "normalized_ticker": normalized_ticker,
            "message": "Valid ticker" if is_valid else f"Ticker '{ticker}' not found"
        }
        
        logger.info(f"Ticker validation result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error validating ticker: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during ticker validation")


@router.post("/process", response_model=CompanyProcessingResponse)
async def start_company_processing(
    request: CompanyProcessingRequest,
    company_service: CompanyService = Depends(get_company_service),
    processing_service: ProcessingService = Depends(get_processing_service_dep)
):
    """
    Start processing SEC filings for a company.
    
    - **ticker**: Stock ticker symbol to process
    - **timeRange**: Number of years of filings to process (1, 3, or 5)
    
    Returns a job ID for tracking the processing status.
    """
    try:
        logger.info(f"Starting processing for ticker: '{request.ticker}', timeRange: {request.timeRange}")
        
        # Validate ticker
        is_valid, normalized_ticker = company_service.validate_ticker(request.ticker)
        if not is_valid:
            raise HTTPException(
                status_code=404, 
                detail=f"Company with ticker '{request.ticker}' not found"
            )
        
        # Validate time range
        if request.timeRange not in [1, 3, 5]:
            raise HTTPException(
                status_code=400,
                detail="Time range must be 1, 3, or 5 years"
            )
        
        # Start processing
        status = await processing_service.start_processing(
            ticker=normalized_ticker,
            time_range=request.timeRange
        )
        
        response = CompanyProcessingResponse(
            jobId=status.job_id,
            ticker=status.ticker,
            timeRange=status.time_range,
            status=status.phase.value,
            message=f"Processing started for {status.ticker} ({status.time_range} years)"
        )
        
        logger.info(f"Processing job {status.job_id} started for {normalized_ticker}")
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error starting processing")


@router.get("/{ticker}/status")
async def get_processing_status(
    ticker: str,
    company_service: CompanyService = Depends(get_company_service),
    processing_service: ProcessingService = Depends(get_processing_service_dep)
):
    """
    Get the processing status for a company's SEC filings.
    
    - **ticker**: Stock ticker symbol
    
    Returns the current processing status and progress.
    """
    try:
        logger.info(f"Getting processing status for ticker: '{ticker}'")
        
        # Validate ticker
        is_valid, normalized_ticker = company_service.validate_ticker(ticker)
        if not is_valid:
            raise HTTPException(
                status_code=404, 
                detail=f"Company with ticker '{ticker}' not found"
            )
        
        # Get processing status
        status = processing_service.get_processing_status(ticker=normalized_ticker)
        
        if not status:
            # No processing found for this ticker
            return {
                "ticker": normalized_ticker,
                "phase": "not_started",
                "progress": 0,
                "documentsFound": 0,
                "documentsProcessed": 0,
                "chunksCreated": 0,
                "chunksVectorized": 0,
                "message": f"No processing found for {normalized_ticker}"
            }
        
        result = status.to_dict()
        logger.info(f"Processing status for {normalized_ticker}: {status.phase}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting processing status")


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    processing_service: ProcessingService = Depends(get_processing_service_dep)
):
    """
    Get processing status by job ID.
    
    - **job_id**: Processing job ID
    
    Returns the current processing status and progress.
    """
    try:
        logger.info(f"Getting job status for job ID: '{job_id}'")
        
        status = processing_service.get_processing_status(job_id=job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Processing job '{job_id}' not found"
            )
        
        result = status.to_dict()
        logger.info(f"Job status for {job_id}: {status.phase}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting job status")


@router.post("/jobs/{job_id}/cancel")
async def cancel_processing_job(
    job_id: str,
    processing_service: ProcessingService = Depends(get_processing_service_dep)
):
    """
    Cancel a processing job.
    
    - **job_id**: Processing job ID to cancel
    
    Returns cancellation result.
    """
    try:
        logger.info(f"Cancelling processing job: '{job_id}'")
        
        success = processing_service.cancel_processing(job_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Processing job '{job_id}' not found or already completed"
            )
        
        result = {
            "jobId": job_id,
            "status": "cancelled",
            "message": f"Processing job {job_id} has been cancelled"
        }
        
        logger.info(f"Successfully cancelled job {job_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error cancelling job")


@router.get("/jobs")
async def list_processing_jobs(
    processing_service: ProcessingService = Depends(get_processing_service_dep)
):
    """
    List all processing jobs.
    
    Returns a list of all processing jobs with their current status.
    """
    try:
        logger.info("Listing all processing jobs")
        
        jobs = processing_service.get_all_jobs()
        
        result = {
            "jobs": [job.to_dict() for job in jobs],
            "total": len(jobs)
        }
        
        logger.info(f"Found {len(jobs)} processing jobs")
        return result
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error listing jobs")
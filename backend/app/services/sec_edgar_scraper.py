"""
SEC EDGAR scraper service for retrieving company filings.
Implements proper rate limiting and respectful scraping practices.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import httpx
import json
from urllib.parse import urljoin
import time
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Filing:
    """Data class representing a SEC filing"""
    accession_number: str
    filing_type: str
    filing_date: datetime
    period_end: Optional[datetime]
    document_url: str
    ticker: str
    company_name: str
    cik: str
    file_size: Optional[int] = None
    document_format: str = "HTML"


class RateLimiter:
    """Rate limiter for SEC EDGAR API compliance"""
    
    def __init__(self, requests_per_second: float = 10.0):
        """
        Initialize rate limiter.
        SEC allows 10 requests per second for non-commercial use.
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    async def wait(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()


class SECEdgarScraper:
    """
    SEC EDGAR scraper with proper rate limiting and error handling.
    Follows SEC.gov guidelines for automated access.
    """
    
    BASE_URL = "https://www.sec.gov"
    COMPANY_TICKERS_URL = f"{BASE_URL}/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    
    # Supported filing types
    SUPPORTED_FILING_TYPES = {
        "10-K": "Annual Report",
        "10-Q": "Quarterly Report", 
        "8-K": "Current Report",
        "20-F": "Annual Report (Foreign)",
        "4": "Statement of Changes in Beneficial Ownership"
    }
    

    
    def __init__(self, user_agent: str = None):
        """
        Initialize SEC EDGAR scraper.
        
        Args:
            user_agent: Custom user agent string (required by SEC)
        """
        self.rate_limiter = RateLimiter(requests_per_second=9.0)  # Conservative rate
        self.user_agent = user_agent or f"{settings.app_name} edgar-scraper@example.com"
        
        # HTTP client with proper headers
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Encoding": "gzip, deflate"
            },
            timeout=30.0,
            follow_redirects=True
        )
        
        # Cache for company CIK lookups
        self._cik_cache: Dict[str, str] = {}
        self._company_tickers: Optional[Dict] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def _make_request(self, url: str, params: Dict = None) -> httpx.Response:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            url: Request URL
            params: Query parameters
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: For HTTP errors
        """
        await self.rate_limiter.wait()
        
        try:
            logger.debug(f"Making request to: {url}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise
    
    async def load_company_tickers(self) -> Dict:
        """
        Load company tickers mapping from SEC.
        
        Returns:
            Dictionary mapping CIK to company info
        """
        if self._company_tickers is not None:
            return self._company_tickers
        
        try:
            response = await self._make_request(self.COMPANY_TICKERS_URL)
            self._company_tickers = response.json()
            logger.info(f"Loaded {len(self._company_tickers)} company tickers")
            return self._company_tickers
        except Exception as e:
            logger.error(f"Failed to load company tickers: {e}")
            raise
    
    async def get_company_cik(self, ticker: str) -> Optional[str]:
        """
        Get company CIK (Central Index Key) from ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CIK string with leading zeros (10 digits), or None if not found
        """
        ticker = ticker.upper().strip()
        
        # Check cache first
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        
        # Load company tickers if not already loaded
        company_tickers = await self.load_company_tickers()
        
        # Search for ticker in the data
        for index, company_info in company_tickers.items():
            if company_info.get("ticker", "").upper() == ticker:
                # Get the actual CIK from cik_str field and format with leading zeros (10 digits)
                actual_cik = company_info.get("cik_str")
                if actual_cik is not None:
                    formatted_cik = str(actual_cik).zfill(10)
                    self._cik_cache[ticker] = formatted_cik
                    logger.debug(f"Found CIK {formatted_cik} for ticker {ticker}")
                    return formatted_cik
        
        logger.warning(f"CIK not found for ticker: {ticker}")
        return None
    
    async def get_company_info(self, ticker: str) -> Optional[Dict]:
        """
        Get company information from ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with company info or None if not found
        """
        ticker = ticker.upper().strip()
        
        # Load company tickers if not already loaded
        company_tickers = await self.load_company_tickers()
        
        # Search for ticker in the data
        for index, company_info in company_tickers.items():
            if company_info.get("ticker", "").upper() == ticker:
                # Get the actual CIK from cik_str field and format with leading zeros (10 digits)
                actual_cik = company_info.get("cik_str")
                if actual_cik is not None:
                    return {
                        "cik": str(actual_cik).zfill(10),
                        "ticker": company_info.get("ticker"),
                        "title": company_info.get("title", ""),
                        "exchange": company_info.get("exchange", "")
                    }
        
        return None
    
    async def get_company_submissions(self, cik: str) -> Dict:
        """
        Get company submissions data from SEC.
        
        Args:
            cik: Company CIK (Central Index Key)
            
        Returns:
            Company submissions data
        """
        # Ensure CIK has proper format (10 digits with leading zeros)
        cik_formatted = str(cik).zfill(10)
        url = f"{self.SUBMISSIONS_URL}/CIK{cik_formatted}.json"
        
        try:
            response = await self._make_request(url)
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"No submissions found for CIK: {cik}")
                return {}
            raise
    
    def _filter_filings_by_date_and_type(self, 
                                       submissions: Dict, 
                                       filing_types: List[str],
                                       start_date: datetime,
                                       end_date: datetime) -> List[Dict]:
        """
        Filter filings by date range and filing types.
        
        Args:
            submissions: Company submissions data from SEC
            filing_types: List of filing types to include
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of filtered filing records
        """
        filings = []
        recent_filings = submissions.get("filings", {}).get("recent", {})
        
        if not recent_filings:
            return filings
        
        # Get arrays from recent filings
        accession_numbers = recent_filings.get("accessionNumber", [])
        filing_dates = recent_filings.get("filingDate", [])
        forms = recent_filings.get("form", [])
        primary_documents = recent_filings.get("primaryDocument", [])
        
        # Process each filing
        for i in range(len(accession_numbers)):
            try:
                form = forms[i] if i < len(forms) else ""
                filing_date_str = filing_dates[i] if i < len(filing_dates) else ""
                
                # Check if filing type matches
                if form not in filing_types:
                    continue
                
                # Parse and check filing date
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
                if not (start_date <= filing_date <= end_date):
                    continue
                
                # Build filing record
                filing = {
                    "accessionNumber": accession_numbers[i],
                    "filingDate": filing_date_str,
                    "form": form,
                    "primaryDocument": primary_documents[i] if i < len(primary_documents) else "",
                    "index": i
                }
                
                filings.append(filing)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Error processing filing at index {i}: {e}")
                continue
        
        return filings
    
    async def scrape_filings(self, 
                           ticker: str, 
                           years: int,
                           filing_types: List[str] = None) -> List[Filing]:
        """
        Scrape SEC filings for a company within specified time range.
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years back to scrape (1, 3, or 5)
            filing_types: List of filing types to scrape (defaults to all supported)
            
        Returns:
            List of Filing objects
            
        Raises:
            ValueError: If ticker not found or invalid parameters
        """
        if filing_types is None:
            filing_types = list(self.SUPPORTED_FILING_TYPES.keys())
        
        # Validate parameters
        if years not in [1, 3, 5]:
            raise ValueError("Years must be 1, 3, or 5")
        
        # Get company CIK
        cik = await self.get_company_cik(ticker)
        if not cik:
            raise ValueError(f"Company not found for ticker: {ticker}")
        
        # Get company info
        company_info = await self.get_company_info(ticker)
        if not company_info:
            raise ValueError(f"Company info not found for ticker: {ticker}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        logger.info(f"Scraping {ticker} filings from {start_date.date()} to {end_date.date()}")
        
        # Get company submissions
        submissions = await self.get_company_submissions(cik)
        if not submissions:
            logger.warning(f"No submissions found for {ticker}")
            return []
        
        # Filter filings by date and type
        filtered_filings = self._filter_filings_by_date_and_type(
            submissions, filing_types, start_date, end_date
        )
        
        # Convert to Filing objects
        filings = []
        for filing_data in filtered_filings:
            try:
                filing = Filing(
                    accession_number=filing_data["accessionNumber"],
                    filing_type=filing_data["form"],
                    filing_date=datetime.strptime(filing_data["filingDate"], "%Y-%m-%d"),
                    period_end=None,  # Will be extracted from document if available
                    document_url=self._build_document_url(
                        cik, 
                        filing_data["accessionNumber"], 
                        filing_data["primaryDocument"]
                    ),
                    ticker=ticker,
                    company_name=company_info["title"],
                    cik=cik,
                    document_format="HTML"
                )
                filings.append(filing)
                
            except Exception as e:
                logger.warning(f"Error creating Filing object: {e}")
                continue
        
        logger.info(f"Found {len(filings)} filings for {ticker}")
        return filings
    
    def _build_document_url(self, cik: str, accession_number: str, primary_document: str) -> str:
        """
        Build document URL for SEC filing.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            primary_document: Primary document filename
            
        Returns:
            Full URL to document
        """
        # Remove dashes from accession number for URL
        accession_clean = accession_number.replace("-", "")
        
        # Build URL path
        url_path = f"/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary_document}"
        return urljoin(self.BASE_URL, url_path)
    
    async def validate_ticker(self, ticker: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate ticker symbol and provide suggestions if invalid.
        
        Args:
            ticker: Stock ticker symbol to validate
            
        Returns:
            Tuple of (is_valid, company_name, suggestions)
        """
        ticker = ticker.upper().strip()
        
        # Try exact match first
        company_info = await self.get_company_info(ticker)
        if company_info:
            return True, company_info["title"], []
        
        # If not found, provide suggestions
        suggestions = await self._get_ticker_suggestions(ticker)
        return False, None, suggestions
    
    async def _get_ticker_suggestions(self, ticker: str, max_suggestions: int = 5) -> List[str]:
        """
        Get ticker suggestions for invalid/partial ticker.
        
        Args:
            ticker: Partial or invalid ticker
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggested tickers
        """
        ticker = ticker.upper().strip()
        company_tickers = await self.load_company_tickers()
        
        suggestions = []
        
        # Look for partial matches
        for cik_str, company_info in company_tickers.items():
            company_ticker = company_info.get("ticker", "").upper()
            company_name = company_info.get("title", "").upper()
            
            # Check if ticker starts with input or company name contains input
            if (company_ticker.startswith(ticker) or 
                ticker in company_name or 
                ticker in company_ticker):
                suggestions.append(company_ticker)
                
                if len(suggestions) >= max_suggestions:
                    break
        
        return suggestions[:max_suggestions]
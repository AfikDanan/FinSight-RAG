from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CompanyBase(BaseModel):
    """Base company model with common fields"""
    ticker: str = Field(..., description="Stock ticker symbol", max_length=10)
    name: str = Field(..., description="Company name", max_length=255)
    cik_str: int = Field(..., description="SEC Central Index Key")


class Company(CompanyBase):
    """Internal company model with all fields"""
    exchange: Optional[str] = Field(None, description="Stock exchange", max_length=50)
    sector: Optional[str] = Field(None, description="Business sector", max_length=100)
    industry: Optional[str] = Field(None, description="Industry classification", max_length=100)
    market_cap: Optional[float] = Field(None, description="Market capitalization in USD")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record update timestamp")


class CompanyResponse(CompanyBase):
    """API response model for company data"""
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    
    class Config:
        from_attributes = True


class CompanySearchResponse(BaseModel):
    """Response model for company search results"""
    companies: List[CompanyResponse]
    total_count: int
    query: str
    suggestions: Optional[List[str]] = None


class CompanyDisambiguationResponse(BaseModel):
    """Response model for company disambiguation"""
    query: str
    matches: List[CompanyResponse]
    exact_match: Optional[CompanyResponse] = None
    suggestions: List[str] = []
    message: str = "Multiple companies found. Please select one:"


class CompanyDetailResponse(CompanyResponse):
    """Detailed company response with additional metadata"""
    last_filing_date: Optional[datetime] = None
    total_filings: Optional[int] = None
    available_documents: Optional[List[str]] = None


class TickerValidationResponse(BaseModel):
    """Response model for ticker validation"""
    ticker: str = Field(..., description="The ticker symbol that was validated")
    isValid: bool = Field(..., description="Whether the ticker is valid")
    companyName: Optional[str] = Field(None, description="Company name if ticker is valid")
    suggestions: List[str] = Field(default_factory=list, description="Suggested tickers if invalid")
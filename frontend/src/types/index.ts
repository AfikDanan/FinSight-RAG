export interface Company {
    ticker: string
    name: string
    exchange: string
    sector: string
    industry: string
    marketCap?: number
}

export interface Message {
    id: string
    content: string
    type: 'user' | 'assistant'
    timestamp: Date
    citations?: Citation[]
    isLoading?: boolean
}

export interface Citation {
    id: string
    documentTitle: string
    section: string
    pageNumber?: number
    excerpt: string
    confidence: number
    url?: string
}

export interface QueryResponse {
    answer: string
    citations: Citation[]
    relatedQuestions: string[]
    processingTime: number
}

export interface CompanySearchResponse {
    companies: Company[]
    suggestions?: Company[]
}

export interface CompanyProcessingRequest {
    ticker: string
    timeRange: 1 | 3 | 5
}

export interface ProcessingStatus {
    ticker: string
    phase: 'scraping' | 'parsing' | 'chunking' | 'vectorizing' | 'complete' | 'error'
    progress: number
    documentsFound: number
    documentsProcessed: number
    chunksCreated: number
    chunksVectorized: number
    estimatedTimeRemaining?: number
    error?: string
    startedAt: Date
    completedAt?: Date
}

export interface CompanyContext {
    ticker: string
    name: string
    processingStatus: ProcessingStatus
    documentsAvailable: number
    timeRangeProcessed: number
}

export interface TickerValidationResponse {
    ticker: string
    isValid: boolean
    companyName?: string
    suggestions: string[]
}
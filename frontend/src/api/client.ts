import axios from 'axios'
import { Company, QueryResponse, CompanyProcessingRequest, ProcessingStatus, TickerValidationResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor for adding auth tokens if needed
apiClient.interceptors.request.use(
    (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Handle unauthorized access
            localStorage.removeItem('auth_token')
            // Could redirect to login page here
        }
        return Promise.reject(error)
    }
)

export const companyAPI = {
    searchCompanies: async (query: string): Promise<Company[]> => {
        const response = await apiClient.get(`/companies/search`, {
            params: { query }
        })
        return response.data
    },

    getCompanyDetails: async (ticker: string): Promise<Company> => {
        const response = await apiClient.get(`/companies/${ticker}`)
        return response.data
    },

    validateTicker: async (ticker: string): Promise<TickerValidationResponse> => {
        const response = await apiClient.get(`/companies/validate/${ticker}`)
        return response.data
    },

    startProcessing: async (request: CompanyProcessingRequest): Promise<{ jobId: string }> => {
        const response = await apiClient.post('/companies/process', request)
        return response.data
    },

    getProcessingStatus: async (ticker: string): Promise<ProcessingStatus & { companyName?: string; timeRangeProcessed?: number }> => {
        const response = await apiClient.get(`/companies/${ticker}/status`)
        return response.data
    },

    cancelProcessing: async (ticker: string): Promise<void> => {
        await apiClient.post(`/companies/${ticker}/cancel`)
    }
}

export const chatAPI = {
    sendQuery: async (query: string, sessionId?: string): Promise<QueryResponse> => {
        const response = await apiClient.post('/chat/query', {
            query,
            session_id: sessionId
        })
        return response.data
    }
}
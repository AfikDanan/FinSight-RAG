import { Company } from '../types'

export const mockCompanies: Company[] = [
    {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        exchange: 'NASDAQ',
        sector: 'Technology',
        industry: 'Consumer Electronics',
        marketCap: 3000000000000, // 3T
    },
    {
        ticker: 'MSFT',
        name: 'Microsoft Corporation',
        exchange: 'NASDAQ',
        sector: 'Technology',
        industry: 'Software',
        marketCap: 2800000000000, // 2.8T
    },
    {
        ticker: 'GOOGL',
        name: 'Alphabet Inc.',
        exchange: 'NASDAQ',
        sector: 'Technology',
        industry: 'Internet Services',
        marketCap: 1700000000000, // 1.7T
    },
    {
        ticker: 'TSLA',
        name: 'Tesla, Inc.',
        exchange: 'NASDAQ',
        sector: 'Consumer Discretionary',
        industry: 'Electric Vehicles',
        marketCap: 800000000000, // 800B
    },
]

export const mockCompanySearchResponse = {
    companies: mockCompanies,
    suggestions: []
}
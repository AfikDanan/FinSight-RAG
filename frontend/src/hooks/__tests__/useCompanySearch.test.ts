import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCompanySearch } from '../useCompanySearch'
import { mockCompanies } from '../../test/mockData'
import * as companyAPI from '../../api/client'
import React from 'react'

// Mock the API
vi.mock('../../api/client', () => ({
    companyAPI: {
        searchCompanies: vi.fn(),
    },
}))

// Mock the debounce hook to avoid timing issues in tests
vi.mock('../useDebounce', () => ({
    useDebounce: (value: string) => value,
}))

describe('useCompanySearch', () => {
    const mockSearchCompanies = vi.mocked(companyAPI.companyAPI.searchCompanies)

    const createWrapper = () => {
        const queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                },
            },
        })

        const Wrapper = ({ children }: { children: React.ReactNode }) => (
            <QueryClientProvider client= { queryClient } >
            { children }
            </QueryClientProvider>
        )

return Wrapper
    }

beforeEach(() => {
    vi.clearAllMocks()
})

it('returns initial state correctly', () => {
    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    expect(result.current.companies).toEqual([])
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
    expect(result.current.searchQuery).toBe('')
})

it('searches companies when query is provided', async () => {
    mockSearchCompanies.mockResolvedValue(mockCompanies)

    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    result.current.searchCompanies('Apple')

    await waitFor(() => {
        expect(result.current.companies).toEqual(mockCompanies)
    })

    expect(mockSearchCompanies).toHaveBeenCalledWith('Apple')
})

it('does not search for queries shorter than 2 characters', () => {
    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    result.current.searchCompanies('A')

    expect(mockSearchCompanies).not.toHaveBeenCalled()
})

it('handles search errors', async () => {
    const error = new Error('API Error')
    mockSearchCompanies.mockRejectedValue(error)

    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    result.current.searchCompanies('Apple')

    await waitFor(() => {
        expect(result.current.error).toBeTruthy()
    })
})

it('clears search query and results', () => {
    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    result.current.searchCompanies('Apple')
    expect(result.current.searchQuery).toBe('Apple')

    result.current.clearSearch()
    expect(result.current.searchQuery).toBe('')
})

it('shows loading state during search', async () => {
    mockSearchCompanies.mockImplementation(() => new Promise(() => { })) // Never resolves

    const { result } = renderHook(() => useCompanySearch(), {
        wrapper: createWrapper(),
    })

    result.current.searchCompanies('Apple')

    await waitFor(() => {
        expect(result.current.isLoading).toBe(true)
    })
})
})
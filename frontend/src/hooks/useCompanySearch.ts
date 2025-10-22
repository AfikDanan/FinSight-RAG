import { useQuery } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { companyAPI } from '../api/client'
import { Company } from '../types'
import { useDebounce } from './useDebounce'

export const useCompanySearch = () => {
    const [searchQuery, setSearchQuery] = useState('')
    const debouncedQuery = useDebounce(searchQuery, 300)

    const {
        data: companies = [],
        isLoading,
        error,
        refetch
    } = useQuery({
        queryKey: ['companies', 'search', debouncedQuery],
        queryFn: () => companyAPI.searchCompanies(debouncedQuery),
        enabled: debouncedQuery.length >= 2,
        staleTime: 5 * 60 * 1000, // 5 minutes
    })

    const searchCompanies = useCallback((query: string) => {
        setSearchQuery(query)
    }, [])

    const clearSearch = useCallback(() => {
        setSearchQuery('')
    }, [])

    return {
        companies,
        isLoading,
        error,
        searchQuery,
        searchCompanies,
        clearSearch,
        refetch
    }
}
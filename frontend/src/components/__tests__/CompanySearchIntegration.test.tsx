import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../test/utils'
import { CompanySelector } from '../CompanySelector'
import { CompanyDisambiguation } from '../CompanyDisambiguation'
import { mockCompanies } from '../../test/mockData'
import * as companyAPI from '../../api/client'
import { useAppStore } from '../../store/useAppStore'

// Mock the API
vi.mock('../../api/client', () => ({
    companyAPI: {
        searchCompanies: vi.fn(),
    },
}))

// Mock the store
const mockSelectCompany = vi.fn()
const mockRemoveSelectedCompany = vi.fn()

vi.mock('../../store/useAppStore', () => ({
    useAppStore: vi.fn(),
}))

describe('Company Search Integration', () => {
    const mockSearchCompanies = vi.mocked(companyAPI.companyAPI.searchCompanies)
    const mockUseAppStore = vi.mocked(useAppStore)
    const user = userEvent.setup()

    beforeEach(() => {
        vi.clearAllMocks()
        mockUseAppStore.mockReturnValue({
            selectedCompanies: [],
            selectCompany: mockSelectCompany,
            removeSelectedCompany: mockRemoveSelectedCompany,
        })
    })

    it('completes full search workflow with single result', async () => {
        // Mock API to return single company
        mockSearchCompanies.mockResolvedValue([mockCompanies[0]]) // Apple only

        render(<CompanySelector placeholder="Search companies..." />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        // Wait for search results
        await waitFor(() => {
            expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        })

        // Select the company
        await user.click(screen.getByText('Apple Inc.'))

        // Verify API was called correctly
        expect(mockSearchCompanies).toHaveBeenCalledWith('Apple')
        expect(mockSelectCompany).toHaveBeenCalledWith(mockCompanies[0])
    })

    it('handles disambiguation workflow with multiple results', async () => {
        // Mock API to return multiple companies
        const multipleResults = mockCompanies.slice(0, 3) // Apple, Microsoft, Google
        mockSearchCompanies.mockResolvedValue(multipleResults)

        const onCompanySelect = vi.fn()
        render(<CompanySelector onCompanySelect={onCompanySelect} />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'tech')

        // Wait for search results - should show multiple options
        await waitFor(() => {
            expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
            expect(screen.getByText('Microsoft Corporation')).toBeInTheDocument()
            expect(screen.getByText('Alphabet Inc.')).toBeInTheDocument()
        })

        // Select one of the companies
        await user.click(screen.getByText('Microsoft Corporation'))

        expect(onCompanySelect).toHaveBeenCalledWith(mockCompanies[1])
    })

    it('integrates with disambiguation dialog for ambiguous queries', async () => {
        const ambiguousResults = [
            {
                ticker: 'AAPL',
                name: 'Apple Inc.',
                exchange: 'NASDAQ',
                sector: 'Technology',
                industry: 'Consumer Electronics',
            },
            {
                ticker: 'APLE',
                name: 'Apple Hospitality REIT',
                exchange: 'NYSE',
                sector: 'Real Estate',
                industry: 'REITs',
            },
        ]

        const onSelect = vi.fn()
        const onClose = vi.fn()

        render(
            <CompanyDisambiguation
                open={true}
                companies={ambiguousResults}
                searchQuery="apple"
                onSelect={onSelect}
                onClose={onClose}
            />
        )

        // Verify disambiguation dialog shows both options
        expect(screen.getByText('Multiple companies found for "apple"')).toBeInTheDocument()
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        expect(screen.getByText('Apple Hospitality REIT')).toBeInTheDocument()

        // Select the first option
        await user.click(screen.getByText('Apple Inc.'))

        expect(onSelect).toHaveBeenCalledWith(ambiguousResults[0])
        expect(onClose).toHaveBeenCalled()
    })

    it('handles API errors gracefully during search', async () => {
        mockSearchCompanies.mockRejectedValue(new Error('Network error'))

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByText('Failed to search companies. Please try again.')).toBeInTheDocument()
        })

        // Verify error doesn't break the component
        expect(input).toBeInTheDocument()
        expect(input).toHaveValue('Apple')
    })

    it('validates minimum search length requirement', async () => {
        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'A')

        // Open dropdown to see message
        await user.click(input)

        await waitFor(() => {
            expect(screen.getByText('Type at least 2 characters to search')).toBeInTheDocument()
        })

        // Verify API is not called for short queries
        expect(mockSearchCompanies).not.toHaveBeenCalled()
    })

    it('shows appropriate message when no companies are found', async () => {
        mockSearchCompanies.mockResolvedValue([])

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'NonExistentCompany')

        // Wait for search to be triggered
        await waitFor(() => {
            expect(mockSearchCompanies).toHaveBeenCalledWith('NonExistentCompany')
        })

        // Open dropdown to see message
        await user.click(input)

        await waitFor(() => {
            expect(screen.getByText('No companies found')).toBeInTheDocument()
        })
    })

    it('supports multiple company selection workflow', async () => {
        mockSearchCompanies.mockResolvedValue([mockCompanies[0]])

        // Mock store to show selected companies
        mockUseAppStore.mockReturnValue({
            selectedCompanies: [mockCompanies[1]], // Microsoft already selected
            selectCompany: mockSelectCompany,
            removeSelectedCompany: mockRemoveSelectedCompany,
        })

        render(<CompanySelector multiple={true} />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Apple Inc.'))

        // Verify new company is added to selection
        expect(mockSelectCompany).toHaveBeenCalledWith(mockCompanies[0])
    })

    it('handles debounced search correctly', async () => {
        mockSearchCompanies.mockResolvedValue(mockCompanies)

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')

        // Type quickly to test debouncing
        await user.type(input, 'Ap')
        await user.type(input, 'ple')

        // Wait for debounced search
        await waitFor(() => {
            expect(mockSearchCompanies).toHaveBeenCalledWith('Apple')
        }, { timeout: 1000 })

        // Should only be called once due to debouncing
        expect(mockSearchCompanies).toHaveBeenCalledTimes(1)
    })
})
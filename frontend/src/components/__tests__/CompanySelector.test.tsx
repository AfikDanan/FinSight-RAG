import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../test/utils'
import { CompanySelector } from '../CompanySelector'
import { mockCompanies } from '../../test/mockData'
import * as companyAPI from '../../api/client'

// Mock the API
vi.mock('../../api/client', () => ({
    companyAPI: {
        searchCompanies: vi.fn(),
    },
}))

// Mock the store
vi.mock('../../store/useAppStore', () => ({
    useAppStore: () => ({
        selectedCompanies: [],
        selectCompany: vi.fn(),
        removeSelectedCompany: vi.fn(),
    }),
}))

describe('CompanySelector', () => {
    const mockSearchCompanies = vi.mocked(companyAPI.companyAPI.searchCompanies)
    const user = userEvent.setup()

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders with placeholder text', () => {
        render(<CompanySelector placeholder="Search companies..." />)

        expect(screen.getByPlaceholderText('Search companies...')).toBeInTheDocument()
    })

    it('shows loading state when searching', async () => {
        mockSearchCompanies.mockImplementation(() => new Promise(() => { })) // Never resolves

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByRole('progressbar')).toBeInTheDocument()
        })
    })

    it('displays search results', async () => {
        mockSearchCompanies.mockResolvedValue(mockCompanies)

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
            expect(screen.getByText('AAPL • NASDAQ • Technology')).toBeInTheDocument()
        })
    })

    it('calls onCompanySelect when a company is selected', async () => {
        const onCompanySelect = vi.fn()
        mockSearchCompanies.mockResolvedValue(mockCompanies)

        render(<CompanySelector onCompanySelect={onCompanySelect} />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Apple Inc.'))

        expect(onCompanySelect).toHaveBeenCalledWith(mockCompanies[0])
    })

    it('shows error message when search fails', async () => {
        mockSearchCompanies.mockRejectedValue(new Error('API Error'))

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'Apple')

        await waitFor(() => {
            expect(screen.getByText('Failed to search companies. Please try again.')).toBeInTheDocument()
        })
    })

    it('shows minimum character message for short queries', async () => {
        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'A')

        // Click to open dropdown
        fireEvent.mouseDown(input)

        await waitFor(() => {
            expect(screen.getByText('Type at least 2 characters to search')).toBeInTheDocument()
        })
    })

    it('shows no options message when no results found', async () => {
        mockSearchCompanies.mockResolvedValue([])

        render(<CompanySelector />)

        const input = screen.getByRole('combobox')
        await user.type(input, 'NonExistentCompany')

        // Click to open dropdown
        fireEvent.mouseDown(input)

        await waitFor(() => {
            expect(screen.getByText('No companies found')).toBeInTheDocument()
        })
    })
})
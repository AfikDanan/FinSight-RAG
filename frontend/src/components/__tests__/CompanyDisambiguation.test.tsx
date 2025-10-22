import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../test/utils'
import { CompanyDisambiguation } from '../CompanyDisambiguation'
import { mockCompanies } from '../../test/mockData'

describe('CompanyDisambiguation', () => {
    const user = userEvent.setup()
    const mockProps = {
        open: true,
        companies: mockCompanies.slice(0, 2), // Apple and Microsoft
        searchQuery: 'tech',
        onSelect: vi.fn(),
        onClose: vi.fn(),
    }

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders dialog with search query', () => {
        render(<CompanyDisambiguation {...mockProps} />)

        expect(screen.getByText('Multiple companies found for "tech"')).toBeInTheDocument()
        expect(screen.getByText('Please select the company you\'re looking for:')).toBeInTheDocument()
    })

    it('displays list of companies', () => {
        render(<CompanyDisambiguation {...mockProps} />)

        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        expect(screen.getByText('AAPL • NASDAQ')).toBeInTheDocument()
        expect(screen.getByText('Technology • Consumer Electronics')).toBeInTheDocument()

        expect(screen.getByText('Microsoft Corporation')).toBeInTheDocument()
        expect(screen.getByText('MSFT • NASDAQ')).toBeInTheDocument()
        expect(screen.getByText('Technology • Software')).toBeInTheDocument()
    })

    it('calls onSelect when a company is clicked', async () => {
        render(<CompanyDisambiguation {...mockProps} />)

        await user.click(screen.getByText('Apple Inc.'))

        expect(mockProps.onSelect).toHaveBeenCalledWith(mockCompanies[0])
        expect(mockProps.onClose).toHaveBeenCalled()
    })

    it('calls onClose when cancel button is clicked', async () => {
        render(<CompanyDisambiguation {...mockProps} />)

        await user.click(screen.getByText('Cancel'))

        expect(mockProps.onClose).toHaveBeenCalled()
        expect(mockProps.onSelect).not.toHaveBeenCalled()
    })

    it('does not render when open is false', () => {
        render(<CompanyDisambiguation {...mockProps} open={false} />)

        expect(screen.queryByText('Multiple companies found for "tech"')).not.toBeInTheDocument()
    })

    it('handles companies without sector/industry gracefully', () => {
        const companiesWithoutSector = [
            {
                ticker: 'TEST1',
                name: 'Test Company 1',
                exchange: 'NYSE',
                sector: '',
                industry: '',
            },
            {
                ticker: 'TEST2',
                name: 'Test Company 2',
                exchange: 'NASDAQ',
                sector: 'Technology',
                industry: '',
            },
        ]

        render(
            <CompanyDisambiguation
                {...mockProps}
                companies={companiesWithoutSector}
            />
        )

        expect(screen.getByText('Test Company 1')).toBeInTheDocument()
        expect(screen.getByText('TEST1 • NYSE')).toBeInTheDocument()

        expect(screen.getByText('Test Company 2')).toBeInTheDocument()
        expect(screen.getByText('TEST2 • NASDAQ')).toBeInTheDocument()
        expect(screen.getByText('Technology')).toBeInTheDocument()
    })
})
import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../test/utils'
import { CompanyCard } from '../CompanyCard'
import { mockCompanies } from '../../test/mockData'

describe('CompanyCard', () => {
    const user = userEvent.setup()
    const mockCompany = mockCompanies[0] // Apple Inc.

    it('renders company information correctly', () => {
        render(<CompanyCard company={mockCompany} />)

        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        expect(screen.getByText('AAPL • NASDAQ')).toBeInTheDocument()
        expect(screen.getByText('Technology')).toBeInTheDocument()
        expect(screen.getByText('Consumer Electronics')).toBeInTheDocument()
        expect(screen.getByText('Market Cap: $3.0T')).toBeInTheDocument()
    })

    it('formats market cap correctly for different values', () => {
        const companyWithBillionMarketCap = {
            ...mockCompany,
            marketCap: 500000000000, // 500B
        }

        const { rerender } = render(<CompanyCard company={companyWithBillionMarketCap} />)
        expect(screen.getByText('Market Cap: $500.0B')).toBeInTheDocument()

        const companyWithMillionMarketCap = {
            ...mockCompany,
            marketCap: 500000000, // 500M
        }

        rerender(<CompanyCard company={companyWithMillionMarketCap} />)
        expect(screen.getByText('Market Cap: $500.0M')).toBeInTheDocument()
    })

    it('handles missing market cap', () => {
        const companyWithoutMarketCap = {
            ...mockCompany,
            marketCap: undefined,
        }

        render(<CompanyCard company={companyWithoutMarketCap} />)
        expect(screen.getByText('Market Cap: N/A')).toBeInTheDocument()
    })

    it('handles missing sector and industry', () => {
        const companyWithoutSectorIndustry = {
            ticker: 'TEST',
            name: 'Test Company',
            exchange: 'NYSE',
            sector: '',
            industry: '',
        }

        render(<CompanyCard company={companyWithoutSectorIndustry} />)

        expect(screen.getByText('Test Company')).toBeInTheDocument()
        expect(screen.getByText('TEST • NYSE')).toBeInTheDocument()
        expect(screen.queryByText('Technology')).not.toBeInTheDocument()
        expect(screen.queryByText('Consumer Electronics')).not.toBeInTheDocument()
    })

    it('shows remove button when showRemoveButton is true', () => {
        const onRemove = vi.fn()

        render(
            <CompanyCard
                company={mockCompany}
                onRemove={onRemove}
                showRemoveButton={true}
            />
        )

        const removeButton = screen.getByRole('button')
        expect(removeButton).toBeInTheDocument()
    })

    it('calls onRemove when remove button is clicked', async () => {
        const onRemove = vi.fn()

        render(
            <CompanyCard
                company={mockCompany}
                onRemove={onRemove}
                showRemoveButton={true}
            />
        )

        const removeButton = screen.getByRole('button')
        await user.click(removeButton)

        expect(onRemove).toHaveBeenCalledWith('AAPL')
    })

    it('does not show remove button when showRemoveButton is false', () => {
        render(<CompanyCard company={mockCompany} showRemoveButton={false} />)

        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
})
import React from 'react'
import {
    Card,
    CardContent,
    Typography,
    Box,
    Chip,
    IconButton,
} from '@mui/material'
import {
    Business as BusinessIcon,
    TrendingUp as TrendingUpIcon,
    Close as CloseIcon,
} from '@mui/icons-material'
import { Company } from '../types'

interface CompanyCardProps {
    company: Company
    onRemove?: (ticker: string) => void
    showRemoveButton?: boolean
}

export const CompanyCard: React.FC<CompanyCardProps> = ({
    company,
    onRemove,
    showRemoveButton = false
}) => {
    const formatMarketCap = (marketCap?: number) => {
        if (!marketCap) return 'N/A'

        if (marketCap >= 1e12) {
            return `$${(marketCap / 1e12).toFixed(1)}T`
        } else if (marketCap >= 1e9) {
            return `$${(marketCap / 1e9).toFixed(1)}B`
        } else if (marketCap >= 1e6) {
            return `$${(marketCap / 1e6).toFixed(1)}M`
        }
        return `$${marketCap.toLocaleString()}`
    }

    return (
        <Card sx={{ position: 'relative', height: '100%' }}>
            {showRemoveButton && onRemove && (
                <IconButton
                    size="small"
                    onClick={() => onRemove(company.ticker)}
                    sx={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        zIndex: 1,
                    }}
                >
                    <CloseIcon fontSize="small" />
                </IconButton>
            )}

            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
                    <BusinessIcon sx={{ mr: 1, mt: 0.5, color: 'primary.main' }} />
                    <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="h6" component="h3" gutterBottom>
                            {company.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                            {company.ticker} • {company.exchange}
                        </Typography>
                    </Box>
                </Box>

                <Box sx={{ mb: 2 }}>
                    {company.sector && (
                        <Chip
                            label={company.sector}
                            size="small"
                            variant="outlined"
                            sx={{ mr: 1, mb: 1 }}
                        />
                    )}
                    {company.industry && (
                        <Chip
                            label={company.industry}
                            size="small"
                            variant="outlined"
                            sx={{ mb: 1 }}
                        />
                    )}
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <TrendingUpIcon sx={{ mr: 1, fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="body2" color="text.secondary">
                        Market Cap: {formatMarketCap(company.marketCap)}
                    </Typography>
                </Box>
            </CardContent>
        </Card>
    )
}
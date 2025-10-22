import React, { useState, useEffect } from 'react'
import {
    Box,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Button,
    Paper,
    Typography,
    Alert,
    Chip,
    CircularProgress,
    SelectChangeEvent
} from '@mui/material'
import { Search as SearchIcon, TrendingUp as TrendingUpIcon } from '@mui/icons-material'
import { useDebounce } from '../hooks/useDebounce'
import { apiClient } from '../api/client'
import { CompanyProcessingRequest, TickerValidationResponse } from '../types'

interface CompanyInputFormProps {
    onSubmit: (request: CompanyProcessingRequest) => void
    isProcessing?: boolean
}

export const CompanyInputForm: React.FC<CompanyInputFormProps> = ({
    onSubmit,
    isProcessing = false
}) => {
    const [ticker, setTicker] = useState('')
    const [timeRange, setTimeRange] = useState<1 | 3 | 5>(3)
    const [isValidating, setIsValidating] = useState(false)
    const [validationResult, setValidationResult] = useState<TickerValidationResponse | null>(null)
    const [error, setError] = useState<string | null>(null)

    const debouncedTicker = useDebounce(ticker, 500)

    // Validate ticker when debounced value changes
    useEffect(() => {
        const validateTicker = async () => {
            if (!debouncedTicker.trim()) {
                setValidationResult(null)
                return
            }

            setIsValidating(true)
            setError(null)

            try {
                const response = await apiClient.get<TickerValidationResponse>(
                    `/companies/validate/${debouncedTicker.toUpperCase()}`
                )
                setValidationResult(response.data)
            } catch (err) {
                setError('Failed to validate ticker. Please try again.')
                setValidationResult(null)
            } finally {
                setIsValidating(false)
            }
        }

        validateTicker()
    }, [debouncedTicker])

    const handleTickerChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const value = event.target.value.toUpperCase()
        setTicker(value)
        setError(null)
    }

    const handleTimeRangeChange = (event: SelectChangeEvent<number>) => {
        setTimeRange(event.target.value as 1 | 3 | 5)
    }

    const handleSubmit = (event: React.FormEvent) => {
        event.preventDefault()

        if (!validationResult?.isValid) {
            setError('Please enter a valid company ticker')
            return
        }

        onSubmit({
            ticker: ticker.toUpperCase(),
            timeRange
        })
    }

    const isFormValid = validationResult?.isValid && !isValidating && !isProcessing

    return (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TrendingUpIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6" component="h2">
                    Analyze Company Financials
                </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Enter a company ticker symbol and select the time range for SEC filing analysis.
                The system will scrape, process, and vectorize the documents for chat-based analysis.
            </Typography>

            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                    <Box sx={{ flex: 1 }}>
                        <TextField
                            fullWidth
                            label="Company Ticker"
                            placeholder="e.g., AAPL, MSFT, GOOGL"
                            value={ticker}
                            onChange={handleTickerChange}
                            disabled={isProcessing}
                            InputProps={{
                                startAdornment: <SearchIcon sx={{ mr: 1, color: 'action.active' }} />,
                                endAdornment: isValidating && (
                                    <CircularProgress size={20} />
                                )
                            }}
                            error={!!error || (!!validationResult && !validationResult.isValid)}
                            helperText={
                                error ||
                                (validationResult && !validationResult.isValid && 'Invalid ticker symbol') ||
                                (validationResult?.isValid && validationResult.companyName)
                            }
                        />

                        {/* Ticker suggestions */}
                        {validationResult && !validationResult.isValid && validationResult.suggestions.length > 0 && (
                            <Box sx={{ mt: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                    Did you mean:
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                                    {validationResult.suggestions.slice(0, 3).map((suggestion) => (
                                        <Chip
                                            key={suggestion}
                                            label={suggestion}
                                            size="small"
                                            onClick={() => setTicker(suggestion)}
                                            clickable
                                            variant="outlined"
                                        />
                                    ))}
                                </Box>
                            </Box>
                        )}
                    </Box>

                    <FormControl sx={{ minWidth: 140 }}>
                        <InputLabel>Time Range</InputLabel>
                        <Select
                            value={timeRange}
                            label="Time Range"
                            onChange={handleTimeRangeChange}
                            disabled={isProcessing}
                        >
                            <MenuItem value={1}>1 Year</MenuItem>
                            <MenuItem value={3}>3 Years</MenuItem>
                            <MenuItem value={5}>5 Years</MenuItem>
                        </Select>
                    </FormControl>
                </Box>

                {/* Validation status */}
                {validationResult?.isValid && (
                    <Alert severity="success" sx={{ alignItems: 'center' }}>
                        <strong>{validationResult.companyName}</strong> - Ready for processing
                    </Alert>
                )}

                <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    disabled={!isFormValid}
                    startIcon={isProcessing ? <CircularProgress size={20} /> : <TrendingUpIcon />}
                    sx={{ alignSelf: 'flex-start' }}
                >
                    {isProcessing ? 'Processing...' : 'Start Analysis'}
                </Button>
            </Box>
        </Paper>
    )
}
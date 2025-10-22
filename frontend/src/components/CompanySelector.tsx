import React, { useState } from 'react'
import {
    Autocomplete,
    TextField,
    Paper,
    Typography,
    Box,
    Chip,
    CircularProgress,
    Alert,
} from '@mui/material'
import { Business as BusinessIcon } from '@mui/icons-material'
import { Company } from '../types'
import { useCompanySearch } from '../hooks/useCompanySearch'
import { useAppStore } from '../store/useAppStore'

interface CompanySelectorProps {
    onCompanySelect?: (company: Company) => void
    placeholder?: string
    multiple?: boolean
}

export const CompanySelector: React.FC<CompanySelectorProps> = ({
    onCompanySelect,
    placeholder = "Search for companies...",
    multiple = false
}) => {
    const [inputValue, setInputValue] = useState('')
    const { companies, isLoading, error, searchCompanies } = useCompanySearch()
    const { selectedCompanies, selectCompany, removeSelectedCompany } = useAppStore()

    const handleInputChange = (event: React.SyntheticEvent, newInputValue: string) => {
        setInputValue(newInputValue)
        searchCompanies(newInputValue)
    }

    const handleCompanySelect = (event: React.SyntheticEvent, value: Company | Company[] | null) => {
        if (multiple) {
            // Handle multiple selection
            const newCompanies = value as Company[]
            if (newCompanies) {
                newCompanies.forEach(company => {
                    if (!selectedCompanies.some(c => c.ticker === company.ticker)) {
                        selectCompany(company)
                        onCompanySelect?.(company)
                    }
                })
            }
        } else {
            // Handle single selection
            const company = value as Company
            if (company) {
                selectCompany(company)
                onCompanySelect?.(company)
                setInputValue('')
            }
        }
    }

    const handleChipDelete = (ticker: string) => {
        removeSelectedCompany(ticker)
    }

    const getOptionLabel = (option: Company) => {
        return `${option.name} (${option.ticker})`
    }

    const renderOption = (props: any, option: Company) => (
        <Box component="li" {...props}>
            <BusinessIcon sx={{ mr: 2, color: 'text.secondary' }} />
            <Box>
                <Typography variant="body1" fontWeight="medium">
                    {option.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    {option.ticker} • {option.exchange}
                    {option.sector && ` • ${option.sector}`}
                </Typography>
            </Box>
        </Box>
    )

    return (
        <Box>
            <Autocomplete
                multiple={multiple}
                options={companies}
                getOptionLabel={getOptionLabel}
                renderOption={renderOption}
                inputValue={inputValue}
                onInputChange={handleInputChange}
                onChange={handleCompanySelect}
                loading={isLoading}
                filterOptions={(x) => x} // Disable client-side filtering since we use server-side search
                PaperComponent={({ children, ...props }) => (
                    <Paper {...props} sx={{ mt: 1 }}>
                        {error && (
                            <Alert severity="error" sx={{ m: 1 }}>
                                Failed to search companies. Please try again.
                            </Alert>
                        )}
                        {children}
                    </Paper>
                )}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        placeholder={placeholder}
                        variant="outlined"
                        fullWidth
                        InputProps={{
                            ...params.InputProps,
                            endAdornment: (
                                <>
                                    {isLoading ? <CircularProgress color="inherit" size={20} /> : null}
                                    {params.InputProps.endAdornment}
                                </>
                            ),
                        }}
                    />
                )}
                noOptionsText={
                    inputValue.length < 2
                        ? "Type at least 2 characters to search"
                        : "No companies found"
                }
            />

            {/* Display selected companies as chips */}
            {selectedCompanies.length > 0 && (
                <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {selectedCompanies.map((company) => (
                        <Chip
                            key={company.ticker}
                            label={`${company.name} (${company.ticker})`}
                            onDelete={() => handleChipDelete(company.ticker)}
                            color="primary"
                            variant="outlined"
                            icon={<BusinessIcon />}
                        />
                    ))}
                </Box>
            )}
        </Box>
    )
}
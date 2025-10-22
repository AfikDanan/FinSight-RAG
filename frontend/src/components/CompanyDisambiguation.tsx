import React from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    List,
    ListItem,
    ListItemButton,
    ListItemText,
    ListItemIcon,
    Typography,
    Box,
    Divider,
} from '@mui/material'
import { Business as BusinessIcon } from '@mui/icons-material'
import { Company } from '../types'

interface CompanyDisambiguationProps {
    open: boolean
    companies: Company[]
    searchQuery: string
    onSelect: (company: Company) => void
    onClose: () => void
}

export const CompanyDisambiguation: React.FC<CompanyDisambiguationProps> = ({
    open,
    companies,
    searchQuery,
    onSelect,
    onClose
}) => {
    const handleCompanySelect = (company: Company) => {
        onSelect(company)
        onClose()
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{
                sx: { borderRadius: 2 }
            }}
        >
            <DialogTitle>
                <Typography variant="h6">
                    Multiple companies found for "{searchQuery}"
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Please select the company you're looking for:
                </Typography>
            </DialogTitle>

            <DialogContent sx={{ px: 0 }}>
                <List>
                    {companies.map((company, index) => (
                        <React.Fragment key={company.ticker}>
                            <ListItem disablePadding>
                                <ListItemButton
                                    onClick={() => handleCompanySelect(company)}
                                    sx={{ px: 3, py: 2 }}
                                >
                                    <ListItemIcon>
                                        <BusinessIcon color="primary" />
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={
                                            <Box>
                                                <Typography variant="subtitle1" fontWeight="medium">
                                                    {company.name}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    {company.ticker} • {company.exchange}
                                                </Typography>
                                            </Box>
                                        }
                                        secondary={
                                            <Box sx={{ mt: 0.5 }}>
                                                {company.sector && (
                                                    <Typography variant="caption" color="text.secondary">
                                                        {company.sector}
                                                        {company.industry && ` • ${company.industry}`}
                                                    </Typography>
                                                )}
                                            </Box>
                                        }
                                    />
                                </ListItemButton>
                            </ListItem>
                            {index < companies.length - 1 && <Divider />}
                        </React.Fragment>
                    ))}
                </List>
            </DialogContent>

            <DialogActions sx={{ px: 3, pb: 2 }}>
                <Button onClick={onClose} color="inherit">
                    Cancel
                </Button>
            </DialogActions>
        </Dialog>
    )
}
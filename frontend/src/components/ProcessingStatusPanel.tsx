import React, { useEffect, useState } from 'react'
import {
    Box,
    Paper,
    Typography,
    LinearProgress,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    Button,
    Alert,
    Chip,
    Card,
    CardContent,
    Grid,
    IconButton,
    Collapse,
    CircularProgress,
    Tooltip
} from '@mui/material'
import {
    CloudDownload as ScrapeIcon,
    Description as ParseIcon,
    ViewModule as ChunkIcon,
    Memory as VectorIcon,
    CheckCircle as CompleteIcon,
    Error as ErrorIcon,
    Cancel as CancelIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    AccessTime as TimeIcon,
    Speed as SpeedIcon,
    TrendingUp as TrendingUpIcon
} from '@mui/icons-material'
import { ProcessingStatus } from '../types'
import { useProcessingStatus } from '../hooks/useProcessingStatus'

interface ProcessingStatusPanelProps {
    status: ProcessingStatus
    onCancel?: () => void
    showDetails?: boolean
    enableRealTimeUpdates?: boolean
}

const PHASE_STEPS = [
    {
        key: 'scraping',
        label: 'Scraping SEC Filings',
        description: 'Downloading documents from SEC EDGAR database',
        icon: ScrapeIcon
    },
    {
        key: 'parsing',
        label: 'Parsing Documents',
        description: 'Extracting content from various document formats',
        icon: ParseIcon
    },
    {
        key: 'chunking',
        label: 'Creating Chunks',
        description: 'Segmenting documents into searchable chunks',
        icon: ChunkIcon
    },
    {
        key: 'vectorizing',
        label: 'Generating Embeddings',
        description: 'Creating vector embeddings for semantic search',
        icon: VectorIcon
    }
]

export const ProcessingStatusPanel: React.FC<ProcessingStatusPanelProps> = ({
    status,
    onCancel,
    showDetails = true,
    enableRealTimeUpdates = true
}) => {
    const [expanded, setExpanded] = useState(showDetails)
    const [elapsedTime, setElapsedTime] = useState(0)
    const [processingRate, setProcessingRate] = useState(0)
    const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null)

    // Use the processing status hook for real-time updates
    const { cancelProcessing, isPolling } = useProcessingStatus({
        ticker: status.ticker,
        enabled: enableRealTimeUpdates && status.phase !== 'complete' && status.phase !== 'error'
    })

    // Calculate elapsed time and processing rate
    useEffect(() => {
        const interval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - new Date(status.startedAt).getTime()) / 1000)
            setElapsedTime(elapsed)

            // Calculate processing rate (items per minute)
            if (elapsed > 0) {
                const totalProcessed = status.documentsProcessed + status.chunksCreated + status.chunksVectorized
                const rate = (totalProcessed / elapsed) * 60 // items per minute
                setProcessingRate(rate)
            }
        }, 1000)

        return () => clearInterval(interval)
    }, [status.startedAt, status.documentsProcessed, status.chunksCreated, status.chunksVectorized])

    // Track last update time for freshness indicator
    useEffect(() => {
        setLastUpdateTime(new Date())
    }, [status.progress, status.documentsProcessed, status.chunksCreated, status.chunksVectorized])

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const getCurrentStepIndex = (): number => {
        return PHASE_STEPS.findIndex(step => step.key === status.phase)
    }

    const getPhaseProgress = (): number => {
        const stepIndex = getCurrentStepIndex()
        if (stepIndex === -1) return 0

        // Calculate progress based on current phase and overall completion
        const baseProgress = (stepIndex / PHASE_STEPS.length) * 100

        // Add intra-phase progress based on documents/chunks processed
        let phaseProgress = 0
        switch (status.phase) {
            case 'scraping':
                phaseProgress = status.documentsFound > 0 ?
                    (status.documentsProcessed / status.documentsFound) * (100 / PHASE_STEPS.length) : 0
                break
            case 'parsing':
                phaseProgress = status.documentsFound > 0 ?
                    (status.documentsProcessed / status.documentsFound) * (100 / PHASE_STEPS.length) : 0
                break
            case 'chunking':
                phaseProgress = status.documentsProcessed > 0 ?
                    (status.chunksCreated / (status.documentsProcessed * 10)) * (100 / PHASE_STEPS.length) : 0 // Assume ~10 chunks per doc
                break
            case 'vectorizing':
                phaseProgress = status.chunksCreated > 0 ?
                    (status.chunksVectorized / status.chunksCreated) * (100 / PHASE_STEPS.length) : 0
                break
        }

        return Math.min(baseProgress + phaseProgress, 100)
    }

    const calculateEstimatedTimeRemaining = (): number | null => {
        if (status.estimatedTimeRemaining) {
            return status.estimatedTimeRemaining
        }

        // Calculate based on processing rate
        if (processingRate > 0 && elapsedTime > 30) { // Only estimate after 30 seconds
            const progress = getPhaseProgress()
            if (progress > 0 && progress < 100) {
                const remainingProgress = 100 - progress
                const estimatedSeconds = (remainingProgress / progress) * elapsedTime
                return Math.max(estimatedSeconds, 0)
            }
        }

        return null
    }

    const handleCancel = async () => {
        try {
            await cancelProcessing(status.ticker)
            onCancel?.()
        } catch (error) {
            console.error('Failed to cancel processing:', error)
        }
    }

    const isError = status.phase === 'error'
    const isComplete = status.phase === 'complete'

    return (
        <Paper elevation={2} sx={{ mb: 3 }}>
            {/* Header */}
            <Box sx={{ p: 3, pb: expanded ? 2 : 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {isComplete ? (
                            <CompleteIcon sx={{ mr: 1, color: 'success.main' }} />
                        ) : isError ? (
                            <ErrorIcon sx={{ mr: 1, color: 'error.main' }} />
                        ) : (
                            <ScrapeIcon sx={{ mr: 1, color: 'primary.main' }} />
                        )}
                        <Typography variant="h6">
                            Processing {status.ticker}
                        </Typography>
                        <Chip
                            label={isComplete ? 'Complete' : isError ? 'Error' : 'In Progress'}
                            color={isComplete ? 'success' : isError ? 'error' : 'primary'}
                            size="small"
                            sx={{ ml: 2 }}
                        />
                    </Box>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {!isComplete && !isError && (
                            <>
                                <Box sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
                                    <TimeIcon sx={{ fontSize: 16, mr: 0.5, color: 'text.secondary' }} />
                                    <Typography variant="caption" color="text.secondary">
                                        {formatTime(elapsedTime)}
                                        {(() => {
                                            const estimated = calculateEstimatedTimeRemaining()
                                            return estimated ? <> / ~{formatTime(Math.round(estimated))}</> : null
                                        })()}
                                    </Typography>
                                </Box>

                                {processingRate > 0 && (
                                    <Tooltip title={`Processing rate: ${processingRate.toFixed(1)} items/min`}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
                                            <SpeedIcon sx={{ fontSize: 16, mr: 0.5, color: 'text.secondary' }} />
                                            <Typography variant="caption" color="text.secondary">
                                                {processingRate.toFixed(1)}/min
                                            </Typography>
                                        </Box>
                                    </Tooltip>
                                )}

                                {isPolling && (
                                    <Tooltip title="Real-time updates active">
                                        <CircularProgress size={16} sx={{ mr: 1 }} />
                                    </Tooltip>
                                )}
                            </>
                        )}

                        {onCancel && !isComplete && !isError && (
                            <Tooltip title="Cancel processing">
                                <IconButton onClick={handleCancel} size="small" color="error">
                                    <CancelIcon />
                                </IconButton>
                            </Tooltip>
                        )}

                        <IconButton
                            onClick={() => setExpanded(!expanded)}
                            size="small"
                        >
                            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                    </Box>
                </Box>

                {/* Progress bar */}
                <Box sx={{ mb: 2 }}>
                    <LinearProgress
                        variant="determinate"
                        value={isComplete ? 100 : getPhaseProgress()}
                        sx={{ height: 8, borderRadius: 4 }}
                        color={isError ? 'error' : isComplete ? 'success' : 'primary'}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                        {isComplete ? 'Processing complete' :
                            isError ? 'Processing failed' :
                                `${Math.round(getPhaseProgress())}% complete`}
                    </Typography>
                </Box>

                {/* Error message */}
                {isError && status.error && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                        {status.error}
                    </Alert>
                )}
            </Box>

            {/* Detailed progress */}
            <Collapse in={expanded}>
                <Box sx={{ px: 3, pb: 3 }}>
                    {/* Real-time update indicator */}
                    {lastUpdateTime && !isComplete && !isError && (
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                            <TrendingUpIcon sx={{ fontSize: 16, mr: 1, color: 'success.main' }} />
                            <Typography variant="caption" color="text.secondary">
                                Last updated: {lastUpdateTime.toLocaleTimeString()}
                                {isPolling && ' • Live updates active'}
                            </Typography>
                        </Box>
                    )}

                    {/* Statistics cards */}
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={6} sm={3}>
                            <Card variant="outlined" sx={{
                                bgcolor: status.phase === 'scraping' ? 'primary.50' : 'background.paper',
                                borderColor: status.phase === 'scraping' ? 'primary.main' : 'divider'
                            }}>
                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Documents Found
                                            </Typography>
                                            <Typography variant="h6">
                                                {status.documentsFound}
                                            </Typography>
                                        </Box>
                                        <ScrapeIcon sx={{
                                            color: status.phase === 'scraping' ? 'primary.main' : 'text.secondary',
                                            opacity: 0.7
                                        }} />
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Card variant="outlined" sx={{
                                bgcolor: status.phase === 'parsing' ? 'primary.50' : 'background.paper',
                                borderColor: status.phase === 'parsing' ? 'primary.main' : 'divider'
                            }}>
                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Documents Processed
                                            </Typography>
                                            <Typography variant="h6">
                                                {status.documentsProcessed}
                                                {status.documentsFound > 0 && (
                                                    <Typography variant="caption" color="text.secondary" component="span">
                                                        /{status.documentsFound}
                                                    </Typography>
                                                )}
                                            </Typography>
                                        </Box>
                                        <ParseIcon sx={{
                                            color: status.phase === 'parsing' ? 'primary.main' : 'text.secondary',
                                            opacity: 0.7
                                        }} />
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Card variant="outlined" sx={{
                                bgcolor: status.phase === 'chunking' ? 'primary.50' : 'background.paper',
                                borderColor: status.phase === 'chunking' ? 'primary.main' : 'divider'
                            }}>
                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Chunks Created
                                            </Typography>
                                            <Typography variant="h6">
                                                {status.chunksCreated}
                                            </Typography>
                                        </Box>
                                        <ChunkIcon sx={{
                                            color: status.phase === 'chunking' ? 'primary.main' : 'text.secondary',
                                            opacity: 0.7
                                        }} />
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Card variant="outlined" sx={{
                                bgcolor: status.phase === 'vectorizing' ? 'primary.50' : 'background.paper',
                                borderColor: status.phase === 'vectorizing' ? 'primary.main' : 'divider'
                            }}>
                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Chunks Vectorized
                                            </Typography>
                                            <Typography variant="h6">
                                                {status.chunksVectorized}
                                                {status.chunksCreated > 0 && (
                                                    <Typography variant="caption" color="text.secondary" component="span">
                                                        /{status.chunksCreated}
                                                    </Typography>
                                                )}
                                            </Typography>
                                        </Box>
                                        <VectorIcon sx={{
                                            color: status.phase === 'vectorizing' ? 'primary.main' : 'text.secondary',
                                            opacity: 0.7
                                        }} />
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>

                    {/* Step-by-step progress */}
                    <Stepper activeStep={getCurrentStepIndex()} orientation="vertical">
                        {PHASE_STEPS.map((step, index) => {
                            const StepIcon = step.icon
                            const isActive = index === getCurrentStepIndex()
                            const isCompleted = index < getCurrentStepIndex() || isComplete
                            const hasError = isError && isActive

                            return (
                                <Step key={step.key} completed={isCompleted}>
                                    <StepLabel
                                        error={hasError}
                                        StepIconComponent={() => (
                                            <Box
                                                sx={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: 24,
                                                    height: 24,
                                                    borderRadius: '50%',
                                                    bgcolor: hasError ? 'error.main' :
                                                        isCompleted ? 'success.main' :
                                                            isActive ? 'primary.main' : 'grey.300',
                                                    color: 'white'
                                                }}
                                            >
                                                <StepIcon sx={{ fontSize: 14 }} />
                                            </Box>
                                        )}
                                    >
                                        <Typography variant="subtitle2">
                                            {step.label}
                                        </Typography>
                                    </StepLabel>
                                    <StepContent>
                                        <Typography variant="body2" color="text.secondary">
                                            {step.description}
                                        </Typography>
                                        {isActive && !isError && (
                                            <Box sx={{ mt: 1 }}>
                                                {(() => {
                                                    let progressValue = 0
                                                    let progressLabel = ''

                                                    switch (step.key) {
                                                        case 'scraping':
                                                            if (status.documentsFound > 0) {
                                                                progressValue = (status.documentsProcessed / status.documentsFound) * 100
                                                                progressLabel = `${status.documentsProcessed}/${status.documentsFound} documents`
                                                            }
                                                            break
                                                        case 'parsing':
                                                            if (status.documentsFound > 0) {
                                                                progressValue = (status.documentsProcessed / status.documentsFound) * 100
                                                                progressLabel = `${status.documentsProcessed}/${status.documentsFound} documents`
                                                            }
                                                            break
                                                        case 'chunking':
                                                            progressLabel = `${status.chunksCreated} chunks created`
                                                            break
                                                        case 'vectorizing':
                                                            if (status.chunksCreated > 0) {
                                                                progressValue = (status.chunksVectorized / status.chunksCreated) * 100
                                                                progressLabel = `${status.chunksVectorized}/${status.chunksCreated} chunks`
                                                            }
                                                            break
                                                    }

                                                    return (
                                                        <Box sx={{ width: 300 }}>
                                                            <LinearProgress
                                                                variant={progressValue > 0 ? "determinate" : "indeterminate"}
                                                                value={progressValue}
                                                                sx={{ mb: 0.5 }}
                                                            />
                                                            {progressLabel && (
                                                                <Typography variant="caption" color="text.secondary">
                                                                    {progressLabel}
                                                                </Typography>
                                                            )}
                                                        </Box>
                                                    )
                                                })()}
                                            </Box>
                                        )}
                                    </StepContent>
                                </Step>
                            )
                        })}
                    </Stepper>

                    {/* Completion message */}
                    {isComplete && (
                        <Alert severity="success" sx={{ mt: 2 }}>
                            <Typography variant="subtitle2">
                                Processing Complete!
                            </Typography>
                            <Typography variant="body2">
                                {status.ticker} is ready for analysis. You can now start asking questions about the company's financial data.
                            </Typography>
                        </Alert>
                    )}
                </Box>
            </Collapse>
        </Paper>
    )
}
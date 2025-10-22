import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Container, Typography, Box, Button, Fade } from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { theme } from './theme'
import { CompanyInputForm, ProcessingStatusPanel, ChatInterface } from './components'
import { useAppStore } from './store/useAppStore'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            staleTime: 5 * 60 * 1000, // 5 minutes
            refetchOnWindowFocus: false,
        },
        mutations: {
            retry: 1,
        },
    },
})

function App() {
    const {
        currentPhase,
        processingStatus,
        companyContext,
        startProcessing,
        resetWorkflow
    } = useAppStore()

    const handleProcessingRequest = async (request: { ticker: string; timeRange: 1 | 3 | 5 }) => {
        await startProcessing(request)
    }

    const handleCancelProcessing = () => {
        // TODO: Implement actual cancellation API call
        resetWorkflow()
    }

    const renderPhaseContent = () => {
        switch (currentPhase) {
            case 'input':
                return (
                    <Fade in timeout={300}>
                        <Box>
                            <Typography variant="body1" gutterBottom sx={{ mb: 4 }}>
                                Enter a company ticker symbol and select the time range for SEC filing analysis.
                                The system will scrape, process, and vectorize the documents for chat-based analysis.
                            </Typography>
                            <CompanyInputForm
                                onSubmit={handleProcessingRequest}
                                isProcessing={false}
                            />
                        </Box>
                    </Fade>
                )

            case 'processing':
                return (
                    <Fade in timeout={300}>
                        <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                                <Button
                                    startIcon={<ArrowBackIcon />}
                                    onClick={resetWorkflow}
                                    variant="outlined"
                                    size="small"
                                >
                                    Start Over
                                </Button>
                            </Box>

                            {processingStatus && (
                                <ProcessingStatusPanel
                                    status={processingStatus}
                                    onCancel={handleCancelProcessing}
                                    showDetails={true}
                                    enableRealTimeUpdates={true}
                                />
                            )}
                        </Box>
                    </Fade>
                )

            case 'chat':
                return (
                    <Fade in timeout={300}>
                        <Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                                <Box>
                                    <Typography variant="h6">
                                        Chat with {companyContext?.name || companyContext?.ticker}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Ask questions about the company's financial data and SEC filings
                                    </Typography>
                                </Box>
                                <Button
                                    startIcon={<ArrowBackIcon />}
                                    onClick={resetWorkflow}
                                    variant="outlined"
                                    size="small"
                                >
                                    Analyze Another Company
                                </Button>
                            </Box>

                            <ChatInterface />
                        </Box>
                    </Fade>
                )

            default:
                return null
        }
    }

    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <Container maxWidth="lg">
                    <Box sx={{ my: 4 }}>
                        <Typography variant="h4" component="h1" gutterBottom>
                            RAG Financial Assistant
                        </Typography>

                        {renderPhaseContent()}
                    </Box>
                </Container>
            </ThemeProvider>
        </QueryClientProvider>
    )
}

export default App
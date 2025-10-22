import { describe, test, expect, beforeEach, vi } from 'vitest'
import { useAppStore } from '../useAppStore'

// Mock the API client
vi.mock('../../api/client', () => ({
    companyAPI: {
        startProcessing: vi.fn().mockResolvedValue({ jobId: 'test-job-123' })
    }
}))

describe('useAppStore - Workflow Phase Management', () => {
    beforeEach(() => {
        // Reset store to initial state
        useAppStore.getState().resetWorkflow()
    })

    test('initializes with correct default state', () => {
        const state = useAppStore.getState()

        expect(state.currentPhase).toBe('input')
        expect(state.previousPhase).toBe(null)
        expect(state.selectedTicker).toBe('')
        expect(state.selectedTimeRange).toBe(3)
        expect(state.workflowError).toBe(null)
        expect(state.processingStatus).toBe(null)
        expect(state.chatEnabled).toBe(false)
    })

    test('canTransitionTo validates phase transitions correctly', () => {
        const state = useAppStore.getState()

        // From input phase
        expect(state.canTransitionTo('input')).toBe(true) // Can always go to input
        expect(state.canTransitionTo('processing')).toBe(true) // Can transition from input to processing
        expect(state.canTransitionTo('chat')).toBe(false) // No processing complete
    })

    test('startProcessing transitions to processing phase correctly', async () => {


        const { startProcessing } = useAppStore.getState()

        await startProcessing({ ticker: 'AAPL', timeRange: 5 })

        const state = useAppStore.getState()
        expect(state.currentPhase).toBe('processing')
        expect(state.previousPhase).toBe('input')
        expect(state.selectedTicker).toBe('AAPL')
        expect(state.selectedTimeRange).toBe(5)
        expect(state.processingStatus).toBeTruthy()
        expect(state.processingStatus?.ticker).toBe('AAPL')
        expect(state.processingStatus?.phase).toBe('scraping')
        expect(state.processingJobId).toBe('test-job-123')
        expect(state.chatEnabled).toBe(false)
    })

    test('completeProcessing transitions to chat phase', () => {
        const { completeProcessing } = useAppStore.getState()

        // First set up processing state
        useAppStore.setState({
            currentPhase: 'processing',
            selectedTicker: 'AAPL'
        })

        const mockCompanyContext = {
            ticker: 'AAPL',
            name: 'Apple Inc.',
            processingStatus: {
                ticker: 'AAPL',
                phase: 'complete' as const,
                progress: 100,
                documentsFound: 10,
                documentsProcessed: 10,
                chunksCreated: 150,
                chunksVectorized: 150,
                startedAt: new Date()
            },
            documentsAvailable: 10,
            timeRangeProcessed: 5
        }

        completeProcessing(mockCompanyContext)

        const state = useAppStore.getState()
        expect(state.currentPhase).toBe('chat')
        expect(state.previousPhase).toBe('processing')
        expect(state.companyContext).toEqual(mockCompanyContext)
        expect(state.chatEnabled).toBe(true)
        expect(state.workflowError).toBe(null)
    })

    test('resetWorkflow clears all state', () => {
        // Set up some state
        useAppStore.setState({
            currentPhase: 'chat',
            selectedTicker: 'AAPL',
            processingStatus: {
                ticker: 'AAPL',
                phase: 'complete',
                progress: 100,
                documentsFound: 10,
                documentsProcessed: 10,
                chunksCreated: 150,
                chunksVectorized: 150,
                startedAt: new Date()
            },
            chatEnabled: true
        })

        const { resetWorkflow } = useAppStore.getState()
        resetWorkflow()

        const state = useAppStore.getState()
        expect(state.currentPhase).toBe('input')
        expect(state.previousPhase).toBe(null)
        expect(state.selectedTicker).toBe('')
        expect(state.selectedTimeRange).toBe(3)
        expect(state.processingStatus).toBe(null)
        expect(state.companyContext).toBe(null)
        expect(state.chatEnabled).toBe(false)
        expect(state.workflowError).toBe(null)
    })

    test('failProcessing sets error state correctly', () => {
        const { failProcessing } = useAppStore.getState()

        // Set up processing state first
        useAppStore.setState({
            currentPhase: 'processing',
            processingStatus: {
                ticker: 'AAPL',
                phase: 'scraping',
                progress: 25,
                documentsFound: 0,
                documentsProcessed: 0,
                chunksCreated: 0,
                chunksVectorized: 0,
                startedAt: new Date()
            }
        })

        failProcessing('Network error', 'Failed to connect to SEC EDGAR')

        const state = useAppStore.getState()
        expect(state.processingStatus?.phase).toBe('error')
        expect(state.processingStatus?.error).toBe('Network error')
        expect(state.workflowError).toBeTruthy()
        expect(state.workflowError?.message).toBe('Network error')
        expect(state.workflowError?.details).toBe('Failed to connect to SEC EDGAR')
        expect(state.workflowError?.recoverable).toBe(true)
    })

    test('updateProcessingProgress updates progress state', () => {
        const { updateProcessingProgress } = useAppStore.getState()

        // Set initial processing progress
        useAppStore.setState({
            processingProgress: {
                phase: 'scraping',
                progress: 0,
                currentStep: 'Starting...',
                documentsFound: 0,
                documentsProcessed: 0,
                chunksCreated: 0,
                chunksVectorized: 0
            }
        })

        updateProcessingProgress({
            progress: 50,
            currentStep: 'Processing documents...',
            documentsFound: 10,
            documentsProcessed: 5
        })

        const state = useAppStore.getState()
        expect(state.processingProgress?.progress).toBe(50)
        expect(state.processingProgress?.currentStep).toBe('Processing documents...')
        expect(state.processingProgress?.documentsFound).toBe(10)
        expect(state.processingProgress?.documentsProcessed).toBe(5)
        expect(state.processingProgress?.phase).toBe('scraping') // Should remain unchanged
    })

    test('markCompanyAsProcessed and isCompanyProcessed work correctly', () => {
        const { markCompanyAsProcessed, isCompanyProcessed } = useAppStore.getState()

        expect(isCompanyProcessed('AAPL')).toBe(false)

        markCompanyAsProcessed('AAPL')

        expect(isCompanyProcessed('AAPL')).toBe(true)
        expect(isCompanyProcessed('GOOGL')).toBe(false)
    })

    test('enableChat and disableChat control chat functionality', () => {
        const { enableChat, disableChat } = useAppStore.getState()

        expect(useAppStore.getState().chatEnabled).toBe(false)

        enableChat()
        expect(useAppStore.getState().chatEnabled).toBe(true)

        disableChat()
        expect(useAppStore.getState().chatEnabled).toBe(false)
    })
})
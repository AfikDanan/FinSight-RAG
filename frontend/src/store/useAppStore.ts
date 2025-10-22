import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { Company, Message, Citation, ProcessingStatus, CompanyContext, CompanyProcessingRequest } from '../types'
import { companyAPI } from '../api/client'

type WorkflowPhase = 'input' | 'processing' | 'chat'
type ProcessingPhase = 'scraping' | 'parsing' | 'chunking' | 'vectorizing' | 'complete' | 'error'

interface WorkflowError {
    phase: WorkflowPhase
    message: string
    details?: string
    timestamp: Date
    recoverable: boolean
}

interface ProcessingProgress {
    phase: ProcessingPhase
    progress: number
    currentStep: string
    estimatedTimeRemaining?: number
    documentsFound: number
    documentsProcessed: number
    chunksCreated: number
    chunksVectorized: number
}

interface AppState {
    // Workflow state
    currentPhase: WorkflowPhase
    previousPhase: WorkflowPhase | null
    selectedTicker: string
    selectedTimeRange: 1 | 3 | 5
    workflowError: WorkflowError | null
    canTransitionTo: (phase: WorkflowPhase) => boolean

    // Processing state
    processingStatus: ProcessingStatus | null
    processingProgress: ProcessingProgress | null
    processingJobId: string | null
    processingStartTime: Date | null
    processingEndTime: Date | null

    // Chat state
    messages: Message[]
    currentSession: string
    isTyping: boolean
    companyContext: CompanyContext | null
    chatEnabled: boolean

    // Company state
    selectedCompanies: Company[]
    companyCache: Map<string, Company>
    processedCompanies: Set<string>

    // UI state
    sidebarOpen: boolean
    citationPanelOpen: boolean
    currentCitation: Citation | null

    // Actions
    // Workflow actions
    startProcessing: (request: CompanyProcessingRequest) => Promise<void>
    updateProcessingStatus: (status: ProcessingStatus) => void
    updateProcessingProgress: (progress: Partial<ProcessingProgress>) => void
    completeProcessing: (companyContext: CompanyContext) => void
    failProcessing: (error: string, details?: string) => void
    resetWorkflow: () => void
    setWorkflowPhase: (phase: WorkflowPhase, force?: boolean) => boolean
    transitionToPhase: (phase: WorkflowPhase) => Promise<boolean>
    handleWorkflowError: (error: WorkflowError) => void
    clearWorkflowError: () => void
    retryFromError: () => Promise<void>

    // Chat actions
    addMessage: (message: Message) => void
    setIsTyping: (isTyping: boolean) => void
    sendMessage: (message: string) => Promise<void>
    clearMessages: () => void
    setCurrentSession: (sessionId: string) => void
    enableChat: () => void
    disableChat: () => void

    // Company actions
    selectCompany: (company: Company) => void
    removeSelectedCompany: (ticker: string) => void
    clearSelectedCompanies: () => void
    cacheCompany: (company: Company) => void
    markCompanyAsProcessed: (ticker: string) => void
    isCompanyProcessed: (ticker: string) => boolean

    // UI actions
    setSidebarOpen: (open: boolean) => void
    openCitation: (citation: Citation) => void
    closeCitationPanel: () => void
}

export const useAppStore = create<AppState>()(
    devtools(
        (set, get) => ({
            // Initial state
            // Workflow state
            currentPhase: 'input',
            previousPhase: null,
            selectedTicker: '',
            selectedTimeRange: 3,
            workflowError: null,
            canTransitionTo: (phase: WorkflowPhase) => {
                const { currentPhase, processingStatus, companyContext } = get()

                switch (phase) {
                    case 'input':
                        return true // Can always go back to input
                    case 'processing':
                        return currentPhase === 'input'
                    case 'chat':
                        return currentPhase === 'processing' &&
                            processingStatus?.phase === 'complete' &&
                            !!companyContext
                    default:
                        return false
                }
            },

            // Processing state
            processingStatus: null,
            processingProgress: null,
            processingJobId: null,
            processingStartTime: null,
            processingEndTime: null,

            // Chat state
            messages: [],
            currentSession: '',
            isTyping: false,
            companyContext: null,
            chatEnabled: false,

            // Company state
            selectedCompanies: [],
            companyCache: new Map(),
            processedCompanies: new Set(),

            // UI state
            sidebarOpen: false,
            citationPanelOpen: false,
            currentCitation: null,

            // Workflow actions
            startProcessing: async (request: CompanyProcessingRequest) => {
                const { canTransitionTo } = get()

                if (!canTransitionTo('processing')) {
                    console.error('Cannot transition to processing phase')
                    return
                }

                const processingStartTime = new Date()

                set((state) => ({
                    previousPhase: state.currentPhase,
                    currentPhase: 'processing',
                    selectedTicker: request.ticker,
                    selectedTimeRange: request.timeRange,
                    processingStartTime,
                    processingEndTime: null,
                    processingJobId: null,
                    workflowError: null,
                    processingStatus: {
                        ticker: request.ticker,
                        phase: 'scraping',
                        progress: 0,
                        documentsFound: 0,
                        documentsProcessed: 0,
                        chunksCreated: 0,
                        chunksVectorized: 0,
                        startedAt: processingStartTime
                    },
                    processingProgress: {
                        phase: 'scraping',
                        progress: 0,
                        currentStep: 'Initializing document scraping...',
                        documentsFound: 0,
                        documentsProcessed: 0,
                        chunksCreated: 0,
                        chunksVectorized: 0
                    },
                    messages: [],
                    companyContext: null,
                    chatEnabled: false
                }))

                try {
                    const response = await companyAPI.startProcessing(request)
                    set({ processingJobId: response.jobId })
                    // Status updates will be handled by the useProcessingStatus hook
                } catch (error) {
                    console.error('Failed to start processing:', error)
                    get().failProcessing(
                        error instanceof Error ? error.message : 'Failed to start processing',
                        'Check your network connection and try again'
                    )
                }
            },

            updateProcessingStatus: (status: ProcessingStatus) => {
                set({ processingStatus: status })

                // Auto-transition to chat phase when processing completes
                if (status.phase === 'complete') {
                    const { companyContext } = get()
                    if (companyContext) {
                        get().transitionToPhase('chat')
                    }
                }
            },

            updateProcessingProgress: (progress: Partial<ProcessingProgress>) =>
                set((state) => ({
                    processingProgress: state.processingProgress ? {
                        ...state.processingProgress,
                        ...progress
                    } : null
                })),

            completeProcessing: (companyContext: CompanyContext) => {
                const processingEndTime = new Date()

                set((state) => ({
                    previousPhase: state.currentPhase,
                    currentPhase: 'chat',
                    companyContext,
                    processingStatus: companyContext.processingStatus,
                    processingEndTime,
                    chatEnabled: true,
                    workflowError: null
                }))

                // Mark company as processed
                get().markCompanyAsProcessed(companyContext.ticker)
            },

            failProcessing: (error: string, details?: string) => {
                const workflowError: WorkflowError = {
                    phase: 'processing',
                    message: error,
                    details,
                    timestamp: new Date(),
                    recoverable: true
                }

                set((state) => ({
                    processingStatus: state.processingStatus ? {
                        ...state.processingStatus,
                        phase: 'error',
                        error
                    } : null,
                    workflowError,
                    processingEndTime: new Date()
                }))
            },

            resetWorkflow: () =>
                set({
                    currentPhase: 'input',
                    previousPhase: null,
                    selectedTicker: '',
                    selectedTimeRange: 3,
                    processingStatus: null,
                    processingProgress: null,
                    processingJobId: null,
                    processingStartTime: null,
                    processingEndTime: null,
                    messages: [],
                    companyContext: null,
                    currentSession: '',
                    chatEnabled: false,
                    workflowError: null,
                    processedCompanies: new Set()
                }),

            setWorkflowPhase: (phase: WorkflowPhase, force = false) => {
                const { canTransitionTo, currentPhase } = get()

                if (!force && !canTransitionTo(phase)) {
                    console.warn(`Cannot transition from ${currentPhase} to ${phase}`)
                    return false
                }

                set((state) => ({
                    previousPhase: state.currentPhase,
                    currentPhase: phase,
                    workflowError: null
                }))

                return true
            },

            transitionToPhase: async (phase: WorkflowPhase) => {
                const { currentPhase, canTransitionTo } = get()

                if (!canTransitionTo(phase)) {
                    console.warn(`Cannot transition from ${currentPhase} to ${phase}`)
                    return false
                }

                try {
                    // Perform any necessary cleanup or preparation for the new phase
                    switch (phase) {
                        case 'input':
                            // Clear processing state when going back to input
                            set({
                                processingStatus: null,
                                processingProgress: null,
                                companyContext: null,
                                chatEnabled: false
                            })
                            break
                        case 'processing':
                            // This should be handled by startProcessing
                            break
                        case 'chat':
                            // Enable chat functionality
                            get().enableChat()
                            break
                    }

                    return get().setWorkflowPhase(phase)
                } catch (error) {
                    console.error(`Failed to transition to ${phase}:`, error)
                    get().handleWorkflowError({
                        phase: currentPhase,
                        message: `Failed to transition to ${phase}`,
                        details: error instanceof Error ? error.message : 'Unknown error',
                        timestamp: new Date(),
                        recoverable: true
                    })
                    return false
                }
            },

            handleWorkflowError: (error: WorkflowError) =>
                set({ workflowError: error }),

            clearWorkflowError: () =>
                set({ workflowError: null }),

            retryFromError: async () => {
                const { workflowError, selectedTicker, selectedTimeRange } = get()

                if (!workflowError || !workflowError.recoverable) {
                    console.error('Cannot retry from current error state')
                    return
                }

                get().clearWorkflowError()

                // Retry based on the error phase
                switch (workflowError.phase) {
                    case 'processing':
                        if (selectedTicker) {
                            await get().startProcessing({
                                ticker: selectedTicker,
                                timeRange: selectedTimeRange
                            })
                        }
                        break
                    default:
                        console.warn('No retry logic for error phase:', workflowError.phase)
                }
            },

            // Chat actions
            addMessage: (message: Message) =>
                set((state) => ({
                    messages: [...state.messages, message]
                })),

            setIsTyping: (isTyping: boolean) =>
                set({ isTyping }),

            sendMessage: async (message: string) => {
                const { companyContext, currentSession, chatEnabled } = get()

                if (!chatEnabled || !companyContext) {
                    console.error('Chat is not enabled or no company context available')
                    return
                }

                // Add user message
                const userMessage: Message = {
                    id: Date.now().toString(),
                    content: message,
                    type: 'user',
                    timestamp: new Date()
                }

                set((state) => ({
                    messages: [...state.messages, userMessage],
                    isTyping: true
                }))

                try {
                    // TODO: Implement actual API call for chat
                    // This will be implemented in the backend tasks
                    // const response = await apiClient.post('/api/chat/query', {
                    //     query: message,
                    //     ticker: companyContext.ticker,
                    //     session_id: currentSession
                    // })

                    // For now, add a placeholder response
                    const assistantMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        content: 'This is a placeholder response. The chat functionality will be implemented in later tasks.',
                        type: 'assistant',
                        timestamp: new Date(),
                        citations: []
                    }

                    set((state) => ({
                        messages: [...state.messages, assistantMessage],
                        isTyping: false
                    }))
                } catch (error) {
                    console.error('Failed to send message:', error)

                    // Handle chat error
                    get().handleWorkflowError({
                        phase: 'chat',
                        message: 'Failed to send message',
                        details: error instanceof Error ? error.message : 'Unknown error',
                        timestamp: new Date(),
                        recoverable: true
                    })

                    set({ isTyping: false })
                }
            },

            clearMessages: () =>
                set({ messages: [] }),

            setCurrentSession: (sessionId: string) =>
                set({ currentSession: sessionId }),

            enableChat: () =>
                set({ chatEnabled: true }),

            disableChat: () =>
                set({ chatEnabled: false }),

            // Company actions
            selectCompany: (company: Company) =>
                set((state) => {
                    const isAlreadySelected = state.selectedCompanies.some(
                        (c) => c.ticker === company.ticker
                    )
                    if (isAlreadySelected) return state

                    return {
                        selectedCompanies: [...state.selectedCompanies, company],
                        companyCache: new Map(state.companyCache.set(company.ticker, company))
                    }
                }),

            removeSelectedCompany: (ticker: string) =>
                set((state) => ({
                    selectedCompanies: state.selectedCompanies.filter(
                        (c) => c.ticker !== ticker
                    )
                })),

            clearSelectedCompanies: () =>
                set({ selectedCompanies: [] }),

            cacheCompany: (company: Company) =>
                set((state) => ({
                    companyCache: new Map(state.companyCache.set(company.ticker, company))
                })),

            markCompanyAsProcessed: (ticker: string) =>
                set((state) => ({
                    processedCompanies: new Set(state.processedCompanies.add(ticker))
                })),

            isCompanyProcessed: (ticker: string) => {
                const { processedCompanies } = get()
                return processedCompanies.has(ticker)
            },

            // UI actions
            setSidebarOpen: (open: boolean) =>
                set({ sidebarOpen: open }),

            openCitation: (citation: Citation) =>
                set({
                    currentCitation: citation,
                    citationPanelOpen: true
                }),

            closeCitationPanel: () =>
                set({
                    citationPanelOpen: false,
                    currentCitation: null
                })
        }),
        {
            name: 'rag-financial-assistant-store'
        }
    )
)
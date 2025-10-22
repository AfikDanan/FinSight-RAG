import { useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '../store/useAppStore'
import { ProcessingStatus } from '../types'
import { apiClient } from '../api/client'

interface UseProcessingStatusOptions {
    ticker?: string
    enabled?: boolean
    pollingInterval?: number
}

export const useProcessingStatus = ({
    ticker,
    enabled = true,
    pollingInterval = 2000 // 2 seconds
}: UseProcessingStatusOptions = {}) => {
    const { processingStatus, updateProcessingStatus, completeProcessing } = useAppStore()
    const intervalRef = useRef<NodeJS.Timeout | null>(null)
    const isPollingRef = useRef(false)

    const fetchStatus = useCallback(async (tickerSymbol: string) => {
        try {
            const response = await apiClient.get(`/companies/${tickerSymbol}/status`)
            const status: ProcessingStatus = {
                ...response.data,
                startedAt: new Date(response.data.startedAt),
                completedAt: response.data.completedAt ? new Date(response.data.completedAt) : undefined
            }

            updateProcessingStatus(status)

            // If processing is complete, transition to chat phase
            if (status.phase === 'complete') {
                completeProcessing({
                    ticker: status.ticker,
                    name: response.data.companyName || status.ticker,
                    processingStatus: status,
                    documentsAvailable: status.documentsProcessed,
                    timeRangeProcessed: response.data.timeRangeProcessed || 3
                })
                stopPolling()
            } else if (status.phase === 'error') {
                stopPolling()
            }

            return status
        } catch (error) {
            console.error('Failed to fetch processing status:', error)
            // Update status to error state
            if (processingStatus) {
                updateProcessingStatus({
                    ...processingStatus,
                    phase: 'error',
                    error: 'Failed to fetch processing status'
                })
            }
            stopPolling()
            throw error
        }
    }, [updateProcessingStatus, completeProcessing, processingStatus])

    const startPolling = useCallback((tickerSymbol: string) => {
        if (isPollingRef.current || !enabled) return

        isPollingRef.current = true

        // Initial fetch
        fetchStatus(tickerSymbol)

        // Set up polling interval
        intervalRef.current = setInterval(() => {
            fetchStatus(tickerSymbol)
        }, pollingInterval)
    }, [fetchStatus, enabled, pollingInterval])

    const stopPolling = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
        }
        isPollingRef.current = false
    }, [])

    const cancelProcessing = useCallback(async (tickerSymbol: string) => {
        try {
            await apiClient.post(`/companies/${tickerSymbol}/cancel`)
            stopPolling()

            if (processingStatus) {
                updateProcessingStatus({
                    ...processingStatus,
                    phase: 'error',
                    error: 'Processing cancelled by user'
                })
            }
        } catch (error) {
            console.error('Failed to cancel processing:', error)
            throw error
        }
    }, [processingStatus, updateProcessingStatus, stopPolling])

    // Start polling when ticker is provided and processing is active
    useEffect(() => {
        if (ticker && enabled && processingStatus &&
            processingStatus.phase !== 'complete' &&
            processingStatus.phase !== 'error') {
            startPolling(ticker)
        } else {
            stopPolling()
        }

        return () => stopPolling()
    }, [ticker, enabled, processingStatus?.phase, startPolling, stopPolling])

    // Cleanup on unmount
    useEffect(() => {
        return () => stopPolling()
    }, [stopPolling])

    return {
        processingStatus,
        isPolling: isPollingRef.current,
        startPolling,
        stopPolling,
        cancelProcessing,
        fetchStatus
    }
}
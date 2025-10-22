import { renderHook, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import { useProcessingStatus } from '../useProcessingStatus'
import { apiClient } from '../../api/client'

// Mock the API client
vi.mock('../../api/client', () => ({
    apiClient: {
        get: vi.fn(),
        post: vi.fn()
    }
}))

// Mock the app store
vi.mock('../../store/useAppStore', () => ({
    useAppStore: () => ({
        processingStatus: null,
        updateProcessingStatus: vi.fn(),
        completeProcessing: vi.fn()
    })
}))

describe('useProcessingStatus', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    test('starts polling when ticker is provided', async () => {
        const mockStatus = {
            ticker: 'AAPL',
            phase: 'scraping',
            progress: 25,
            documentsFound: 10,
            documentsProcessed: 3,
            chunksCreated: 0,
            chunksVectorized: 0,
            startedAt: new Date().toISOString()
        }

        vi.mocked(apiClient.get).mockResolvedValue({ data: mockStatus })

        const { result } = renderHook(() =>
            useProcessingStatus({
                ticker: 'AAPL',
                enabled: true,
                pollingInterval: 1000
            })
        )

        expect(result.current.isPolling).toBe(false)

        // Wait for initial fetch
        await waitFor(() => {
            expect(apiClient.get).toHaveBeenCalledWith('/companies/AAPL/status')
        })
    })

    test('stops polling when processing is complete', async () => {
        const mockCompleteStatus = {
            ticker: 'AAPL',
            phase: 'complete',
            progress: 100,
            documentsFound: 10,
            documentsProcessed: 10,
            chunksCreated: 150,
            chunksVectorized: 150,
            startedAt: new Date().toISOString(),
            completedAt: new Date().toISOString()
        }

        vi.mocked(apiClient.get).mockResolvedValue({ data: mockCompleteStatus })

        const { result } = renderHook(() =>
            useProcessingStatus({
                ticker: 'AAPL',
                enabled: true,
                pollingInterval: 1000
            })
        )

        await waitFor(() => {
            expect(apiClient.get).toHaveBeenCalled()
        })

        // Polling should stop when complete
        expect(result.current.isPolling).toBe(false)
    })

    test('handles cancellation correctly', async () => {
        vi.mocked(apiClient.post).mockResolvedValue({})

        const { result } = renderHook(() =>
            useProcessingStatus({
                ticker: 'AAPL',
                enabled: true
            })
        )

        await result.current.cancelProcessing('AAPL')

        expect(apiClient.post).toHaveBeenCalledWith('/companies/AAPL/cancel')
    })

    test('handles API errors gracefully', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => { })
        vi.mocked(apiClient.get).mockRejectedValue(new Error('API Error'))

        const { result } = renderHook(() =>
            useProcessingStatus({
                ticker: 'AAPL',
                enabled: true
            })
        )

        await waitFor(() => {
            expect(consoleError).toHaveBeenCalledWith('Failed to fetch processing status:', expect.any(Error))
        })

        consoleError.mockRestore()
    })

    test('does not start polling when disabled', () => {
        const { result } = renderHook(() =>
            useProcessingStatus({
                ticker: 'AAPL',
                enabled: false
            })
        )

        expect(result.current.isPolling).toBe(false)
        expect(apiClient.get).not.toHaveBeenCalled()
    })

    test('stops polling when ticker is removed', () => {
        const { result, rerender } = renderHook(
            ({ ticker }) => useProcessingStatus({ ticker, enabled: true }),
            { initialProps: { ticker: 'AAPL' } }
        )

        // Remove ticker
        rerender({ ticker: undefined })

        expect(result.current.isPolling).toBe(false)
    })
})
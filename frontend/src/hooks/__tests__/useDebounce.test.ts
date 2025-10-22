import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDebounce } from '../useDebounce'

describe('useDebounce', () => {
    beforeEach(() => {
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('returns initial value immediately', () => {
        const { result } = renderHook(() => useDebounce('initial', 500))

        expect(result.current).toBe('initial')
    })

    it('debounces value changes', () => {
        const { result, rerender } = renderHook(
            ({ value, delay }) => useDebounce(value, delay),
            {
                initialProps: { value: 'initial', delay: 500 }
            }
        )

        expect(result.current).toBe('initial')

        // Change the value
        rerender({ value: 'updated', delay: 500 })

        // Value should not change immediately
        expect(result.current).toBe('initial')

        // Fast-forward time
        act(() => {
            vi.advanceTimersByTime(500)
        })

        // Now the value should be updated
        expect(result.current).toBe('updated')
    })

    it('cancels previous timeout when value changes quickly', () => {
        const { result, rerender } = renderHook(
            ({ value, delay }) => useDebounce(value, delay),
            {
                initialProps: { value: 'initial', delay: 500 }
            }
        )

        // Change value multiple times quickly
        rerender({ value: 'first', delay: 500 })
        act(() => {
            vi.advanceTimersByTime(200)
        })

        rerender({ value: 'second', delay: 500 })
        act(() => {
            vi.advanceTimersByTime(200)
        })

        rerender({ value: 'final', delay: 500 })

        // Value should still be initial
        expect(result.current).toBe('initial')

        // Complete the debounce period
        act(() => {
            vi.advanceTimersByTime(500)
        })

        // Should have the final value, not intermediate ones
        expect(result.current).toBe('final')
    })

    it('works with different delay values', () => {
        const { result, rerender } = renderHook(
            ({ value, delay }) => useDebounce(value, delay),
            {
                initialProps: { value: 'initial', delay: 1000 }
            }
        )

        rerender({ value: 'updated', delay: 1000 })

        // Should not update after 500ms
        act(() => {
            vi.advanceTimersByTime(500)
        })
        expect(result.current).toBe('initial')

        // Should update after 1000ms
        act(() => {
            vi.advanceTimersByTime(500)
        })
        expect(result.current).toBe('updated')
    })
})
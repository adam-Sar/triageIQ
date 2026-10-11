import { useCallback, useEffect, useRef, useState } from 'react'

/** Polls an async fetcher on an interval; returns data plus a manual refresh. */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  const refresh = useCallback(async () => {
    try {
      setData(await fetcherRef.current())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = setInterval(() => void refresh(), intervalMs)
    return () => clearInterval(timer)
  }, [refresh, intervalMs])

  return { data, error, refresh }
}

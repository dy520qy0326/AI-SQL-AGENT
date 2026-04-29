import { useState, useEffect, useCallback } from 'react'

type Theme = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme'
const STORAGE = (typeof window !== 'undefined' ? window.localStorage : null) as Storage | null

function getInitialTheme(): Theme {
  const stored = STORAGE?.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return 'system'
}

function getSystemPref(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(resolved: 'light' | 'dark') {
  const root = document.documentElement
  if (resolved === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  const resolved: 'light' | 'dark' =
    theme === 'system' ? (getSystemPref() ? 'dark' : 'light') : theme

  const setTheme = useCallback((t: Theme) => {
    STORAGE?.setItem(STORAGE_KEY, t)
    setThemeState(t)
  }, [])

  const toggle = useCallback(() => {
    setTheme(resolved === 'dark' ? 'light' : 'dark')
  }, [resolved, setTheme])

  // Apply theme on change
  useEffect(() => {
    applyTheme(resolved)
  }, [resolved])

  // Listen to system preference changes (only when theme === 'system')
  useEffect(() => {
    if (theme !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme(mq.matches ? 'dark' : 'light')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  return { theme, resolved, setTheme, toggle } as const
}

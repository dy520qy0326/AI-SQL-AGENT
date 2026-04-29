import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/globals.css'

// Init theme before first paint to avoid flash
;(() => {
  const stored = localStorage.getItem('theme') as string | null
  let dark = false
  if (stored === 'dark') dark = true
  else if (stored === 'light') dark = false
  else dark = window.matchMedia('(prefers-color-scheme: dark)').matches
  if (dark) document.documentElement.classList.add('dark')
})()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

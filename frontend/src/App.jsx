import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'

import ComplaintForm from './components/ComplaintForm'
import Copilot from './components/Copilot'
import Ledger from './components/Ledger'
import { setLedger, setToast, toggleTheme } from './store/uiSlice'

export default function App() {
  const dispatch = useDispatch()
  const { theme, showLedger, toast } = useSelector((s) => s.ui)

  // One attribute on <html> drives every colour token in styles.css.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.style.colorScheme = theme
  }, [theme])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => dispatch(setToast(null)), 4000)
    return () => clearTimeout(id)
  }, [toast, dispatch])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">A</span>
          AIVOA
          <span className="brand-sub">Quality Management System</span>
        </div>
        <div className="topbar-spacer" />
        <button className="ghost-btn" onClick={() => dispatch(setLedger(true))}>
          QMS Ledger
        </button>
        <button
          className="ghost-btn icon-btn"
          onClick={() => dispatch(toggleTheme())}
          aria-label={'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode'}
          title={'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode'}
        >
          {theme === 'dark' ? '\u2600' : '\u263E'}
        </button>
      </header>

      <main className="panes">
        <ComplaintForm />
        <Copilot />
      </main>

      {showLedger && <Ledger />}
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}

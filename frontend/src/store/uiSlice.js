import { createSlice } from '@reduxjs/toolkit'

// Theme is resolved once, before first paint, so the app never flashes the wrong
// colours: stored choice first, then the OS setting.
const stored = localStorage.getItem('aivoa-theme')
const initialTheme =
  stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')

const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    theme: initialTheme,
    sessionId: 'sess-' + Math.random().toString(36).slice(2, 10),
    showTrace: false,
    showLedger: false,
    toast: null,
  },
  reducers: {
    toggleTheme(state) {
      state.theme = state.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('aivoa-theme', state.theme)
    },
    toggleTrace(state) {
      state.showTrace = !state.showTrace
    },
    setLedger(state, action) {
      state.showLedger = action.payload
    },
    setToast(state, action) {
      state.toast = action.payload
    },
  },
})

export const { toggleTheme, toggleTrace, setLedger, setToast } = uiSlice.actions
export default uiSlice.reducer

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Keeps the browser on one origin, so no CORS preflight in dev.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})

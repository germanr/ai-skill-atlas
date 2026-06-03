import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/ai-skill-atlas/',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5175,
    strictPort: false,
  },
  cacheDir: process.env.TEMP + '/vite-ai-skill-atlas',
})

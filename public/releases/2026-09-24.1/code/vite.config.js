import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { tmpdir } from 'os'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  // Use the same canonical path for the root and both HTML entry points,
  // including when PowerShell starts Vite through the C:\Dropbox junction.
  root: __dirname,
  base: '/',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5175,
    strictPort: false,
  },
  cacheDir: resolve(tmpdir(), 'vite-ai-skill-atlas'),
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        about: resolve(__dirname, 'about/index.html'),
      },
    },
  },
})

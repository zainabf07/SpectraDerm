import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI app already allows http://localhost:5173 in CORS, but proxying
// keeps the browser on a single origin so no CORS round trip is needed at all.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/health': { target, changeOrigin: true },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
      include: ['src/**/*.test.{js,jsx}'],
    },
  }
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En desarrollo, /api va al backend local. Se usa 127.0.0.1 y no localhost:
// en Windows localhost intenta primero IPv6 y uvicorn solo escucha en IPv4.
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})

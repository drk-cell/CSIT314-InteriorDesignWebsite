import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The dev server may sit behind a proxy on another port. tsc has no Node types
// here, so declare the one global the config reads.
declare const process: { env: Record<string, string | undefined> };

const API_TARGET = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/uploads': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  optimizeDeps: {
    // Do NOT force-rebundle on every start (avoids esbuild OOM on Windows)
    force: false,
    // Limit esbuild worker threads to reduce peak memory
    esbuildOptions: {
      target: 'es2020',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'es2020',
  },
});

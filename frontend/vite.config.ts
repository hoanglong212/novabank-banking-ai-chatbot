import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, '.', 'NOVABANK_DEV_').NOVABANK_DEV_API_TARGET?.trim();
  let apiProxy: string | { target: string; changeOrigin: boolean } = 'http://127.0.0.1:8080';

  if (target) {
    const invalid = 'NOVABANK_DEV_API_TARGET must be an HTTPS origin or an HTTP loopback origin.';
    let origin: URL;
    try {
      origin = new URL(target);
    } catch {
      throw new Error(invalid);
    }
    const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname);
    if ((origin.protocol !== 'https:' && !(origin.protocol === 'http:' && loopback)) ||
        origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
      throw new Error(invalid);
    }
    // Change Host so a shared HTTPS virtual host selects the right site.
    apiProxy = { target: origin.origin, changeOrigin: true };
  }

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: { '/api': apiProxy },
    },
  };
});

/**
 * Vite 开发与构建配置。
 *
 * 开发服务器把浏览器发往 `/api` 的请求转发给本地 FastAPI，并移除 `/api`
 * 前缀。例如 `/api/health` 最终请求后端的 `http://127.0.0.1:8000/health`。
 * 这样前端业务代码不需要硬编码后端地址，也不需要在当前阶段修改 CORS。
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

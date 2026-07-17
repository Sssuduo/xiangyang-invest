import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import ElementPlus from 'unplugin-element-plus/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    ElementPlus(),
    {
      name: 'inject-demand-button-style',
      transformIndexHtml(html) {
        return html.replace(
          '</head>',
          `<style>.demand-card-actions .el-button.is-link{font-weight:500}.demand-card-actions .el-button--primary.is-link{color:#409eff !important}.demand-card-actions .el-button--danger.is-link{color:#f56c6c !important}.demand-card-actions .el-button.is-link .el-icon{color:inherit}</style></head>`
        )
      }
    }
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err) => console.log('[Vite Proxy Error]', err.message))
        }
      },
      '/static': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})

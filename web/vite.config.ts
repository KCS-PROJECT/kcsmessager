import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// KCS Talk 디자인 시스템 문서 (ui-styling: shadcn/ui + Tailwind)
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: { fs: { allow: ['..'] } },   // ../assets/design-tokens.* 사용
})

import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: [ "http://localhost:5173", "hisako-potatory-emile.ngrok-free.dev"]
  }
})
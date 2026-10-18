import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const DJANGO = process.env.DJANGO_URL || "http://127.0.0.1:8000";

// Desarrollo: la SPA vive en /app/ y todo lo demás (API, media, pantallas Django aún no migradas) va a Django.
// Producción: el build se sirve como estáticos de Django en /static/app/.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/app/" : "/app/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": `${import.meta.dirname}/src` } },
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "^/(?!app(/|$)).*": { target: DJANGO, changeOrigin: false } },
  },
}));

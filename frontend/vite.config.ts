import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { fileURLToPath } from "node:url";

const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export default defineConfig({
  resolve: { alias: { "@shared": fileURLToPath(new URL("../shared", import.meta.url)) } },
  server: { port: 5173, proxy: { "/api": backend, "/media": backend }, fs: { allow: [".."] } },
  preview: { port: 4173, proxy: { "/api": backend, "/media": backend } },
  build: { target: "es2020", chunkSizeWarningLimit: 400 },
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "Yme Jibu — Exploitation & Maintenance",
        short_name: "Yme Jibu E&M",
        lang: "fr",
        start_url: "/",
        display: "standalone",
        background_color: "#fcfcfb",
        theme_color: "#104281",
        icons: [{ src: "icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/media\//, /^\/admin\//],
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.hostname.endsWith("tile.openstreetmap.org"),
            handler: "CacheFirst",
            options: { cacheName: "osm-tiles", expiration: { maxEntries: 400, maxAgeSeconds: 30 * 24 * 3600 } },
          },
        ],
      },
    }),
  ],
});

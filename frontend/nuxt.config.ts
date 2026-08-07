import tailwindcss from "@tailwindcss/vite";
import process from "node:process";

const apiProxyTarget = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";

export default defineNuxtConfig({
  modules: ["@nuxt/ui"],

  components: [
    { path: "~/components/cards", pathPrefix: false },
    { path: "~/components/buttons", pathPrefix: false },
    { path: "~/components/modals", pathPrefix: false },
    { path: "~/components/layout", pathPrefix: false },
    "~/components",
  ],

  devtools: { enabled: false },
  css: ["~/assets/css/main.css"],
  ssr: false,
  sourcemap: {
    client: true,
    server: false,
  },
  vite: {
    logLevel: "error",
    server: {
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
    build: {
      sourcemap: true,
      modulePreload: {
        polyfill: false,
      },
    },
    css: {
      devSourcemap: true,
    },
  },
  app: {
    head: {
      title: "Shiori Keeper",
      meta: [
        {
          name: "viewport",
          content: "width=device-width, initial-scale=1",
        },
      ],
    },
  },
  compatibilityDate: "2025-04-07",
});

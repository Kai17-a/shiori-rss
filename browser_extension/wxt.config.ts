import { defineConfig } from "wxt";
import tailwindcss from "@tailwindcss/vite";

// See https://wxt.dev/api/config.html
export default defineConfig({
  vite: () => ({
    plugins: [tailwindcss()],
  }),
  modules: ["@wxt-dev/module-vue"],
  manifest: {
    name: "Shiori Keeper",
    version: "0.1.0",
    description: "An extension for Shiori Keeper.",
    action: {
      default_popup: "popup.html",
      default_title: "Shiori Keeper",
    },
    permissions: ["tabs", "storage"],
    host_permissions: ["<all_urls>"],
    content_security_policy: {},
  },
});

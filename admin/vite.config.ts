import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const adminDir = dirname(fileURLToPath(import.meta.url));
const serverAdminDir = resolve(adminDir, "../server/admin");

export default defineConfig({
  plugins: [
    vue(),
    {
      name: "log-server-outdir",
      closeBundle() {
        console.log(`\n后台已输出到 ${serverAdminDir}`);
        console.log("git add / commit / push 即可，不用再拷文件。\n");
      },
    },
  ],
  build: {
    outDir: serverAdminDir,
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/uploads": "http://127.0.0.1:8010",
    },
  },
});

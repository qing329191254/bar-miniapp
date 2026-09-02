import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

const adminDir = dirname(fileURLToPath(import.meta.url));
const serverAdminDir = resolve(adminDir, "../server/admin");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, adminDir, "");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8010";

  return {
    plugins: [
      vue(),
      {
        name: "log-server-outdir",
        closeBundle() {
          console.log(`\n后台已输出到 ${serverAdminDir}`);
          console.log("确认本地效果后再提交，无需手动复制文件。\n");
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
        "/api": { target: apiTarget, changeOrigin: true },
        "/uploads": { target: apiTarget, changeOrigin: true },
        "/ws": { target: apiTarget, changeOrigin: true, ws: true },
      },
    },
  };
});

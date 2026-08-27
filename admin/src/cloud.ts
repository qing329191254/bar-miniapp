import cloudbase from "@cloudbase/js-sdk";

const ENV_ID = import.meta.env.VITE_TCB_ENV || "prod-d2gc6jcwy846bd613";
const COS_PUBLIC_BASE = (
  import.meta.env.VITE_COS_PUBLIC_BASE ||
  "https://7072-prod-d2gc6jcwy846bd613-1476141553.cos.ap-shanghai.myqcloud.com"
).replace(/\/$/, "");
const COS_PREFIX = (import.meta.env.VITE_COS_PREFIX || "wanka/uploads/").replace(/^\//, "");

const ALLOWED = new Set([".jpg", ".jpeg", ".png", ".webp", ".gif"]);
const MAX_BYTES = 2 * 1024 * 1024;

let app: ReturnType<typeof cloudbase.init> | null = null;
let authReady: Promise<void> | null = null;

function tcb() {
  if (!app) app = cloudbase.init({ env: ENV_ID });
  return app;
}

async function ensureAuth() {
  if (!authReady) {
    authReady = (async () => {
      const auth = tcb().auth({ persistence: "local" });
      if (!(await auth.getLoginState())) {
        await auth.signInAnonymously();
      }
    })();
  }
  try {
    await authReady;
  } catch {
    authReady = null;
    throw new Error(
      "云存储登录失败：请在微信云开发控制台 → 登录授权 中开启「匿名登录」，并允许上传 wanka/uploads/",
    );
  }
}

function extOf(file: File) {
  const m = (file.name || "").match(/\.[^.]+$/);
  let ext = (m ? m[0] : ".jpg").toLowerCase();
  if (ext === ".jpeg") ext = ".jpg";
  return ext;
}

function publicUrl(cloudPath: string) {
  return `${COS_PUBLIC_BASE}/${cloudPath}`;
}

export async function uploadToCloud(file: File): Promise<string> {
  const ext = extOf(file);
  if (!ALLOWED.has(ext)) throw new Error("仅支持 jpg / png / webp / gif");
  if (file.size > MAX_BYTES) throw new Error("图片需 ≤ 2MB");

  await ensureAuth();
  const name = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}${ext}`;
  const cloudPath = `${COS_PREFIX}${name}`;

  const res = await tcb().uploadFile({
    cloudPath,
    filePath: file,
  });
  if (!res?.fileID) throw new Error("上传失败，未返回 fileID");
  return publicUrl(cloudPath);
}

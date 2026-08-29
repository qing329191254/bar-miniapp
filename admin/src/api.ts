const TOKEN_KEY = "wanka_admin_token";
const USER_KEY = "wanka_admin_user";

export function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function savedUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setSession(t: string, user: unknown) {
  localStorage.setItem(TOKEN_KEY, t);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function api<T = any>(
  path: string,
  opts: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const res = await fetch("/api" + path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: "Bearer " + token() } : {}),
    },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = (data as { detail?: unknown }).detail;
    throw new Error(typeof d === "string" ? d : res.statusText);
  }
  return data as T;
}

export type PageResult<T> = { items: T[]; total: number; page: number; pageSize: number };

export function pageQs(page: number, pageSize: number, extra?: Record<string, string | number | undefined>) {
  const q = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (extra) {
    for (const [k, v] of Object.entries(extra)) {
      if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
    }
  }
  return q.toString();
}

export async function uploadFile(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/admin/upload", {
    method: "POST",
    headers: token() ? { Authorization: "Bearer " + token() } : {},
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : "图片上传失败");
  }
  const url = (data as { url?: unknown }).url;
  if (typeof url !== "string" || !url) throw new Error("服务端未返回图片地址");
  return url;
}

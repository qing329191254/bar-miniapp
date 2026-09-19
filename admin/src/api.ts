import { ref } from "vue";

const TOKEN_KEY = "wanka_admin_token";
const USER_KEY = "wanka_admin_user";

function readStoredUser(): any {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Reactive session — App sidebar/menus depend on this updating after login. */
export const sessionToken = ref(localStorage.getItem(TOKEN_KEY) || "");
export const sessionUser = ref<any>(readStoredUser());

export function token() {
  return sessionToken.value || localStorage.getItem(TOKEN_KEY) || "";
}

export function savedUser() {
  return sessionUser.value;
}

export function setSession(t: string, user: unknown) {
  localStorage.setItem(TOKEN_KEY, t);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  sessionToken.value = t;
  sessionUser.value = user;
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  sessionToken.value = "";
  sessionUser.value = null;
}

const LOGIN_NOTICE_KEY = "wanka_admin_login_notice";
let redirectingToLogin = false;

/** One-shot message shown on the login page after a forced sign-out. */
export function takeLoginNotice(): string {
  const msg = sessionStorage.getItem(LOGIN_NOTICE_KEY) || "";
  if (msg) sessionStorage.removeItem(LOGIN_NOTICE_KEY);
  return msg;
}

function kickToLogin() {
  const hadSession = !!token();
  clearSession();
  if (!hadSession || redirectingToLogin) return;
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/") return;
  redirectingToLogin = true;
  sessionStorage.setItem(LOGIN_NOTICE_KEY, "登录已过期，请重新登录");
  window.location.assign("/");
}

function errorDetail(data: unknown, fallback: string) {
  const detail = (data as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : fallback;
}

function rejectHttp(path: string, res: Response, data: unknown, fallback: string): never {
  const isLogin = path.split("?")[0] === "/auth/login";
  if (res.status === 401 && !isLogin) kickToLogin();
  throw new Error(errorDetail(data, fallback));
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
  if (!res.ok) rejectHttp(path, res, data, res.statusText || "请求失败");
  return data as T;
}

export const DEFAULT_PAGE_SIZE = 15;

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
  if (!res.ok) rejectHttp("/admin/upload", res, data, "图片上传失败");
  const url = (data as { url?: unknown }).url;
  if (typeof url !== "string" || !url) throw new Error("服务端未返回图片地址");
  return url;
}

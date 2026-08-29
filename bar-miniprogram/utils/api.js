import { reactive } from "vue";

/** 微信云托管 API 公网地址（小程序与 Web 后台均对接此云端数据） */
export const BASE = "https://api-303869-11-1476141553.sh.run.tcloudbase.com";
export const CLOUD_ENV = "prod-d2gc6jcwy846bd613";
export const CLOUD_SERVICE = "api";

export function media(url) {
  if (!url) return "";
  const value = String(url).trim();
  if (/^https?:\/\//.test(value) || value.startsWith("data:")) return value;
  if (value.startsWith("/")) return BASE.replace(/\/$/, "") + value;
  // Legacy seed values such as "ipa.jpg" were never real deployed files.
  return "";
}

const TOKEN_KEY = "wanka_token";
const USER_KEY = "wanka_user";

export function token() {
  return uni.getStorageSync(TOKEN_KEY) || "";
}

export function savedUser() {
  return uni.getStorageSync(USER_KEY) || null;
}

export function setSession(t, user) {
  uni.setStorageSync(TOKEN_KEY, t);
  uni.setStorageSync(USER_KEY, user);
}

export function clearSession() {
  uni.removeStorageSync(TOKEN_KEY);
  uni.removeStorageSync(USER_KEY);
}

const CART_KEY = "wanka_cart";
let redirectingToLogin = false;
const pendingRequests = new Map();
let loadingCount = 0;
let loadingTimer = null;
let loadingShown = false;

function beginLoading() {
  loadingCount += 1;
  if (loadingCount !== 1) return;
  loadingTimer = setTimeout(() => {
    if (!loadingCount) return;
    loadingShown = true;
    uni.showLoading({ title: "加载中", mask: true });
  }, 180);
}

function finishLoading() {
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount) return;
  if (loadingTimer) {
    clearTimeout(loadingTimer);
    loadingTimer = null;
  }
  if (loadingShown) {
    uni.hideLoading();
    loadingShown = false;
  }
}

function requestKey(path, opts) {
  return `${(opts.method || "GET").toUpperCase()} ${path} ${JSON.stringify(opts.body || {})}`;
}

export function loadCart() {
  const raw = uni.getStorageSync(CART_KEY);
  if (!Array.isArray(raw)) return [];
  return raw.filter((x) => x && Number(x.pid) > 0 && Number(x.qty) > 0).map((x) => ({
    pid: Number(x.pid),
    qty: Math.min(99, Math.floor(Number(x.qty))),
    specIds: Array.isArray(x.specIds) ? x.specIds.map(Number).filter(Number.isFinite) : [],
  }));
}

export function saveCart(lines) {
  uni.setStorageSync(CART_KEY, lines || []);
}

function detailMsg(data) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) {
    return d.map((x) => x.msg || x.message).filter(Boolean).join("；") || "请求失败";
  }
  return "请求失败";
}

function canUseCloudContainer() {
  return typeof wx !== "undefined" && wx.cloud && typeof wx.cloud.callContainer === "function";
}

function parseResponse(res, method, opts, finish, resolve, reject) {
  let data = res.data;
  if (typeof data === "string") {
    try {
      data = JSON.parse(data);
    } catch (e) {
      data = {};
    }
  }
  data = data || {};
  const statusCode = res.statusCode;
  if (statusCode >= 200 && statusCode < 300) {
    finish();
    resolve(data);
    return;
  }
  if (statusCode === 401 && token()) {
    clearSession();
    if (!redirectingToLogin) {
      redirectingToLogin = true;
      uni.reLaunch({
        url: "/pages/login/login",
        complete: () => { redirectingToLogin = false; },
      });
    }
    finish();
    reject(new Error("登录已过期，请重新登录"));
    return;
  }
  const error = new Error(detailMsg(data));
  if (method === "GET" && opts.silent !== true) {
    toastText(error.message);
  }
  finish();
  reject(error);
}

function requestFailMessage(err) {
  const raw = String(err?.errMsg || err?.message || "");
  if (raw.includes("timeout")) return "请求超时，请稍后重试";
  return "连不上云端服务";
}

function requestViaHttp(path, opts, method, finish, resolve, reject) {
  const url = BASE.replace(/\/$/, "") + "/api" + path;
  uni.request({
    url,
    method,
    data: opts.body === undefined ? undefined : opts.body,
    header: {
      "content-type": "application/json",
      ...(token() ? { Authorization: "Bearer " + token() } : {}),
    },
    timeout: 60000,
    success(res) {
      parseResponse(res, method, opts, finish, resolve, reject);
    },
    fail(err) {
      const message = requestFailMessage(err);
      if (method === "GET" && opts.silent !== true) {
        toastText(message);
      }
      finish();
      reject(new Error(message));
    },
  });
}

function requestViaCloud(path, opts, method, finish, resolve, reject) {
  wx.cloud.init({ env: CLOUD_ENV, traceUser: true });
  wx.cloud.callContainer({
    config: { env: CLOUD_ENV },
    path: "/api" + path,
    method,
    header: {
      "content-type": "application/json",
      "X-WX-SERVICE": CLOUD_SERVICE,
      ...(token() ? { Authorization: "Bearer " + token() } : {}),
    },
    data: opts.body === undefined ? {} : opts.body,
    timeout: 60000,
    success(res) {
      parseResponse(res, method, opts, finish, resolve, reject);
    },
    fail(err) {
      // 云托管通道失败时，改走云托管 HTTPS 公网地址（仍是同一套云端数据）
      requestViaHttp(path, opts, method, finish, resolve, reject);
    },
  });
}

export function api(path, opts = {}) {
  const key = requestKey(path, opts);
  if (pendingRequests.has(key)) return pendingRequests.get(key);

  const withLoading = opts.loading !== false;
  if (withLoading) beginLoading();
  const request = new Promise((resolve, reject) => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      if (withLoading) finishLoading();
    };
    const method = (opts.method || "GET").toUpperCase();
    if (canUseCloudContainer()) {
      requestViaCloud(path, opts, method, finish, resolve, reject);
      return;
    }
    requestViaHttp(path, opts, method, finish, resolve, reject);
  });
  pendingRequests.set(key, request);
  request.then(
    () => pendingRequests.delete(key),
    () => pendingRequests.delete(key),
  );
  return request;
}

export function go(url, replace) {
  if (replace) uni.redirectTo({ url });
  else uni.navigateTo({ url });
}

export const toastStore = reactive({
  visible: false,
  message: "",
  fading: false,
});

let toastTimer = null;
let fadeTimer = null;

export function toastText(message, duration = 2200) {
  const text = String(message || "操作失败").replace(/\s+/g, " ").trim();
  if (toastTimer) clearTimeout(toastTimer);
  if (fadeTimer) clearTimeout(fadeTimer);
  toastStore.fading = false;
  toastStore.message = text;
  toastStore.visible = true;
  toastTimer = setTimeout(() => {
    toastStore.fading = true;
    fadeTimer = setTimeout(() => {
      toastStore.visible = false;
      toastStore.fading = false;
      toastTimer = null;
      fadeTimer = null;
    }, 320);
  }, duration);
}

export function relaunch(url) {
  uni.reLaunch({ url });
}

const DRAFT_KEY = "wanka_game_draft";
const DRAFT_TTL = 24 * 60 * 60 * 1000;

export function loadGameDraft() {
  const draft = uni.getStorageSync(DRAFT_KEY) || null;
  if (!draft) return null;

  // 兼容升级前保存的草稿：首次读取时从当前时间开始计算有效期。
  if (!draft.savedAt) {
    draft.savedAt = Date.now();
    uni.setStorageSync(DRAFT_KEY, draft);
  }
  if (Date.now() - Number(draft.savedAt) >= DRAFT_TTL) {
    uni.removeStorageSync(DRAFT_KEY);
    return null;
  }
  return draft;
}

export function saveGameDraft(wiz) {
  if (!wiz || !wiz.step || wiz.step >= 5) {
    uni.removeStorageSync(DRAFT_KEY);
    return;
  }
  uni.setStorageSync(DRAFT_KEY, { ...wiz, savedAt: Date.now() });
}

export function clearGameDraft() {
  uni.removeStorageSync(DRAFT_KEY);
}

export function hideWxHomeButton() {
  // #ifdef MP-WEIXIN
  if (typeof uni.hideHomeButton === "function") {
    uni.hideHomeButton();
  }
  // #endif
}

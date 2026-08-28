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
    if (typeof wx === "undefined" || !wx.cloud) {
      finish();
      reject(new Error("请在微信开发者工具中打开"));
      return;
    }
    wx.cloud.init({ env: CLOUD_ENV });
    const method = (opts.method || "GET").toUpperCase();
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
        let data = res.data;
        if (typeof data === "string") {
          try {
            data = JSON.parse(data);
          } catch (e) {
            data = {};
          }
        }
        data = data || {};
        if (res.statusCode >= 200 && res.statusCode < 300) {
          finish();
          resolve(data);
          return;
        }
        if (res.statusCode === 401 && token()) {
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
          uni.showToast({ title: error.message, icon: "none" });
        }
        finish();
        reject(error);
      },
      fail(err) {
        const message = err?.errMsg?.includes("timeout") ? "请求超时，请稍后重试" : "连不上云端服务";
        if (method === "GET" && opts.silent !== true) {
          uni.showToast({ title: message, icon: "none" });
        }
        finish();
        reject(new Error(message));
      },
    });
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

export function relaunch(url) {
  uni.reLaunch({ url });
}

const DRAFT_KEY = "wanka_game_draft";

export function loadGameDraft() {
  return uni.getStorageSync(DRAFT_KEY) || null;
}

export function saveGameDraft(wiz) {
  if (!wiz || !wiz.step || wiz.step >= 5) {
    uni.removeStorageSync(DRAFT_KEY);
    return;
  }
  uni.setStorageSync(DRAFT_KEY, wiz);
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

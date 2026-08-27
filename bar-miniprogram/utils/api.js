export const BASE = "https://api-303869-11-1476141553.sh.run.tcloudbase.com";
export const CLOUD_ENV = "prod-d2gc6jcwy846bd613";
export const CLOUD_SERVICE = "api";

export function media(url) {
  if (!url) return "";
  if (/^https?:\/\//.test(url) || String(url).startsWith("data:")) return url;
  return BASE + url;
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

function detailMsg(data) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) {
    return d.map((x) => x.msg || x.message).filter(Boolean).join("；") || "请求失败";
  }
  return "请求失败";
}

export function api(path, opts = {}) {
  return new Promise((resolve, reject) => {
    if (typeof wx === "undefined" || !wx.cloud) {
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
          resolve(data);
          return;
        }
        reject(new Error(detailMsg(data)));
      },
      fail() {
        reject(new Error("连不上云端服务"));
      },
    });
  });
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

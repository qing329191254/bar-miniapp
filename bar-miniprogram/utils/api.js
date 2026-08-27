export const BASE = "http://127.0.0.1:8010";

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

export function api(path, opts = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE + "/api" + path,
      method: opts.method || "GET",
      header: {
        "Content-Type": "application/json",
        ...(token() ? { Authorization: "Bearer " + token() } : {}),
      },
      data: opts.body,
      success(res) {
        const data = res.data || {};
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
          return;
        }
        const d = data.detail;
        reject(new Error(typeof d === "string" ? d : "请求失败"));
      },
      fail(e) {
        reject(new Error(e.errMsg || "网络错误"));
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

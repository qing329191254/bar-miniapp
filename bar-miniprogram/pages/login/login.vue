<script setup>
import { computed, onMounted, ref } from "vue";
import { api, savedUser, setSession, token, relaunch, toastText } from "@/utils/api";

const err = ref("");
const wxLoading = ref(false);
const smsLoading = ref(false);
const sending = ref(false);
const agreed = ref(false);
const agreementsReady = ref(false);
const showLogin = ref(false);
const showSms = ref(false);
const phone = ref("");
const smsCode = ref("");
const countdown = ref(0);
let countdownTimer = null;
const agreements = ref({
  terms: { ver: 1, title: "会员服务协议", text: "" },
  privacy: { ver: 1, title: "隐私政策", text: "" },
});
const openDoc = ref("");
const currentDoc = computed(() => agreements.value[openDoc.value] || {});

onMounted(async () => {
  const u = savedUser();
  if (u?.role && token()) {
    enter(u.role);
    return;
  }
  showLogin.value = true;
  try {
    const docs = await api("/agreements", { silent: true });
    agreements.value = {
      terms: { ...agreements.value.terms, ...(docs?.terms || {}) },
      privacy: { ...agreements.value.privacy, ...(docs?.privacy || {}) },
    };
    agreementsReady.value = true;
  } catch (e) {
    err.value = "协议加载失败，请稍后重试";
  }
});

function enter(role) {
  relaunch(role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo");
}

function ensureAgreed() {
  if (!agreementsReady.value) {
    toastText("协议加载失败，请重试");
    return false;
  }
  if (!agreed.value) {
    toastText("请先阅读并同意协议");
    return false;
  }
  return true;
}

function wxLogin(e) {
  if (wxLoading.value) return;
  if (!ensureAgreed()) return;
  const phoneCode = e?.detail?.code;
  if (!phoneCode) {
    err.value = "需要授权手机号才能登录";
    return;
  }
  err.value = "";
  wxLoading.value = true;
  uni.login({
    provider: "weixin",
    success: async (res) => {
      if (!res.code) {
        err.value = "未拿到微信登录码";
        wxLoading.value = false;
        return;
      }
      try {
        const r = await api("/auth/login", {
          method: "POST",
          body: {
            code: res.code,
            phoneCode,
            agreed: true,
            termsVersion: Number(agreements.value.terms.ver || 1),
            privacyVersion: Number(agreements.value.privacy.ver || 1),
          },
        });
        setSession(r.token, r.user);
        enter(r.user.role);
      } catch (e) {
        err.value = e.message;
      } finally {
        wxLoading.value = false;
      }
    },
    fail: (e) => {
      err.value = e.errMsg || "微信登录失败";
      wxLoading.value = false;
    },
  });
}

function loginTap() {
  ensureAgreed();
}

function startCountdown(sec) {
  countdown.value = sec;
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }, 1000);
}

async function sendSms() {
  if (sending.value || countdown.value > 0) return;
  if (!ensureAgreed()) return;
  const p = phone.value.trim();
  if (!/^1\d{10}$/.test(p)) {
    err.value = "请填写11位手机号";
    return;
  }
  err.value = "";
  sending.value = true;
  try {
    const r = await api("/auth/sms/send", { method: "POST", body: { phone: p }, loading: false });
    startCountdown(60);
    if (r?.mock && r.debugCode) {
      smsCode.value = r.debugCode;
      toastText("本地调试：验证码已填入");
    } else {
      toastText("验证码已发送");
    }
  } catch (e) {
    err.value = e.message;
  } finally {
    sending.value = false;
  }
}

function wxCode() {
  return new Promise((resolve) => {
    uni.login({
      provider: "weixin",
      success: (res) => resolve(res.code || ""),
      fail: () => resolve(""),
    });
  });
}

async function smsLogin() {
  if (smsLoading.value) return;
  if (!ensureAgreed()) return;
  const p = phone.value.trim();
  const c = smsCode.value.trim();
  if (!/^1\d{10}$/.test(p)) {
    err.value = "请填写11位手机号";
    return;
  }
  if (!c) {
    err.value = "请输入验证码";
    return;
  }
  err.value = "";
  smsLoading.value = true;
  try {
    const code = await wxCode();
    const r = await api("/auth/login", {
      method: "POST",
      body: {
        phone: p,
        smsCode: c,
        code,
        agreed: true,
        termsVersion: Number(agreements.value.terms.ver || 1),
        privacyVersion: Number(agreements.value.privacy.ver || 1),
      },
    });
    setSession(r.token, r.user);
    enter(r.user.role);
  } catch (e) {
    err.value = e.message;
  } finally {
    smsLoading.value = false;
  }
}
</script>

<template>
  <page-meta :page-style="`overflow:${openDoc ? 'hidden' : 'visible'}`" />
  <view v-if="!showLogin" class="login-boot" />
  <view v-else class="login-page">
    <view class="profile-hd login-hd">
      <image class="login-logo" src="/static/logo.png" mode="aspectFit" />
      <view class="login-name">玩咖桌游酒吧</view>
    </view>

    <view class="card login-card">
      <button
        class="btn block login-act"
        :open-type="agreed && agreementsReady ? 'getPhoneNumber' : ''"
        :disabled="wxLoading || smsLoading"
        @tap="loginTap"
        @getphonenumber="wxLogin"
      >
        <text>{{ wxLoading ? "登录中…" : "一键登录" }}</text>
      </button>
      <button class="btn ghost block login-act" :disabled="wxLoading || smsLoading" @tap="showSms = !showSms">
        <text>{{ showSms ? "收起验证码登录" : "手机号验证码登录" }}</text>
      </button>
      <view v-if="showSms" class="sms-box">
        <input
          class="login-inp"
          v-model="phone"
          type="number"
          maxlength="11"
          placeholder="请输入手机号"
          placeholder-class="login-ph"
        />
        <view class="sms-row">
          <input
            class="login-inp sms-code"
            v-model="smsCode"
            type="number"
            maxlength="6"
            placeholder="验证码"
            placeholder-class="login-ph"
          />
          <button class="btn ghost sms-send" :disabled="sending || countdown > 0" @tap="sendSms">
            {{ countdown > 0 ? countdown + "s" : sending ? "发送中" : "获取验证码" }}
          </button>
        </view>
        <button class="btn block login-act" :disabled="smsLoading || wxLoading" @tap="smsLogin">
          <text>{{ smsLoading ? "登录中…" : "验证码登录" }}</text>
        </button>
      </view>
      <view class="agreement-row" @tap="agreed = !agreed">
        <view class="agreement-check" :class="{ on: agreed }"><text v-if="agreed">✓</text></view>
        <text>我已阅读并同意</text>
        <text class="agreement-link" @tap.stop="openDoc = 'terms'">《会员服务协议》</text>
        <text>和</text>
        <text class="agreement-link" @tap.stop="openDoc = 'privacy'">《隐私政策》</text>
      </view>
    </view>

    <view class="err" v-if="err">{{ err }}</view>
    <view class="tiny login-tip">优先使用一键登录；无法授权手机号时可用短信验证码。员工由后台按手机号授权。</view>

    <view v-if="openDoc" class="agreement-mask" @tap="openDoc = ''" @touchmove.stop.prevent></view>
    <view v-if="openDoc" class="agreement-sheet">
      <view class="agreement-head"><text>{{ currentDoc.title }} v{{ currentDoc.ver }}</text><text class="agreement-close" @tap="openDoc = ''">关闭</text></view>
      <scroll-view scroll-y :show-scrollbar="false" class="agreement-body">
        <view v-if="currentDoc.text" class="agreement-text">{{ currentDoc.text }}</view>
        <view v-else class="agreement-empty">协议正文尚未配置，请联系商家</view>
      </scroll-view>
    </view>
    <app-toast />
  </view>
</template>

<style scoped>
.login-boot {
  min-height: 100vh;
  background: #f5f4f0;
}
.login-page { padding: 14px 14px 28px; }
.login-hd { margin-bottom: 14px; text-align: center; padding: 28px 16px 24px; }
.login-logo {
  width: 88px;
  height: 88px;
  display: block;
  margin: 0 auto 12px;
}
.login-name { font-size: 20px; font-weight: 600; letter-spacing: 1px; }
.login-card { padding: 16px; }
.login-act {
  height: 44px;
  padding: 0 !important;
  margin-left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 44px;
  box-sizing: border-box;
}
.login-act text {
  line-height: 44px;
}
.login-card .btn + .btn {
  margin-left: 0;
  margin-top: 12px;
}
.sms-box { margin-top: 14px; }
.login-inp {
  display: block;
  width: 100%;
  height: 44px;
  min-height: 44px;
  line-height: 44px;
  padding: 0 12px;
  margin-bottom: 10px;
  border: 1px solid rgba(28,27,25,.24);
  border-radius: 10px;
  background: #FAF9F5;
  font-size: 15px;
  color: #1C1B19;
  box-sizing: border-box;
}
.login-ph { color: #9C9A93; font-size: 15px; line-height: 44px; }
.sms-row { display: flex; gap: 8px; align-items: flex-start; }
.sms-code { flex: 1; min-width: 0; margin-bottom: 10px; }
.sms-send {
  height: 44px;
  margin: 0;
  padding: 0 10px !important;
  flex: none;
  width: 108px;
  font-size: 12px;
  line-height: 44px;
}
.login-tip {
  margin-top: 12px;
  text-align: center;
  color: #9C9A93;
  line-height: 1.6;
  padding: 0 8px;
}
.agreement-row { display:flex;align-items:center;justify-content:center;flex-wrap:wrap;margin-top:14px;color:#6b6a65;font-size:11px;line-height:1.8; }
.agreement-check { width:14px;height:14px;margin-right:5px;border:1px solid rgba(28,27,25,.3);border-radius:3px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;line-height:1;box-sizing:border-box; }
.agreement-check.on { border-color:#1c1b19;background:#1c1b19; }
.agreement-link { color:#185fa5; }
.agreement-mask { position:fixed;z-index:100;inset:0;background:rgba(0,0,0,.42); }
.agreement-sheet { position:fixed;z-index:101;left:0;right:0;bottom:0;padding:15px 16px calc(18px + env(safe-area-inset-bottom));border-radius:20px 20px 0 0;background:#fff;box-sizing:border-box; }
.agreement-head { display:flex;align-items:center;padding-bottom:11px;border-bottom:1px solid rgba(28,27,25,.12);font-size:15px;font-weight:600; }
.agreement-close { margin-left:auto;color:#9c9a93;font-size:12px;font-weight:400; }
.agreement-body { max-height:62vh;scrollbar-width:none; }
.agreement-body::-webkit-scrollbar { display:none;width:0;height:0; }
.agreement-text { padding:13px 0;color:#6b6a65;font-size:12px;line-height:1.8;white-space:pre-wrap; }
.agreement-empty { padding:36px 0;color:#9c9a93;font-size:12px;text-align:center; }
</style>

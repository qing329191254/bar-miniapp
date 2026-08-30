<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, setSession } from "../api";
import UiIcon from "../components/UiIcon.vue";

const router = useRouter();
const account = ref("");
const password = ref("");
const showPassword = ref(false);
const err = ref("");
const loading = ref(false);

async function submit() {
  const acc = account.value.trim();
  const pwd = password.value;
  if (!acc || !pwd) {
    err.value = "请输入账号和密码";
    return;
  }
  loading.value = true;
  err.value = "";
  try {
    const r = await api<any>("/auth/login", {
      method: "POST",
      body: { account: acc, password: pwd },
    });
    const role = r.user?.role;
    if (role === "CUSTOMER") {
      err.value = "会员账号请使用小程序登录";
      return;
    }
    if (role === "STAFF") {
      err.value = "店员请使用小程序店员端登录";
      return;
    }
    if (role !== "MANAGER" && role !== "BOSS") {
      err.value = "无管理后台权限";
      return;
    }
    setSession(r.token, r.user);
    router.replace("/dash");
  } catch (e: any) {
    err.value = e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Enter") submit();
}
</script>

<template>
  <div class="login-page">
    <div class="login-glow glow-one"></div>
    <div class="login-glow glow-two"></div>
    <div class="login-card">
      <div class="login-logo-wrap"><img class="login-logo" src="/logo.png" alt="玩咖桌游酒吧" /></div>
      <div class="login-kicker"><UiIcon name="sparkle" /> 门店运营中心</div>
      <h1 class="login-title">玩咖桌游酒吧 · 管理后台</h1>
      <p class="login-sub">欢迎回来，请使用店长或老板账号登录。</p>

      <label class="fld">账号</label>
      <input
        class="inp login-inp"
        v-model="account"
        placeholder="员工账号，如 900002"
        autocomplete="username"
        @keyup="onKey"
      />
      <label class="fld">密码</label>
      <div class="password-field">
        <input
          class="inp login-inp password-inp"
          v-model="password"
          :type="showPassword ? 'text' : 'password'"
          placeholder="登录密码"
          autocomplete="current-password"
          @keyup="onKey"
        />
        <button
          type="button"
          class="password-toggle"
          :aria-label="showPassword ? '隐藏密码' : '显示密码'"
          :title="showPassword ? '隐藏密码' : '显示密码'"
          @click="showPassword = !showPassword"
        >
          <svg v-if="showPassword" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 3l18 18M10.6 10.7a2 2 0 002.7 2.7M9.9 4.3A10.8 10.8 0 0112 4c5.5 0 9 5 9 5a15.4 15.4 0 01-2.1 2.5M6.2 6.2C4.2 7.5 3 9 3 9s3.5 5 9 5c1.2 0 2.3-.2 3.3-.6" />
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5z" />
            <circle cx="12" cy="12" r="2.5" />
          </svg>
        </button>
      </div>

      <p class="login-err" v-if="err">{{ err }}</p>

      <button class="btn login-btn" :disabled="loading" @click="submit">
        <span>{{ loading ? "正在登录…" : "进入管理后台" }}</span>
        <UiIcon v-if="!loading" name="arrowRight" />
      </button>

      <p class="login-hint tiny">
        不同角色将按权限展示可管理的业务内容
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  background:
    linear-gradient(rgba(255,255,255,.5) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.5) 1px,transparent 1px),
    radial-gradient(circle at 22% 18%,#FFF8EB 0%,transparent 33%),
    linear-gradient(145deg,#F5F1E9 0%,#EEE7DB 100%);
  background-size: 32px 32px,32px 32px,auto,auto;
}
.login-glow{position:absolute;border-radius:50%;filter:blur(1px);pointer-events:none;z-index:-1}
.glow-one{width:360px;height:360px;right:-90px;top:-110px;background:radial-gradient(circle,rgba(201,139,50,.23),rgba(201,139,50,0) 68%)}
.glow-two{width:320px;height:320px;left:-110px;bottom:-130px;background:radial-gradient(circle,rgba(99,72,41,.12),rgba(99,72,41,0) 68%)}
.login-card {
  width: 100%;
  max-width: 400px;
  position:relative;
  background: linear-gradient(155deg,rgba(255,255,255,.97),rgba(255,252,246,.95));
  border: 1px solid rgba(110,79,43,.14);
  border-radius: 22px;
  padding: 31px 30px 26px;
  box-shadow: 0 24px 65px rgba(68,48,26,.13),inset 0 1px 0 #fff;
  backdrop-filter:blur(16px);
}
.login-card::before{content:"";position:absolute;left:28px;right:28px;top:0;height:2px;background:linear-gradient(90deg,transparent,#D39A48,transparent)}
.login-logo-wrap{width:82px;height:82px;display:grid;place-items:center;margin:0 auto 14px;border:1px solid rgba(185,120,34,.16);border-radius:23px;background:linear-gradient(145deg,#fff,#FFF2DE);box-shadow:0 12px 26px rgba(111,72,24,.11),inset 0 1px 0 #fff}
.login-logo {
  width: 68px;
  height: 68px;
  display: block;
}
.login-kicker{display:flex;align-items:center;justify-content:center;gap:5px;margin-bottom:8px;color:#A56A1D;font-size:10px;font-weight:700;letter-spacing:1.5px}
.login-kicker .ui-icon{width:13px;height:13px}
.login-title {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 7px;
  text-align:center;
  letter-spacing:-.25px;
}
.login-sub {
  font-size: 12px;
  color: #958B7F;
  line-height: 1.6;
  margin-bottom: 24px;
  text-align:center;
}
.fld {
  display: block;
  font-size: 12px;
  color: #6b6a65;
  margin-bottom: 6px;
}
.login-inp {
  margin-bottom: 14px;
}
.password-field {
  position: relative;
  margin-bottom: 14px;
}
.password-inp {
  width: 100%;
  margin-bottom: 0;
  padding-right: 44px;
}
.password-toggle {
  position: absolute;
  top: 50%;
  right: 10px;
  width: 30px;
  height: 30px;
  padding: 5px;
  border: 0;
  background: transparent;
  color: #6b6a65;
  cursor: pointer;
  transform: translateY(-50%);
}
.password-toggle:hover { color: #1c1b19; }
.password-toggle svg {
  display: block;
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.login-err {
  color: #a32d2d;
  font-size: 12px;
  margin: -4px 0 12px;
  line-height: 1.5;
}
.login-btn {
  width: 100%;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:9px;
  padding: 11px 14px;
  font-weight: 600;
  margin-top:4px;
}
.login-btn .ui-icon{width:16px;height:16px;transition:transform .18s ease}
.login-btn:hover .ui-icon{transform:translateX(3px)}
.login-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.login-hint {
  margin-top: 14px;
  text-align: center;
  line-height: 1.6;
}
</style>

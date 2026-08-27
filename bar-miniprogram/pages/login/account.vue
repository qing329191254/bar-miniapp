<script setup>
import { ref } from "vue";
import { api, setSession, relaunch } from "@/utils/api";

const account = ref("");
const password = ref("");
const err = ref("");
const loading = ref(false);

async function submit() {
  const v = account.value.trim();
  const p = password.value;
  if (!v) {
    err.value = "请输入账号";
    return;
  }
  if (!/^\d+$/.test(v)) {
    err.value = "请输入数字账号";
    return;
  }
  if (!p) {
    err.value = "请输入密码";
    return;
  }
  err.value = "";
  loading.value = true;
  try {
    const r = await api("/auth/login", { method: "POST", body: { account: v, password: p } });
    setSession(r.token, r.user);
    relaunch(r.user.role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo");
  } catch (e) {
    err.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <view class="login-page">
    <view class="card login-card">
      <view class="lab">账号</view>
      <input
        class="login-inp"
        v-model="account"
        type="digit"
        maxlength="8"
        placeholder="请输入账号"
        placeholder-class="login-ph"
        confirm-type="next"
      />
      <view class="lab">密码</view>
      <input
        class="login-inp"
        v-model="password"
        password
        placeholder="请输入密码"
        placeholder-class="login-ph"
        confirm-type="done"
        @confirm="submit"
      />
      <button class="btn block login-btn" :disabled="loading" @tap="submit">
        <text>{{ loading ? "登录中…" : "登录" }}</text>
      </button>
    </view>
    <view class="err" v-if="err">{{ err }}</view>
  </view>
</template>

<style scoped>
.login-page { padding: 14px 14px 28px; }
.login-card { padding: 16px; }
.lab { font-size: 12px; color: #6B6A65; margin-bottom: 6px; }
.login-inp {
  display: block;
  width: 100%;
  height: 44px;
  min-height: 44px;
  line-height: 44px;
  padding: 0 12px;
  margin-bottom: 14px;
  border: 1px solid rgba(28,27,25,.24);
  border-radius: 10px;
  background: #FAF9F5;
  font-size: 15px;
  color: #1C1B19;
  box-sizing: border-box;
}
.login-ph { color: #9C9A93; font-size: 15px; line-height: 44px; }
.login-btn {
  height: 44px;
  margin-top: 4px;
  margin-left: 0;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 44px;
}
</style>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, setSession } from "../api";

const router = useRouter();
const account = ref("");
const password = ref("");
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
    <div class="login-card">
      <div class="login-dots">
        <span class="wdot" style="background:#E24B4A"></span>
        <span class="wdot" style="background:#FAC775"></span>
        <span class="wdot" style="background:#97C459"></span>
      </div>
      <h1 class="login-title">玩咖桌游酒吧 · 管理后台</h1>
      <p class="login-sub">店长 / 老板登录。资产负债与调账审批仅老板可见。</p>

      <label class="fld">账号</label>
      <input
        class="inp login-inp"
        v-model="account"
        placeholder="员工账号，如 900002"
        autocomplete="username"
        @keyup="onKey"
      />
      <label class="fld">密码</label>
      <input
        class="inp login-inp"
        v-model="password"
        type="password"
        placeholder="登录密码"
        autocomplete="current-password"
        @keyup="onKey"
      />

      <p class="login-err" v-if="err">{{ err }}</p>

      <button class="btn login-btn" :disabled="loading" @click="submit">
        {{ loading ? "登录中…" : "登录" }}
      </button>

      <p class="login-hint tiny">
        演示账号：900002 店长 · 900003 老板，密码 123456
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
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border: 1px solid rgba(28, 27, 25, 0.12);
  border-radius: 16px;
  padding: 28px 24px 24px;
  box-shadow: 0 8px 28px rgba(28, 27, 25, 0.06);
}
.login-dots {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
}
.login-title {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 8px;
}
.login-sub {
  font-size: 12px;
  color: #9c9a93;
  line-height: 1.6;
  margin-bottom: 20px;
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
.login-err {
  color: #a32d2d;
  font-size: 12px;
  margin: -4px 0 12px;
  line-height: 1.5;
}
.login-btn {
  width: 100%;
  padding: 11px 14px;
  font-weight: 600;
}
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

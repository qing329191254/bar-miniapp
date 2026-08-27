<script setup>
import { onMounted, ref } from "vue";
import { api, go, savedUser, setSession, relaunch } from "@/utils/api";

const err = ref("");
const wxLoading = ref(false);

onMounted(() => {
  const u = savedUser();
  if (u?.role) enter(u.role);
});

function enter(role) {
  relaunch(role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo");
}

function wxLogin() {
  if (wxLoading.value) return;
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
        const r = await api("/auth/login", { method: "POST", body: { code: res.code } });
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
</script>

<template>
  <view class="login-page">
    <view class="profile-hd login-hd">
      <view class="login-mark">玩</view>
      <view class="login-name">玩咖桌游酒吧</view>
    </view>

    <view class="card login-card">
      <button class="btn block login-act" :disabled="wxLoading" @tap="wxLogin">
        <text>{{ wxLoading ? "登录中…" : "一键登录" }}</text>
      </button>
      <button class="btn ghost block login-act" :disabled="wxLoading" @tap="go('/pages/login/account')">
        <text>账号登录</text>
      </button>
    </view>

    <view class="err" v-if="err">{{ err }}</view>
  </view>
</template>

<style scoped>
.login-page { padding: 14px 14px 28px; }
.login-hd { margin-bottom: 14px; text-align: center; padding: 28px 16px 24px; }
.login-mark {
  width: 54px; height: 54px; border-radius: 16px; margin: 0 auto 12px;
  background: linear-gradient(135deg,#BA7517,#F6C96A); color: #fff;
  font-size: 22px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
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
</style>

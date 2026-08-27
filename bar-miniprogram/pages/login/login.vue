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

function wxLogin(e) {
  if (wxLoading.value) return;
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
          body: { code: res.code, phoneCode },
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
</script>

<template>
  <view class="login-page">
    <view class="profile-hd login-hd">
      <image class="login-logo" src="/static/logo.png" mode="aspectFit" />
      <view class="login-name">玩咖桌游酒吧</view>
    </view>

    <view class="card login-card">
      <button
        class="btn block login-act"
        open-type="getPhoneNumber"
        :disabled="wxLoading"
        @getphonenumber="wxLogin"
      >
        <text>{{ wxLoading ? "登录中…" : "一键登录" }}</text>
      </button>
      <button class="btn ghost block login-act" :disabled="wxLoading" @tap="go('/pages/login/account')">
        <text>账号登录</text>
      </button>
    </view>

    <view class="err" v-if="err">{{ err }}</view>
    <view class="tiny login-tip">登录即表示同意绑定微信与手机号，用于会员身份识别与订单服务。</view>
  </view>
</template>

<style scoped>
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
.login-tip {
  margin-top: 12px;
  text-align: center;
  color: #9C9A93;
  line-height: 1.6;
  padding: 0 8px;
}
</style>

<script setup>
import { onLoad } from "@dcloudio/uni-app";
import {
  isStaffRole,
  relaunch,
  savedUser,
  setPortal,
  token,
} from "@/utils/api";
import { startStaffReminder, stopStaffReminder } from "@/utils/staff-reminder";

onLoad(() => {
  const u = savedUser();
  if (!u?.role || !token()) {
    relaunch("/pages/login/login");
    return;
  }
  if (!isStaffRole(u)) {
    setPortal("customer");
    relaunch("/pages/c/home");
  }
});

function pick(mode) {
  setPortal(mode);
  if (mode === "customer") {
    stopStaffReminder();
    relaunch("/pages/c/home");
    return;
  }
  startStaffReminder();
  relaunch("/pages/s/todo");
}
</script>

<template>
  <view class="portal-page">
    <view class="portal-hd">
      <image class="portal-logo" src="/static/logo.png" mode="aspectFit" />
      <view class="portal-name">玩咖桌游酒吧</view>
      <view class="portal-sub">请选择本次进入的端</view>
    </view>

    <view class="portal-card card">
      <button class="btn block portal-btn" @tap="pick('staff')">进入员工端</button>
      <button class="btn ghost block portal-btn" @tap="pick('customer')">进入会员端</button>
      <view class="tiny portal-tip">会员端可点单、充值与查看资产；员工端处理待办与核销。可在「我的」随时切换。</view>
    </view>
  </view>
</template>

<style scoped>
.portal-page {
  min-height: 100vh;
  padding: 14px 14px 28px;
  box-sizing: border-box;
  background: #f5f4f0;
}
.portal-hd {
  text-align: center;
  padding: 36px 16px 20px;
}
.portal-logo {
  width: 88px;
  height: 88px;
  display: block;
  margin: 0 auto 12px;
}
.portal-name {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #1c1b19;
}
.portal-sub {
  margin-top: 8px;
  font-size: 14px;
  color: #6b6962;
}
.portal-card {
  padding: 16px;
}
.portal-btn {
  height: 44px;
  margin-left: 0;
  line-height: 44px;
}
.portal-card .btn + .btn {
  margin-left: 0;
  margin-top: 12px;
}
.portal-tip {
  margin-top: 14px;
  text-align: center;
  color: #9c9a93;
  line-height: 1.5;
}
</style>

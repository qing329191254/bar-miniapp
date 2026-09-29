<script setup>
import { go, relaunch } from "@/utils/api";

defineProps({ text: { type: String, default: "登录后查看你的会员信息" } });
</script>

<template>
  <view class="gg">
    <view class="gg-card">
      <view class="gg-t">{{ text }}</view>
      <view class="gg-s">也可以先逛逛首页、菜单、店铺玩法和榜单</view>
      <button class="btn block gg-b" @tap="go('/pages/login/login')">去登录</button>
      <view class="gg-home" @tap="relaunch('/pages/c/home')">先逛逛</view>
    </view>
  </view>
</template>

<style scoped>
.gg {
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;
  z-index: 50;
  background: #F5F4F0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 28px;
}
.gg-card {
  width: 100%;
  box-sizing: border-box;
  background: #fff;
  border: 1px solid rgba(28,27,25,.1);
  border-radius: 16px;
  padding: 24px 18px 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(28,27,25,.05);
}
.gg-t { font-size: 15px; font-weight: 600; }
.gg-s { font-size: 12px; color: #9C9A93; margin: 6px 0 18px; }
.gg-home { font-size: 13px; color: #6B6A65; padding: 12px 0 2px; }
</style>

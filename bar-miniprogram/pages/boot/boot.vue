<script setup>
import { onLoad } from "@dcloudio/uni-app";
import { resolveHomeUrl, savedUser, token } from "@/utils/api";

onLoad(() => {
  const u = savedUser();
  const t = token();
  if (!u || !u.role || !t) {
    uni.reLaunch({ url: "/pages/login/login" });
    return;
  }
  uni.reLaunch({ url: resolveHomeUrl() });
});
</script>

<template>
  <view class="boot" />
</template>

<style scoped>
.boot {
  min-height: 100vh;
  background: #f5f4f0;
}
</style>

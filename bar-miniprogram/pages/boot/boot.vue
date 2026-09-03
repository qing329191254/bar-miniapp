<script setup>
import { onLoad } from "@dcloudio/uni-app";
import { savedUser, token } from "@/utils/api";

onLoad(() => {
  const u = savedUser();
  const t = token();
  if (!u || !u.role || !t) {
    uni.reLaunch({ url: "/pages/login/login" });
    return;
  }
  uni.reLaunch({
    url: u.role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo",
  });
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

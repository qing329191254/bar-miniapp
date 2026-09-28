<script setup>
import { onShow } from "@dcloudio/uni-app";
import { hideWxHomeButton, relaunch, resolveHomeUrl } from "@/utils/api";

/** Legacy entry: redirect into member shell (guest or logged-in). */
onShow(() => {
  hideWxHomeButton();
  relaunch(resolveHomeUrl());
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

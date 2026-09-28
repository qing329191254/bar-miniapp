<script setup>
import { onLoad } from "@dcloudio/uni-app";
import { resolveHomeUrl } from "@/utils/api";

onLoad(() => {
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

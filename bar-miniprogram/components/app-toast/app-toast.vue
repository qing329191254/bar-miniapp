<script setup>
import { toastStore } from "@/utils/api";
</script>

<template>
  <view v-if="toastStore.visible" class="app-toast-root">
    <view class="app-toast" :class="{ out: toastStore.fading }">{{ toastStore.message }}</view>
  </view>
</template>

<style scoped>
.app-toast-root {
  position: fixed;
  left: 50%;
  top: 22vh;
  transform: translateX(-50%);
  z-index: 9999;
  pointer-events: none;
  max-width: calc(100vw - 56px);
}
.app-toast {
  background: rgba(28, 27, 25, 0.92);
  color: #fff;
  font-size: 14px;
  line-height: 1.35;
  padding: 10px 18px;
  border-radius: 99px;
  box-shadow: 0 8px 20px rgba(28, 27, 25, 0.18);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  animation: toast-in 0.25s ease;
}
.app-toast.out {
  opacity: 0;
  transition: opacity 0.3s;
}
@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

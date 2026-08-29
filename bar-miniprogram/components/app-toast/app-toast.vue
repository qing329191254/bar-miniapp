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
  top: 56px;
  transform: translateX(-50%);
  z-index: 999;
  pointer-events: none;
  max-width: calc(100vw - 32px);
}
.app-toast {
  background: rgba(28, 27, 25, 0.92);
  color: #fff;
  font-size: 12.5px;
  padding: 9px 16px;
  border-radius: 20px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  text-align: center;
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

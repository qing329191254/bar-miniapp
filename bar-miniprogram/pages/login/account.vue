<script setup>
import { onMounted } from "vue";
import { relaunch } from "@/utils/api";

onMounted(() => {
  relaunch("/pages/login/login");
});
</script>

<template>
  <view />
</template>

<script setup lang="ts">
import { useToastState } from "../composables/useToast";

const toast = useToastState();
</script>

<template>
  <Transition name="app-toast">
    <div v-if="toast.visible" class="app-toast" :class="{ error: toast.error }">{{ toast.text }}</div>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{
  name: "up" | "down" | "trash";
  disabled?: boolean;
  title?: string;
}>();
</script>

<template>
  <button type="button" class="ico-btn" :class="{ danger: name === 'trash' }" :disabled="disabled" :title="title">
    <svg v-if="name === 'up'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <path d="M8 12.5V3.5M4.5 7L8 3.5 11.5 7" />
    </svg>
    <svg v-else-if="name === 'down'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <path d="M8 3.5v9M4.5 9L8 12.5 11.5 9" />
    </svg>
    <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3.5 4.5h9M6 4.5V3.2h4V4.5M5.2 4.5l.5 8.2h4.6l.5-8.2" />
    </svg>
  </button>
</template>

<style scoped>
.ico-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 7px;
  color: var(--ink2);
  cursor: pointer;
  flex: none;
}
.ico-btn:hover:not(:disabled) { background: #FAF9F5; color: var(--ink); }
.ico-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.ico-btn.danger { color: var(--red); }
.ico-btn.danger:hover:not(:disabled) { background: var(--redbg); }
.ico-btn svg { width: 14px; height: 14px; display: block; }
</style>

<script setup lang="ts">
defineProps<{
  name: "up" | "down" | "trash";
  disabled?: boolean;
  title?: string;
}>();
</script>

<template>
  <button type="button" class="ico-btn" :class="{ danger: name === 'trash' }" :disabled="disabled" :title="title">
    <svg v-if="name === 'up'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4.5 4.5h11" />
      <path d="M10 15.5V7M6.7 10.2 10 6.9l3.3 3.3" />
    </svg>
    <svg v-else-if="name === 'down'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4.5 15.5h11" />
      <path d="M10 4.5V13m-3.3-3.2 3.3 3.3 3.3-3.3" />
    </svg>
    <svg v-else viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 5.5h12M8 5.5V3.8h4v1.7M5.7 5.5l.7 10.2h7.2l.7-10.2" />
      <path d="M8.2 8.5v4.7M11.8 8.5v4.7" />
    </svg>
  </button>
</template>

<style scoped>
.ico-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: linear-gradient(180deg, #FFFFFF, #F5F3EC);
  border-radius: 9px;
  color: #625F57;
  cursor: pointer;
  flex: none;
  box-shadow: 0 1px 2px rgba(28, 27, 25, 0.06), inset 0 1px 0 rgba(255,255,255,.9);
  transition: transform .15s ease, border-color .15s ease, color .15s ease, background .15s ease, box-shadow .15s ease;
}
.ico-btn:hover:not(:disabled) {
  color: #8A5815;
  border-color: rgba(186,117,23,.42);
  background: linear-gradient(180deg, #FFFDF8, #FAEEDA);
  box-shadow: 0 3px 8px rgba(92,59,15,.13), inset 0 1px 0 #fff;
  transform: translateY(-1px);
}
.ico-btn:active:not(:disabled) { transform: translateY(0); box-shadow: inset 0 1px 2px rgba(28,27,25,.1); }
.ico-btn:disabled { opacity: 0.3; cursor: not-allowed; box-shadow: none; }
.ico-btn.danger { color: var(--red); background: linear-gradient(180deg, #FFF, #FFF7F7); }
.ico-btn.danger:hover:not(:disabled) { color: #7F1D1D; border-color: rgba(163,45,45,.35); background: var(--redbg); }
.ico-btn svg { width: 17px; height: 17px; display: block; }
</style>

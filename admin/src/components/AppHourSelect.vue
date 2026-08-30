<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: number;
    disabled?: boolean;
  }>(),
  { disabled: false },
);

const emit = defineEmits<{
  "update:modelValue": [v: number];
  change: [v: number];
}>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const hours = Array.from({ length: 24 }, (_, i) => i);

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
}

function pick(h: number) {
  emit("update:modelValue", h);
  emit("change", h);
  open.value = false;
}

function onDoc(e: MouseEvent) {
  if (!root.value?.contains(e.target as Node)) open.value = false;
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") open.value = false;
}

onMounted(() => {
  document.addEventListener("mousedown", onDoc);
  document.addEventListener("keydown", onKey);
});

onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onDoc);
  document.removeEventListener("keydown", onKey);
});
</script>

<template>
  <div ref="root" class="hour-sel" :class="{ open, disabled }">
    <button type="button" class="hour-sel-btn" :disabled="disabled" aria-haspopup="listbox" :aria-expanded="open" @click="toggle">
      {{ pad(modelValue) }}
      <span class="hour-sel-chev" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="14" height="14"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
    </button>
    <div v-if="open" class="hour-sel-menu" role="listbox" aria-label="选择小时">
      <button
        v-for="h in hours"
        :key="h"
        type="button"
        class="hour-sel-opt"
        :class="{ on: h === modelValue }"
        role="option"
        :aria-selected="h === modelValue"
        @click="pick(h)"
      >
        {{ pad(h) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.hour-sel {
  position: relative;
  flex: none;
}

.hour-sel-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 66px;
  min-width: 66px;
  padding: 8px 8px 8px 10px;
  border: 1px solid rgba(82, 59, 32, 0.18);
  border-right: 0;
  border-radius: 9px 0 0 9px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(74, 52, 28, 0.025);
}

.hour-sel-btn:hover:not(:disabled) {
  border-color: rgba(82, 59, 32, 0.3);
}

.hour-sel.open .hour-sel-btn,
.hour-sel-btn:focus {
  outline: none;
  border-color: rgba(185, 120, 34, 0.65);
  box-shadow: 0 0 0 3px rgba(185, 120, 34, 0.11);
}

.hour-sel.disabled .hour-sel-btn {
  opacity: 0.55;
  cursor: not-allowed;
}

.hour-sel-chev {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ink3);
  transition: transform 0.18s ease;
}

.hour-sel.open .hour-sel-chev {
  transform: rotate(180deg);
}

.hour-sel-menu {
  position: absolute;
  left: 0;
  top: calc(100% + 6px);
  z-index: 40;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 4px;
  width: 198px;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(28, 27, 25, 0.14);
}

.hour-sel-opt {
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--ink2);
  font: inherit;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  padding: 7px 0;
  cursor: pointer;
  text-align: center;
}

.hour-sel-opt:hover {
  background: #faf9f5;
}

.hour-sel-opt.on {
  background: var(--goldbg);
  color: var(--gold);
  font-weight: 600;
}
</style>

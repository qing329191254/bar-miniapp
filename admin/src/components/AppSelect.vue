<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

export type SelOpt = { value: any; label: string };

const props = withDefaults(
  defineProps<{
    modelValue: any;
    options: SelOpt[];
    disabled?: boolean;
    placeholder?: string;
  }>(),
  { placeholder: "请选择" },
);
const emit = defineEmits<{
  "update:modelValue": [v: any];
  change: [v: any];
}>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);

function same(a: any, b: any) {
  return a === b || (a == null && b == null);
}
const current = computed(() => props.options.find((o) => same(o.value, props.modelValue)));
const label = computed(() => current.value?.label || props.placeholder);

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
}
function pick(o: SelOpt) {
  emit("update:modelValue", o.value);
  emit("change", o.value);
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
  <div ref="root" class="sel" :class="{ open, disabled }">
    <button type="button" class="sel-btn" :disabled="disabled" @click="toggle">
      <span class="sel-label">{{ label }}</span>
      <span class="sel-chev">›</span>
    </button>
    <div v-if="open" class="sel-menu">
      <button
        v-for="(o, i) in options"
        :key="i"
        type="button"
        class="sel-opt"
        :class="{ on: same(o.value, modelValue) }"
        @click="pick(o)"
      >
        {{ o.label }}
      </button>
      <div v-if="!options.length" class="sel-empty">暂无选项</div>
    </div>
  </div>
</template>

<style scoped>
.sel {
  position: relative;
  width: 100%;
  margin-bottom: 8px;
}
.sel-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(28, 27, 25, 0.24);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  font-size: 13px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
}
.sel-btn:hover {
  border-color: rgba(28, 27, 25, 0.4);
}
.sel.open .sel-btn,
.sel-btn:focus {
  outline: none;
  border-color: rgba(186, 117, 23, 0.65);
  box-shadow: 0 0 0 3px rgba(186, 117, 23, 0.12);
}
.sel.disabled .sel-btn {
  opacity: 0.55;
  cursor: not-allowed;
}
.sel-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sel-chev {
  flex: none;
  font-size: 12px;
  color: var(--ink3);
  transform: rotate(90deg);
  transition: transform 0.18s ease;
  line-height: 1;
}
.sel.open .sel-chev {
  transform: rotate(-90deg);
}
.sel-menu {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  z-index: 30;
  background: #fff;
  border: 1px solid rgba(28, 27, 25, 0.12);
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 10px 28px rgba(28, 27, 25, 0.12);
  max-height: 240px;
  overflow: auto;
}
.sel-opt {
  display: block;
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  font: inherit;
  font-size: 13px;
  color: var(--ink);
  padding: 8px 10px;
  border-radius: 7px;
  cursor: pointer;
}
.sel-opt:hover {
  background: #FAF9F5;
}
.sel-opt.on {
  background: var(--goldbg);
  color: var(--gold);
  font-weight: 600;
}
.sel-empty {
  padding: 10px;
  font-size: 12px;
  color: var(--ink3);
  text-align: center;
}
</style>

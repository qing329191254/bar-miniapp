<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

export type SelOpt = { value: any; label: string };

const props = withDefaults(
  defineProps<{
    modelValue: any;
    options: SelOpt[];
    disabled?: boolean;
    placeholder?: string;
    compact?: boolean;
    noMargin?: boolean;
    action?: boolean;
  }>(),
  { placeholder: "请选择" },
);
const emit = defineEmits<{
  "update:modelValue": [v: any];
  change: [v: any];
}>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const menuStyle = ref<Record<string, string>>({});

function same(a: any, b: any) {
  return a === b || (a == null && b == null);
}
const current = computed(() => props.options.find((o) => same(o.value, props.modelValue)));
const label = computed(() => current.value?.label || props.placeholder);
const isPlaceholder = computed(() => !current.value);

function syncMenuPos() {
  const btn = root.value?.querySelector(".sel-btn") as HTMLElement | null;
  if (!btn) return;
  const r = btn.getBoundingClientRect();
  menuStyle.value = {
    position: "fixed",
    left: `${r.left}px`,
    top: `${r.bottom + 6}px`,
    width: `${r.width}px`,
    zIndex: "1100",
  };
}

function bindMenuPos() {
  syncMenuPos();
  window.addEventListener("resize", syncMenuPos);
  window.addEventListener("scroll", syncMenuPos, true);
}

function unbindMenuPos() {
  window.removeEventListener("resize", syncMenuPos);
  window.removeEventListener("scroll", syncMenuPos, true);
}

watch(open, async (v) => {
  if (v) {
    await nextTick();
    bindMenuPos();
  } else {
    unbindMenuPos();
  }
});

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
}
function pick(o: SelOpt) {
  if (!props.action) emit("update:modelValue", o.value);
  emit("change", o.value);
  open.value = false;
}
function onDoc(e: MouseEvent) {
  const t = e.target as Node;
  if (root.value?.contains(t)) return;
  if ((t as Element).closest?.(".sel-menu-portal")) return;
  open.value = false;
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
  unbindMenuPos();
});
</script>

<template>
  <div
    ref="root"
    class="sel"
    :class="{ open, disabled, compact, noMargin, placeholder: isPlaceholder }"
  >
    <button type="button" class="sel-btn" :disabled="disabled" aria-haspopup="listbox" :aria-expanded="open" @click="toggle">
      <span class="sel-label">{{ label }}</span>
      <span class="sel-chev" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="14" height="14">
          <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
    </button>
    <Teleport to="body">
      <div v-if="open" class="sel-menu sel-menu-portal" :class="{ compact }" :style="menuStyle" role="listbox">
        <button
          v-for="(o, i) in options"
          :key="i"
          type="button"
          class="sel-opt"
          :class="{ on: same(o.value, modelValue) }"
          role="option"
          :aria-selected="same(o.value, modelValue)"
          @click="pick(o)"
        >
          {{ o.label }}
        </button>
        <div v-if="!options.length" class="sel-empty">暂无选项</div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.sel {
  position: relative;
  width: 100%;
  margin-bottom: 8px;
}
.sel.noMargin {
  margin-bottom: 0;
}
.sel-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(82, 59, 32, 0.18);
  border-radius: 9px;
  padding: 8px 10px;
  font: inherit;
  font-size: 13px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  box-shadow: inset 0 1px 2px rgba(74, 52, 28, 0.025);
}
.sel.compact .sel-btn {
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 8px;
  gap: 4px;
}
.sel-btn:hover:not(:disabled) {
  border-color: rgba(82, 59, 32, 0.3);
}
.sel.open .sel-btn,
.sel-btn:focus {
  outline: none;
  border-color: rgba(185, 120, 34, 0.65);
  box-shadow: 0 0 0 3px rgba(185, 120, 34, 0.11);
}
.sel.disabled .sel-btn {
  opacity: 0.55;
  cursor: not-allowed;
}
.sel.placeholder .sel-label {
  color: var(--ink3);
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ink3);
  transition: transform 0.18s ease;
}
.sel.open .sel-chev {
  transform: rotate(180deg);
}
</style>

<style>
.sel-menu-portal {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 10px 28px rgba(28, 27, 25, 0.14);
  max-height: 240px;
  overflow: auto;
}
.sel-menu-portal .sel-opt {
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
.sel-menu-portal .sel-opt:hover {
  background: #faf9f5;
}
.sel-menu-portal .sel-opt.on {
  background: var(--goldbg);
  color: var(--gold);
  font-weight: 600;
}
.sel-menu-portal.compact .sel-opt {
  font-size: 12px;
  padding: 6px 8px;
}
.sel-menu-portal .sel-empty {
  padding: 10px;
  font-size: 12px;
  color: var(--ink3);
  text-align: center;
}
</style>

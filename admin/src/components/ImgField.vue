<script setup lang="ts">
import { computed, ref } from "vue";
import { uploadFile } from "../api";

const props = withDefaults(
  defineProps<{ modelValue?: string; size?: "sm" | "md"; actions?: boolean }>(),
  { modelValue: "", size: "sm", actions: false },
);
const emit = defineEmits<{ "update:modelValue": [v: string] }>();

const inp = ref<HTMLInputElement | null>(null);
const busy = ref(false);
const err = ref("");
const displayUrl = computed(() => /^(https?:\/\/|data:|\/uploads\/)/.test(props.modelValue || "") ? props.modelValue : "");

function pick() {
  if (busy.value) return;
  inp.value?.click();
}
async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  (e.target as HTMLInputElement).value = "";
  if (!file) return;
  err.value = "";
  busy.value = true;
  try {
    const url = await uploadFile(file);
    emit("update:modelValue", url);
  } catch (e: any) {
    err.value = e.message || "上传失败";
  } finally {
    busy.value = false;
  }
}
function clearImg() {
  err.value = "";
  emit("update:modelValue", "");
}
</script>

<template>
  <div class="imgf-wrap">
    <div class="imgf" :class="size" :title="displayUrl ? '点击更换图片' : '点击上传图片'" @click="pick">
      <img v-if="displayUrl && !busy" :src="displayUrl" alt="" />
      <span v-else class="ph" :class="{ busy }">{{ busy ? "上传中…" : "+" }}</span>
      <input ref="inp" type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="onFile" />
    </div>
    <div v-if="err" class="imgf-error">{{ err }}</div>
    <div v-if="actions && displayUrl" class="imgf-actions">
      <button type="button" class="btn sm" :disabled="busy" @click="pick">替换</button>
      <button type="button" class="btn sm" :disabled="busy" @click="clearImg">删图</button>
    </div>
  </div>
</template>

<style scoped>
.imgf-wrap { display: inline-flex; flex-direction: column; align-items: flex-start; max-width: 100%; }
.imgf-actions { display: flex; gap: 4px; margin-top: 5px; flex-wrap: wrap; }
.imgf-actions .btn { padding: 3px 7px; font-size: 11px; }
.imgf {
  position: relative;
  background: #EDEBE4;
  border: 1px dashed rgba(28, 27, 25, 0.18);
  overflow: hidden;
  cursor: pointer;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink3);
}
.imgf:hover { border-color: rgba(186, 117, 23, 0.5); }
.imgf.sm { width: 52px; height: 42px; border-radius: 7px; }
.imgf.md { width: 82px; height: 82px; border-radius: 9px; font-size: 22px; }
.imgf img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ph { font-size: 10px; line-height: 1; white-space: nowrap; }
.imgf.md .ph { font-size: 22px; }
.imgf .ph.busy,
.imgf.md .ph.busy { font-size: 10px; font-weight: 400; letter-spacing: 0; }
.imgf-error {
  max-width: 280px;
  margin-top: 5px;
  color: #a32d2d;
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>

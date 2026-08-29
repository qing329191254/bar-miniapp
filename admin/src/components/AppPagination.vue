<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ page: number; pageSize: number; total: number }>();
const emit = defineEmits<{ "update:page": [number]; "update:pageSize": [number] }>();

const sizes = [15, 30, 50];
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize) || 1));
const from = computed(() => (props.total ? (props.page - 1) * props.pageSize + 1 : 0));
const to = computed(() => Math.min(props.page * props.pageSize, props.total));
const show = computed(() => props.total > 0);

function setPage(p: number) {
  emit("update:page", Math.min(Math.max(1, p), totalPages.value));
}
</script>

<template>
  <div v-if="show" class="pg-bar">
    <span class="tiny pg-info">第 {{ from }}–{{ to }} 条，共 {{ total.toLocaleString("en-US") }} 条</span>
    <div class="pg-ops">
      <span class="tiny pg-label">每页</span>
      <span
        v-for="s in sizes"
        :key="s"
        class="chip pg-size"
        :class="{ on: pageSize === s }"
        @click="emit('update:pageSize', s)"
      >{{ s }}</span>
      <button class="btn sm ghost" type="button" :disabled="page <= 1" @click="setPage(page - 1)">上一页</button>
      <span class="tiny pg-num">{{ page }} / {{ totalPages }}</span>
      <button class="btn sm ghost" type="button" :disabled="page >= totalPages" @click="setPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

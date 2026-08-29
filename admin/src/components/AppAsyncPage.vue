<script setup lang="ts">
import { computed } from "vue";
import AppPageSkeleton from "./AppPageSkeleton.vue";

export type SkeletonOptions = {
  metrics?: number;
  tableRows?: number;
  tableCols?: number;
  showFilter?: boolean;
  showNote?: boolean;
  showTabs?: boolean;
  showExtraCard?: boolean;
  showChart?: boolean;
  variant?: "table" | "feed" | "detail" | "chart";
};

const props = withDefaults(
  defineProps<{
    loading: boolean;
    data: unknown;
    err?: string;
    skeleton?: SkeletonOptions;
    retryLabel?: string;
  }>(),
  { err: "", retryLabel: "重试" },
);

defineEmits<{ retry: [] }>();

const initialLoad = computed(() => props.loading && !props.data);
const refreshing = computed(() => props.loading && !!props.data);

const sk = computed(() => ({
  metrics: 4,
  tableRows: 6,
  tableCols: 9,
  showFilter: true,
  showNote: true,
  showTabs: false,
  showExtraCard: false,
  showChart: false,
  variant: "table" as const,
  ...props.skeleton,
}));
</script>

<template>
  <div v-if="initialLoad" class="page-loading">
    <AppPageSkeleton v-bind="sk" />
  </div>
  <div v-else-if="err && !data" class="card page-err">
    <p>{{ err }}</p>
    <button class="btn sm ghost" type="button" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>
  <div v-else class="page-body" :class="{ refreshing }">
    <div v-if="refreshing" class="refresh-bar" aria-hidden="true" />
    <slot />
  </div>
</template>

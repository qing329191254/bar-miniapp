<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
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
  showHeader?: boolean;
  formSections?: number;
  formColumns?: 1 | 2;
  variant?: "table" | "feed" | "detail" | "form" | "chart" | "dashboard";
};

const props = withDefaults(
  defineProps<{
    loading: boolean;
    data?: unknown;
    err?: string;
    skeleton?: SkeletonOptions;
    retryLabel?: string;
    skeletonDelay?: number;
    skeletonMinDuration?: number;
  }>(),
  {
    err: "",
    retryLabel: "重试",
    skeletonDelay: 140,
    skeletonMinDuration: 300,
  },
);

defineEmits<{ retry: [] }>();

const resolvedOnce = ref(Boolean(props.data));
const showSkeleton = ref(false);
const skeletonShownAt = ref(0);
let showTimer: ReturnType<typeof setTimeout> | undefined;
let hideTimer: ReturnType<typeof setTimeout> | undefined;

const hasData = computed(() => Boolean(props.data) || resolvedOnce.value);
const initialLoad = computed(() => props.loading && !hasData.value);
const refreshing = computed(() => props.loading && hasData.value);
const waitingForSkeleton = computed(() => initialLoad.value && !showSkeleton.value);

function clearShowTimer() {
  if (showTimer) window.clearTimeout(showTimer);
  showTimer = undefined;
}

function clearHideTimer() {
  if (hideTimer) window.clearTimeout(hideTimer);
  hideTimer = undefined;
}

watch(
  () => props.data,
  (value) => {
    if (value) resolvedOnce.value = true;
  },
);

watch(
  () => props.loading,
  (loading) => {
    if (!loading && !props.err) resolvedOnce.value = true;
  },
);

watch(
  initialLoad,
  (loading) => {
    clearShowTimer();
    clearHideTimer();

    if (loading) {
      showSkeleton.value = false;
      showTimer = window.setTimeout(() => {
        if (!initialLoad.value) return;
        skeletonShownAt.value = performance.now();
        showSkeleton.value = true;
      }, props.skeletonDelay);
      return;
    }

    if (!showSkeleton.value) return;
    const elapsed = performance.now() - skeletonShownAt.value;
    hideTimer = window.setTimeout(
      () => {
        showSkeleton.value = false;
      },
      Math.max(0, props.skeletonMinDuration - elapsed),
    );
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  clearShowTimer();
  clearHideTimer();
});

const sk = computed(() => ({
  metrics: 4,
  tableRows: 6,
  tableCols: 9,
  showFilter: true,
  showNote: true,
  showTabs: false,
  showExtraCard: false,
  showChart: false,
  showHeader: true,
  formSections: 2,
  formColumns: 2 as const,
  variant: "table" as const,
  ...props.skeleton,
}));
</script>

<template>
  <div v-if="showSkeleton" class="page-loading async-fade-in">
    <AppPageSkeleton v-bind="sk" />
  </div>
  <div v-else-if="waitingForSkeleton" class="page-loading-pending" aria-busy="true" aria-label="页面加载中" />
  <div v-else-if="err && !hasData" class="card page-err async-fade-in">
    <p>{{ err }}</p>
    <button class="btn sm ghost" type="button" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>
  <div v-else class="page-body async-fade-in" :class="{ refreshing }" :aria-busy="refreshing">
    <div v-if="refreshing" class="refresh-bar" aria-hidden="true" />
    <slot />
  </div>
</template>

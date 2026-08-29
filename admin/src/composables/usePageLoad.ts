import { computed, type Ref } from "vue";

export function usePageLoad(loading: Ref<boolean>, data: Ref<unknown>) {
  const initialLoad = computed(() => loading.value && !data.value);
  const refreshing = computed(() => loading.value && !!data.value);
  return { initialLoad, refreshing };
}

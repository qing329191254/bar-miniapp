import { computed, ref, watch, type ComputedRef, type Ref } from "vue";
import { DEFAULT_PAGE_SIZE } from "../api";

export function usePagination<T>(source: Ref<T[]> | ComputedRef<T[]>, defaultSize = DEFAULT_PAGE_SIZE) {
  const page = ref(1);
  const pageSize = ref(defaultSize);
  const total = computed(() => source.value.length);
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value) || 1));
  const items = computed(() => {
    const start = (page.value - 1) * pageSize.value;
    return source.value.slice(start, start + pageSize.value);
  });

  watch(source, () => {
    page.value = 1;
  });
  watch(pageSize, () => {
    page.value = 1;
  });
  watch(totalPages, (tp) => {
    if (page.value > tp) page.value = tp;
  });

  return { page, pageSize, total, totalPages, items };
}

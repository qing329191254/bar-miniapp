<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ name: string }>();

const icons: Record<string, string[]> = {
  dashboard: ["M4 13h6V4H4v9Z", "M14 20h6v-9h-6v9Z", "M14 4h6v3h-6V4Z", "M4 17h6v3H4v-3Z"],
  trend: ["M4 19V5", "M4 19h16", "m7 15 3-4 3 2 4-6"],
  orders: ["M6 3h12v18l-3-2-3 2-3-2-3 2V3Z", "M9 8h6", "M9 12h6"],
  recharge: ["M4 7h16v12H4V7Z", "M4 10h16", "M8 15h3", "M7 4h10"],
  jobs: ["M8 4h8", "M9 3h6v3H9V3Z", "M6 5h12v16H6V5Z", "m9 11-5 5-2-2"],
  reports: ["M5 20V10", "M10 20V4", "M15 20v-7", "M20 20H3"],
  game: ["M8 8h8", "M12 4v8", "M6 20h12l2-8-3-5H7l-3 5 2 8Z", "M16.5 14.5h.01", "M18.5 16.5h.01"],
  records: ["M4 6h16", "M4 12h16", "M4 18h16", "M7 3v6", "M17 9v6"],
  trophy: ["M8 4h8v4c0 3-1.8 5-4 5S8 11 8 8V4Z", "M8 6H4v2c0 2 1.4 3 4 3", "M16 6h4v2c0 2-1.4 3-4 3", "M12 13v4", "M8 20h8", "M10 17h4"],
  history: ["M4 12a8 8 0 1 0 2.3-5.7L4 8.6", "M4 4v4.6h4.6", "M12 8v5l3 2"],
  rules: ["M5 4h14", "M5 12h14", "M5 20h14", "M8 2v4", "M16 10v4", "M10 18v4"],
  project: ["M5 5h14v14H5V5Z", "M8 8h.01", "M16 8h.01", "M8 16h.01", "M16 16h.01", "M12 12h.01"],
  withdrawal: ["M12 3v13", "m7 11 5 5 5-5", "M5 20h14"],
  products: ["m4 7 8-4 8 4-8 4-8-4Z", "M4 7v10l8 4 8-4V7", "M12 11v10"],
  ticket: ["M4 7h16v4a2 2 0 0 0 0 4v4H4v-4a2 2 0 0 0 0-4V7Z", "M12 7v2", "M12 15v2"],
  tiers: ["M12 7c4 0 7-1.1 7-2.5S16 2 12 2 5 3.1 5 4.5 8 7 12 7Z", "M5 4.5V9c0 1.4 3 2.5 7 2.5S19 10.4 19 9V4.5", "M5 9v4.5C5 14.9 8 16 12 16s7-1.1 7-2.5V9", "M5 13.5V18c0 1.4 3 2.5 7 2.5s7-1.1 7-2.5v-4.5"],
  calendar: ["M5 5h14v15H5V5Z", "M8 3v4", "M16 3v4", "M5 9h14", "m9 13-3 3-2-2"],
  members: ["M9 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M3 21v-2a6 6 0 0 1 12 0v2", "M17 11a3 3 0 0 0 0-6", "M18 21v-2a5 5 0 0 0-3-4.6"],
  userMinus: ["M9 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M3 21v-2a6 6 0 0 1 12 0v2", "M16 10h6"],
  teams: ["M12 3 4 7v5c0 5 3.4 8.3 8 10 4.6-1.7 8-5 8-10V7l-8-4Z", "M9 12a3 3 0 1 0 6 0", "M7.5 18a5 5 0 0 1 9 0"],
  content: ["M4 5h16v14H4V5Z", "M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z", "m4 17 4-4 3 3 2-2 3 3"],
  agreement: ["M6 3h9l3 3v15H6V3Z", "M15 3v4h4", "M9 11h6", "M9 15h6"],
  bell: ["M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9", "M10 21h4"],
  shop: ["M4 10h16", "m5 4-2 6h10l-2-6H9Z", "M5 10v10h14V10", "M9 20v-6h6v6"],
  staff: ["M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M3 21v-2a6 6 0 0 1 12 0v2", "m17 11 2 2 4-4", "M19 13v6h4"],
  logs: ["M5 4h14v16H5V4Z", "M8 8h8", "M8 12h8", "M8 16h5"],
  logout: ["M10 4H5v16h5", "M14 8l4 4-4 4", "M18 12H9"],
  sparkle: ["m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Z", "m18 14 .7 2.3L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.7L18 14Z", "M5 15l.5 1.5L7 17l-1.5.5L5 19l-.5-1.5L3 17l1.5-.5L5 15Z"],
  arrowRight: ["M5 12h14", "m14 7 5 5-5 5"],
};

const paths = computed(() => icons[props.name] || icons.sparkle);
</script>

<template>
  <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
    <path v-for="path in paths" :key="path" :d="path" />
  </svg>
</template>

<style scoped>
.ui-icon{width:1em;height:1em;display:block;flex:none}
</style>

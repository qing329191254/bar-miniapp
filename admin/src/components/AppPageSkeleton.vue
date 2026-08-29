<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    metrics?: number;
    tableRows?: number;
    tableCols?: number;
    showFilter?: boolean;
    showNote?: boolean;
    showTabs?: boolean;
    showExtraCard?: boolean;
    showChart?: boolean;
    variant?: "table" | "feed" | "detail" | "chart";
  }>(),
  {
    metrics: 4,
    tableRows: 6,
    tableCols: 9,
    showFilter: true,
    showNote: true,
    showTabs: false,
    showExtraCard: false,
    showChart: false,
    variant: "table",
  },
);

const gridCols = computed(() => {
  const n = props.tableCols;
  if (n <= 5) return "1.4fr 1fr 1fr 1fr 1fr";
  if (n === 7) return "1.4fr 0.9fr 1fr 1.2fr 0.9fr 0.8fr 0.9fr";
  if (n === 8) return "1.3fr 1fr 0.8fr 0.9fr 1fr 0.9fr 0.9fr 0.8fr";
  if (n >= 10) return "1.2fr repeat(9, minmax(0, 1fr))";
  return "1.6fr 0.9fr 0.6fr 1fr 0.6fr 0.7fr 0.6fr 0.8fr 0.9fr";
});

const feedCols = "0.9fr 1.8fr 2fr 1fr 0.9fr";
const detailCols = "1.2fr 1fr 1fr 0.8fr 1.6fr";
</script>

<template>
  <div class="page-skeleton" aria-busy="true" aria-label="页面加载中">
    <div v-if="showFilter" class="card sk-block">
      <div class="sk-line sk-st" />
      <div class="sk-chips">
        <span v-for="i in 7" :key="'c' + i" class="sk-chip" />
      </div>
      <div class="sk-line sk-field" />
    </div>

    <div v-if="showTabs" class="card sk-block sk-tabs-card">
      <div class="sk-line sk-st short" />
      <div class="sk-chips">
        <span v-for="i in 9" :key="'t' + i" class="sk-chip wide" />
      </div>
    </div>

    <div class="cards sk-metrics">
      <div v-for="i in metrics" :key="'m' + i" class="mtr sk-metric">
        <div class="sk-line sk-k" />
        <div class="sk-line sk-v" />
        <div class="sk-line sk-sub" />
      </div>
    </div>

    <div v-if="showExtraCard" class="card sk-block">
      <div class="sk-line sk-st short" />
      <div class="sk-chips">
        <span v-for="i in 8" :key="'e' + i" class="sk-chip" />
      </div>
    </div>

    <div v-if="showChart" class="card sk-chart">
      <div class="sk-line sk-st short" />
      <div class="sk-chart-area" />
    </div>

    <!-- 流水 / 详情 -->
    <template v-if="variant === 'feed'">
      <div class="card sk-block">
        <div class="sk-line sk-st short" />
        <div class="sk-chips">
          <span v-for="i in 5" :key="'f' + i" class="sk-chip wide" />
        </div>
      </div>
      <div v-for="d in 2" :key="'day' + d" class="card sk-feed-day">
        <div class="sk-line sk-st short" />
        <div class="sk-feed-head" :style="{ gridTemplateColumns: feedCols }">
          <span v-for="i in 5" :key="'fh' + d + i" class="sk-th" />
        </div>
        <div v-for="r in 4" :key="'fr' + d + r" class="sk-feed-row" :style="{ gridTemplateColumns: feedCols }">
          <span v-for="i in 5" :key="'fc' + d + r + i" class="sk-cell" />
        </div>
      </div>
    </template>

    <template v-else-if="variant === 'detail'">
      <div class="card sk-block">
        <div class="sk-line sk-st short" />
        <div v-for="i in 3" :key="'info' + i" class="sk-info-row">
          <span class="sk-line sk-info-k" />
          <span class="sk-line sk-info-v" />
        </div>
      </div>
      <div class="card sk-table">
        <div class="sk-table-head" :style="{ gridTemplateColumns: detailCols }">
          <span v-for="i in 5" :key="'dh' + i" class="sk-th" />
        </div>
        <div v-for="r in tableRows" :key="'dr' + r" class="sk-table-row simple" :style="{ gridTemplateColumns: detailCols }">
          <span v-for="i in 5" :key="'dc' + r + i" class="sk-cell" />
        </div>
      </div>
    </template>

    <!-- 默认表格 -->
    <div v-else class="card sk-table">
      <div class="sk-table-head" :style="{ gridTemplateColumns: gridCols }">
        <span v-for="i in tableCols" :key="'h' + i" class="sk-th" />
      </div>
      <div v-for="r in tableRows" :key="'r' + r" class="sk-table-row" :class="{ simple: tableCols <= 7 }" :style="{ gridTemplateColumns: gridCols }">
        <template v-if="tableCols >= 9 && variant === 'table'">
          <div class="sk-staff">
            <span class="sk-av" />
            <span class="sk-staff-text">
              <span class="sk-line sk-name" />
              <span class="sk-line sk-phone" />
            </span>
          </div>
          <span class="sk-pill" />
          <span v-for="i in tableCols - 2" :key="'c' + r + i" class="sk-cell" :class="{ 'sk-wide': i === 3 }" />
        </template>
        <template v-else>
          <span v-for="i in tableCols" :key="'c' + r + i" class="sk-cell" />
        </template>
      </div>
    </div>

    <div v-if="showNote" class="note sk-note">
      <span class="sk-line sk-note-line" />
      <span class="sk-line sk-note-line short" />
    </div>
  </div>
</template>

<style scoped>
.page-skeleton {
  min-height: min(72vh, 640px);
}

.sk-block,
.sk-table,
.sk-metric,
.sk-feed-day,
.sk-chart {
  position: relative;
  overflow: hidden;
}

.sk-block::after,
.sk-table::after,
.sk-metric::after,
.sk-feed-day::after,
.sk-chart::after,
.sk-chip::after,
.sk-th::after,
.sk-cell::after,
.sk-pill::after,
.sk-btn::after,
.sk-av::after,
.sk-line::after,
.sk-chart-area::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  animation: sk-shimmer 1.35s ease-in-out infinite;
}

.sk-st {
  width: 42%;
  height: 14px;
  margin-bottom: 12px;
  border-radius: 6px;
}

.sk-st.short {
  width: 28%;
}

.sk-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.sk-tabs-card,
.sk-block + .sk-metrics {
  margin-top: 0;
}

.sk-chip {
  position: relative;
  width: 52px;
  height: 28px;
  border-radius: 999px;
  background: #eceae4;
  overflow: hidden;
}

.sk-chip.wide {
  width: 44px;
}

.sk-field {
  width: 170px;
  height: 34px;
  border-radius: 8px;
}

.sk-metrics {
  margin-bottom: 12px;
}

.sk-k {
  width: 56%;
  height: 11px;
  margin-bottom: 10px;
  border-radius: 4px;
}

.sk-v {
  width: 72%;
  height: 22px;
  margin-bottom: 8px;
  border-radius: 6px;
}

.sk-sub {
  width: 48%;
  height: 10px;
  border-radius: 4px;
}

.sk-chart {
  margin-bottom: 12px;
  padding: 14px;
}

.sk-chart-area {
  position: relative;
  height: 130px;
  border-radius: 10px;
  background: #eceae4;
  overflow: hidden;
}

.sk-table {
  padding: 0;
  overflow: hidden;
}

.sk-table-head,
.sk-table-row,
.sk-feed-head,
.sk-feed-row {
  display: grid;
  gap: 8px;
  align-items: center;
  padding: 11px 14px;
  border-bottom: 1px solid var(--line);
}

.sk-table-head,
.sk-feed-head {
  background: #faf9f5;
}

.sk-table-row:last-child,
.sk-feed-row:last-child {
  border-bottom: none;
}

.sk-th {
  position: relative;
  height: 10px;
  border-radius: 4px;
  background: #e8e6e0;
  overflow: hidden;
}

.sk-staff {
  display: flex;
  align-items: center;
  gap: 7px;
}

.sk-av {
  position: relative;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e8e6e0;
  flex-shrink: 0;
  overflow: hidden;
}

.sk-staff-text {
  flex: 1;
  min-width: 0;
}

.sk-name {
  width: 68%;
  height: 12px;
  margin-bottom: 6px;
  border-radius: 4px;
}

.sk-phone {
  width: 46%;
  height: 9px;
  border-radius: 4px;
}

.sk-pill {
  position: relative;
  width: 38px;
  height: 22px;
  border-radius: 999px;
  background: #eceae4;
  overflow: hidden;
}

.sk-cell {
  position: relative;
  height: 11px;
  border-radius: 4px;
  background: #eceae4;
  overflow: hidden;
}

.sk-cell.sk-wide {
  height: 14px;
}

.sk-info-row {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}

.sk-info-row:last-child {
  border-bottom: none;
}

.sk-info-k {
  width: 88px;
  height: 12px;
  flex-shrink: 0;
}

.sk-info-v {
  flex: 1;
  height: 12px;
}

.sk-feed-day {
  margin-bottom: 12px;
  padding: 14px;
}

.sk-note {
  margin-top: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-note-line {
  width: 100%;
  height: 11px;
  border-radius: 4px;
}

.sk-note-line.short {
  width: 72%;
}

.sk-line {
  position: relative;
  display: block;
  background: #eceae4;
  overflow: hidden;
}

@keyframes sk-shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>

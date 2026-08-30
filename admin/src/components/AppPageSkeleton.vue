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
    showHeader?: boolean;
    formSections?: number;
    formColumns?: 1 | 2;
    variant?: "table" | "feed" | "detail" | "form" | "chart" | "dashboard";
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
    showHeader: true,
    formSections: 2,
    formColumns: 2,
    variant: "table",
  },
);

const gridCols = computed(() => {
  const n = Math.max(1, props.tableCols);
  const weights = [1.45, 0.95, 0.8, 1.1, 0.82, 0.9, 0.78, 0.86, 0.82, 0.76];
  return Array.from({ length: n }, (_, i) => `${weights[i] || 0.8}fr`).join(" ");
});

const feedCols = "0.9fr 1.8fr 2fr 1fr 0.9fr";
const detailCols = "1.2fr 1fr 1fr 0.8fr 1.6fr";
</script>

<template>
  <div class="page-skeleton" aria-busy="true" aria-label="页面加载中">
    <div v-if="showHeader" class="sk-page-head">
      <span class="sk-line sk-page-title" />
      <div class="sk-head-actions">
        <span class="sk-line sk-head-meta" />
        <span class="sk-action" />
      </div>
    </div>

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

    <!-- 表单 / 流水 / 详情 -->
    <template v-if="variant === 'form'">
      <div class="sk-form-layout" :class="{ single: formColumns === 1 }">
        <section v-for="section in formSections" :key="'form' + section" class="card sk-form-section">
          <div class="sk-form-title">
            <span class="sk-line sk-st short" />
            <span class="sk-line sk-form-hint" />
          </div>
          <div class="sk-form-grid">
            <div v-for="field in 4" :key="'field' + section + field" class="sk-form-field" :class="{ wide: field === 4 }">
              <span class="sk-line sk-label" />
              <span class="sk-input" />
              <span v-if="field === 1 || field === 4" class="sk-line sk-help" />
            </div>
          </div>
          <div class="sk-form-actions">
            <span class="sk-action ghost" />
            <span class="sk-action primary" />
          </div>
        </section>
      </div>
    </template>

    <template v-else-if="variant === 'feed'">
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
    <div v-else-if="variant !== 'dashboard'" class="card sk-table">
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
  width: 100%;
}

.sk-page-head {
  display: flex;
  align-items: center;
  min-height: 36px;
  margin-bottom: 12px;
  padding: 2px 0;
}

.sk-page-title {
  width: 176px;
  height: 22px;
  border-radius: 7px;
}

.sk-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.sk-head-meta {
  width: 128px;
  height: 11px;
  border-radius: 5px;
}

.sk-chip::after,
.sk-th::after,
.sk-cell::after,
.sk-pill::after,
.sk-action::after,
.sk-input::after,
.sk-av::after,
.sk-line::after,
.sk-chart-area::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.48), transparent);
  animation: sk-shimmer 1.65s ease-in-out infinite;
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
  background: #ece8e1;
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
  background: #ece8e1;
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
  padding: 14px;
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
  background: #e7e3dc;
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
  background: #e7e3dc;
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
  background: #ece8e1;
  overflow: hidden;
}

.sk-cell {
  position: relative;
  height: 11px;
  border-radius: 4px;
  background: #ece8e1;
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

.sk-form-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.sk-form-layout.single {
  grid-template-columns: 1fr;
}

.sk-form-section {
  padding: 18px;
}

.sk-form-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 22px;
  margin-bottom: 18px;
}

.sk-form-title .sk-st {
  margin: 0;
}

.sk-form-hint {
  width: 42%;
  height: 10px;
  border-radius: 4px;
}

.sk-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 14px;
}

.sk-form-field {
  min-width: 0;
}

.sk-form-field.wide {
  grid-column: 1 / -1;
}

.sk-label {
  width: 74px;
  height: 10px;
  margin-bottom: 8px;
  border-radius: 4px;
}

.sk-input {
  position: relative;
  display: block;
  width: 100%;
  height: 38px;
  border: 1px solid rgba(82, 59, 32, 0.06);
  border-radius: 9px;
  background: #ece8e1;
  overflow: hidden;
}

.sk-form-field.wide .sk-input {
  height: 62px;
}

.sk-help {
  width: 58%;
  height: 8px;
  margin-top: 7px;
  border-radius: 4px;
}

.sk-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.sk-action {
  position: relative;
  display: block;
  width: 76px;
  height: 34px;
  border-radius: 9px;
  background: #e7e3dc;
  overflow: hidden;
}

.sk-action.ghost {
  width: 68px;
}

.sk-action.primary {
  background: #e2d6c5;
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
  background: #ece8e1;
  overflow: hidden;
}

@keyframes sk-shimmer {
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 900px) {
  .sk-form-layout,
  .sk-form-grid {
    grid-template-columns: 1fr;
  }

  .sk-form-field.wide {
    grid-column: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sk-chip::after,
  .sk-th::after,
  .sk-cell::after,
  .sk-pill::after,
  .sk-action::after,
  .sk-input::after,
  .sk-av::after,
  .sk-line::after,
  .sk-chart-area::after {
    animation: none;
  }
}
</style>

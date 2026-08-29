<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { type BizMetric, type BizGranularity, type BizRow, type ChartMode, chartMode } from "./bizChartUtil";

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Row = BizRow;

const props = defineProps<{ rows: Row[]; metric: BizMetric; peakVal?: number; granularity?: BizGranularity }>();
const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

const METRIC_LABEL: Record<BizMetric, string> = {
  biz: "营业额",
  recharge: "充值额",
  orders: "订单数",
  guests: "到店人次",
};

const MODE_HINT: Record<ChartMode, string> = {
  single: "单日构成",
  bar: "逐日对比",
  line: "趋势折线",
  "line-sparse": "长期趋势",
};

const modeHint = computed(() => MODE_HINT[mode.value]);

function valOf(row: Row) {
  switch (props.metric) {
    case "recharge":
      return Number(row.recharge || 0);
    case "orders":
      return Number(row.orders || 0);
    case "guests":
      return Number(row.guests || 0);
    default:
      return Number(row.coin || 0) + Number(row.offline || 0);
  }
}

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

const mode = computed(() => chartMode(props.rows.length, props.granularity || "day"));
const singleRow = computed(() => props.rows[0] || null);
const isMoney = computed(() => props.metric === "biz" || props.metric === "recharge");

function labelOf(row: Row) {
  if (props.granularity === "week" && row.dEnd) {
    return `${row.d.slice(5)}~${row.dEnd.slice(5)}`;
  }
  const n = props.rows.length;
  if (n <= 14) return row.d.slice(5);
  if (n <= 31) return row.d.slice(5);
  const [, mo, da] = row.d.split("-");
  return `${mo}/${da}`;
}

function periodOf(row: Row) {
  return row.dEnd ? `${row.d} ~ ${row.dEnd}` : row.d;
}

function barColor(v: number) {
  const peak = props.peakVal ?? Math.max(...props.rows.map(valOf), 0);
  return v === peak && peak > 0 ? "#378ADD" : "#B5D4F4";
}

function tooltipHtml(row: Row, v: number) {
  const label = METRIC_LABEL[props.metric];
  const main = isMoney.value ? `¥${fmt(v)}` : fmt(v);
  const period = periodOf(row);
  if (props.metric === "biz") {
    return `${period}<br/>${label} ${main}<br/><span style="color:#9C9A93">金币 ¥${fmt(row.coin)} + 现场 ¥${fmt(row.offline)}</span>`;
  }
  return `${period}<br/>${label} ${main}`;
}

function option() {
  const rows = props.rows.length ? props.rows : [];
  const labels = rows.map(labelOf);
  const vals = rows.map(valOf);
  const max = Math.max(...vals, 1);
  const m = mode.value;

  const base = {
    animation: false,
    animationDuration: 0,
    animationDurationUpdate: 0,
    grid: { left: 8, right: 8, top: 8, bottom: 28, containLabel: false },
    tooltip: {
      trigger: "axis" as const,
      backgroundColor: "#fff",
      borderColor: "rgba(28,27,25,.12)",
      textStyle: { color: "#1C1B19", fontSize: 12 },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const row = rows[p.dataIndex];
        if (!row) return "";
        return tooltipHtml(row, valOf(row));
      },
    },
    xAxis: {
      type: "category" as const,
      data: labels,
      axisLine: { show: true, lineStyle: { color: "rgba(28,27,25,.12)" } },
      axisTick: { show: false },
      axisLabel: {
        color: "#9C9A93",
        fontSize: m === "line-sparse" ? 8 : 9,
        margin: 8,
        interval: m === "line-sparse" ? Math.max(0, Math.floor(labels.length / 8) - 1) : 0,
        rotate: m === "line-sparse" && labels.length > 40 ? 35 : 0,
      },
    },
    yAxis: {
      type: "value" as const,
      min: 0,
      max: max * 1.12,
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: m !== "bar", lineStyle: { color: "rgba(28,27,25,.06)" } },
    },
  };

  if (m === "bar") {
    return {
      ...base,
      tooltip: { ...base.tooltip, axisPointer: { type: "shadow", shadowStyle: { color: "rgba(55,138,221,.08)" } } },
      series: [
        {
          type: "bar",
          data: vals.map((v) => ({
            value: v,
            itemStyle: { color: barColor(v), borderRadius: [3, 3, 0, 0] },
          })),
          barMaxWidth: rows.length <= 4 ? 48 : 34,
          barCategoryGap: rows.length <= 4 ? "36%" : "28%",
          barMinHeight: 3,
        },
      ],
    };
  }

  const peak = props.peakVal ?? Math.max(...vals, 0);
  return {
    ...base,
    tooltip: { ...base.tooltip, axisPointer: { type: "line", lineStyle: { color: "rgba(55,138,221,.25)" } } },
    series: [
      {
        type: "line",
        data: vals.map((v, i) => ({
          value: v,
          symbol: m === "line-sparse" ? "none" : "circle",
          symbolSize: v === peak && peak > 0 ? 8 : 5,
          itemStyle: { color: v === peak && peak > 0 ? "#378ADD" : "#378ADD" },
        })),
        smooth: m === "line-sparse" ? 0.35 : 0.25,
        lineStyle: { width: m === "line-sparse" ? 2 : 2.5, color: "#378ADD" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(55,138,221,.18)" },
              { offset: 1, color: "rgba(55,138,221,.02)" },
            ],
          },
        },
        showSymbol: m !== "line-sparse",
      },
    ],
  };
}

function render() {
  if (mode.value === "single" || !el.value) return;
  if (!chart) chart = echarts.init(el.value);
  chart.setOption(option(), true);
  chart.resize();
}

function disposeChart() {
  ro?.disconnect();
  ro = null;
  chart?.dispose();
  chart = null;
}

onMounted(() => {
  if (mode.value === "single" || !el.value) return;
  chart = echarts.init(el.value);
  render();
  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

watch(
  () => [props.rows.map((r) => `${r.d}|${r.dEnd || ""}`).join(), props.metric, props.peakVal, props.granularity, mode.value] as const,
  async () => {
    if (mode.value === "single") {
      disposeChart();
      return;
    }
    await nextTick();
    if (!el.value) return;
    if (!chart) {
      chart = echarts.init(el.value);
      ro = new ResizeObserver(() => chart?.resize());
      ro.observe(el.value);
    }
    render();
  },
);

onBeforeUnmount(disposeChart);
</script>

<template>
  <div v-if="!rows.length" class="mut empty-chart">所选区间无数据</div>

  <!-- 1 天：构成条，贴底展示 -->
  <div v-else-if="mode === 'single' && singleRow" class="single-wrap">
    <div class="single-head">
      <span class="single-date">{{ singleRow.d }}</span>
      <b class="single-val">{{ isMoney ? "¥" : "" }}{{ fmt(valOf(singleRow)) }}</b>
    </div>
    <template v-if="metric === 'biz'">
      <div class="single-bar">
        <div
          v-if="singleRow.coin > 0"
          class="seg seg-coin"
          :style="{ flex: singleRow.coin || 1 }"
          :title="`金币 ¥${fmt(singleRow.coin)}`"
        />
        <div
          v-if="singleRow.offline > 0"
          class="seg seg-offline"
          :style="{ flex: singleRow.offline || 1 }"
          :title="`现场 ¥${fmt(singleRow.offline)}`"
        />
      </div>
      <div class="single-legend">
        <span><i class="dot dot-coin" />金币 ¥{{ fmt(singleRow.coin) }}</span>
        <span><i class="dot dot-offline" />现场 ¥{{ fmt(singleRow.offline) }}</span>
      </div>
    </template>
    <p v-else class="single-note">{{ METRIC_LABEL[metric] }} · 单日无可拆分项，详见下表</p>
  </div>

  <div v-else ref="el" class="biz-chart" :class="`mode-${mode}`"></div>
</template>

<style scoped>
.biz-chart {
  width: 100%;
  height: 110px;
  flex: none;
}
.biz-chart.mode-line,
.biz-chart.mode-line-sparse {
  height: 128px;
}
.empty-chart {
  padding: 26px;
  text-align: center;
  color: var(--ink3);
  font-size: 12px;
}
.single-wrap {
  padding: 4px 2px 2px;
}
.single-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.single-date {
  font-size: 12px;
  color: var(--ink3);
}
.single-val {
  font-size: 22px;
  font-weight: 600;
}
.single-bar {
  display: flex;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  background: #f1efe8;
}
.seg-coin {
  background: #378add;
}
.seg-offline {
  background: #b5d4f4;
}
.single-legend {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--ink2);
}
.single-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot-coin {
  background: #378add;
}
.dot-offline {
  background: #b5d4f4;
}
.single-note {
  font-size: 11px;
  color: var(--ink3);
  margin: 8px 0 0;
}
</style>

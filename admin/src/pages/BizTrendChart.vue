<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Row = { d: string; coin: number; offline: number };

const props = defineProps<{ rows: Row[]; peakBiz?: number }>();
const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

function barColor(v: number) {
  const peak = props.peakBiz ?? Math.max(...props.rows.map((x) => x.coin + x.offline), 0);
  return v === peak && peak > 0 ? "#378ADD" : "#B5D4F4";
}

function option() {
  const rows = props.rows.length ? props.rows : [];
  const labels = rows.map((x) => x.d.slice(5));
  const vals = rows.map((x) => Number(x.coin || 0) + Number(x.offline || 0));
  const max = Math.max(...vals, 1);

  return {
    animationDuration: 400,
    grid: { left: 0, right: 0, top: 8, bottom: 0, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(55,138,221,.08)" } },
      backgroundColor: "#fff",
      borderColor: "rgba(28,27,25,.12)",
      textStyle: { color: "#1C1B19", fontSize: 12 },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const row = rows[p.dataIndex] || { coin: 0, offline: 0, d: "" };
        const n = Number(p.value || 0).toLocaleString("en-US");
        return `${row.d}<br/>营业额 ¥${n}<br/><span style="color:#9C9A93">金币 ¥${Number(row.coin || 0).toLocaleString("en-US")} + 现场 ¥${Number(row.offline || 0).toLocaleString("en-US")}</span>`;
      },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: { show: true, lineStyle: { color: "rgba(28,27,25,.12)" } },
      axisTick: { show: false },
      axisLabel: { color: "#9C9A93", fontSize: 9, margin: 8 },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: max * 1.15,
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    series: [
      {
        type: "bar",
        data: vals.map((v) => ({
          value: v,
          itemStyle: { color: barColor(v), borderRadius: [3, 3, 0, 0] },
        })),
        barMaxWidth: 34,
        barCategoryGap: "28%",
        barMinHeight: 3,
      },
    ],
  };
}

function render() {
  chart?.setOption(option(), true);
  chart?.resize();
}

onMounted(() => {
  if (!el.value) return;
  chart = echarts.init(el.value);
  render();
  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

watch(() => [props.rows, props.peakBiz], render, { deep: true });

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div v-if="rows.length" ref="el" class="biz-chart"></div>
  <div v-else class="mut empty-chart">所选区间无数据</div>
</template>

<style scoped>
.biz-chart {
  width: 100%;
  height: 130px;
}
.empty-chart {
  padding: 26px;
  text-align: center;
  color: var(--ink3);
  font-size: 12px;
}
</style>

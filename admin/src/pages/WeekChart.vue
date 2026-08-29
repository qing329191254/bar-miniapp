<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Row = { d: string; coin: number; offline: number; label?: string };

const props = defineProps<{ rows: Row[] }>();
const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

const WD = ["日", "一", "二", "三", "四", "五", "六"];

function wdLabel(d: string) {
  const dt = new Date(`${d}T12:00:00`);
  return WD[dt.getDay()] || "";
}

function isoWeekday(d: string) {
  const dt = new Date(`${d}T12:00:00`);
  const day = dt.getDay();
  return day === 0 ? 7 : day;
}

function barColor(d: string) {
  return isoWeekday(d) >= 5 ? "#378ADD" : "#B5D4F4";
}

function option() {
  const rows = props.rows.length ? props.rows : [];
  const labels = rows.map((x) => x.label || wdLabel(x.d));
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
        const row = rows[p.dataIndex] || { coin: 0, offline: 0 };
        const n = Number(p.value || 0).toLocaleString("en-US");
        return `${p.name}<br/>营业额 ¥${n}<br/><span style="color:#9C9A93">金币 ¥${Number(row.coin || 0).toLocaleString("en-US")} + 现场 ¥${Number(row.offline || 0).toLocaleString("en-US")}</span>`;
      },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: { show: true, lineStyle: { color: "rgba(28,27,25,.12)" } },
      axisTick: { show: false },
      axisLabel: { color: "#9C9A93", fontSize: 11, margin: 10 },
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
        data: vals.map((v, i) => ({
          value: v,
          itemStyle: {
            color: barColor(rows[i]?.d || ""),
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barMaxWidth: 40,
        barCategoryGap: "28%",
        barMinHeight: 4,
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

watch(() => props.rows, render, { deep: true });

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="el" class="week-chart"></div>
</template>

<style scoped>
.week-chart {
  width: 100%;
  height: 100%;
  min-height: 160px;
}
</style>

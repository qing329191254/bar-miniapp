<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Row = { d: string; pts: number; today?: boolean };

const props = defineProps<{ rows: Row[] }>();
const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

function label(d: string) {
  return String(d || "").slice(5);
}

function option() {
  const rows = props.rows.length ? props.rows : [];
  const labels = rows.map((x) => label(x.d));
  const vals = rows.map((x) => Number(x.pts || 0));
  const max = Math.max(...vals, 1);

  return {
    animationDuration: 400,
    grid: { left: 0, right: 0, top: 8, bottom: 0, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(226,75,74,.08)" } },
      backgroundColor: "#fff",
      borderColor: "rgba(28,27,25,.12)",
      textStyle: { color: "#1C1B19", fontSize: 12 },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const row = rows[p.dataIndex];
        const n = Number(p.value || 0).toLocaleString("en-US");
        const tag = row?.today ? ' <span style="color:#A32D2D">（今日）</span>' : "";
        return `${row?.d || p.name}${tag}<br/>发放积分 ${n} 分`;
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
      max: max * 1.12,
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
            color: rows[i]?.today ? "#E24B4A" : "#B5D4F4",
            borderRadius: [3, 3, 0, 0],
          },
        })),
        barMaxWidth: 34,
        barCategoryGap: "32%",
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

watch(() => props.rows, render, { deep: true });

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="el" class="point-trend-chart"></div>
</template>

<style scoped>
.point-trend-chart {
  width: 100%;
  height: 130px;
  min-height: 130px;
}
</style>

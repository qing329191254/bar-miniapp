<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Row = { d: string; coin: number; offline: number; label: string };

const props = defineProps<{ rows: Row[] }>();
const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

function option() {
  const labels = props.rows.map((x) => x.label);
  const vals = props.rows.map((x) => Number(x.coin || 0) + Number(x.offline || 0));
  const max = Math.max(...vals, 1);
  return {
    animationDuration: 400,
    grid: { left: 0, right: 4, top: 22, bottom: 0, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(55,138,221,.08)" } },
      backgroundColor: "#fff",
      borderColor: "rgba(28,27,25,.12)",
      textStyle: { color: "#1C1B19", fontSize: 12 },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const row = props.rows[p.dataIndex] || { coin: 0, offline: 0 };
        const n = Number(p.value || 0).toLocaleString("en-US");
        return `${p.name}<br/>营业额 ¥${n}<br/><span style="color:#9C9A93">金币 ¥${Number(row.coin || 0).toLocaleString("en-US")} + 现场 ¥${Number(row.offline || 0).toLocaleString("en-US")}</span>`;
      },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#9C9A93", fontSize: 11, margin: 10 },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: max * 1.2,
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { lineStyle: { color: "rgba(28,27,25,.06)" } },
    },
    series: [
      {
        type: "bar",
        data: vals.map((v) => ({
          value: v,
          itemStyle: {
            color: v > 0
              ? {
                  type: "linear",
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: "#5BA3E8" },
                    { offset: 1, color: "#378ADD" },
                  ],
                }
              : "#E6F1FB",
          },
        })),
        barWidth: "56%",
        barCategoryGap: "18%",
        barMinHeight: 3,
        itemStyle: { borderRadius: [5, 5, 0, 0] },
        label: {
          show: true,
          position: "top",
          distance: 5,
          fontSize: 10,
          color: "#9C9A93",
          formatter: (p: any) => (p.value > 0 ? `¥${Number(p.value).toLocaleString("en-US")}` : ""),
        },
      },
    ],
  };
}

function render() {
  chart?.setOption(option(), true);
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
  height: 188px;
}
</style>

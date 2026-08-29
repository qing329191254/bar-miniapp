<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import BizTrendChart from "./BizTrendChart.vue";
import { buildChartSlice, type BizMetric } from "./bizChartUtil";
import AppPagination from "../components/AppPagination.vue";
import AppDateInput from "../components/AppDateInput.vue";

const router = useRouter();
const preset = ref("7d");
const dateFrom = ref("");
const dateTo = ref("");
const chartMetric = ref<BizMetric>("biz");
const data = ref<any>(null);
const loading = ref(true);
const refreshing = ref(false);
const err = ref("");

let loadSeq = 0;
let loadCtrl: AbortController | null = null;

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function weekName(d: string) {
  const w = new Date(`${d}T00:00:00`).getDay();
  return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][w];
}
function bizOf(row: { coin: number; offline: number }) {
  return Number(row.coin || 0) + Number(row.offline || 0);
}
function metricVal(row: any, metric: BizMetric) {
  if (metric === "recharge") return row.recharge || 0;
  if (metric === "orders") return row.orders || 0;
  if (metric === "guests") return row.guests || 0;
  return bizOf(row);
}
function back() {
  router.push("/dash");
}
function setPreset(p: string) {
  if (p !== "custom" && p === preset.value) return;
  preset.value = p;
  if (p !== "custom") {
    dateFrom.value = "";
    dateTo.value = "";
    load(true);
  }
}
function onCustomDateChange() {
  clampCustomDates();
  if (preset.value === "custom" && dateFrom.value && dateTo.value) load(true);
}
function clampCustomDates() {
  const cap = data.value?.today || todayMax();
  if (dateTo.value && dateTo.value > cap) dateTo.value = cap;
  if (dateFrom.value && dateFrom.value > cap) dateFrom.value = cap;
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) {
    dateFrom.value = dateTo.value;
  }
}
function todayMax() {
  return new Date().toISOString().slice(0, 10);
}

const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);

const rows = computed(() => data.value?.rows || []);
const rowTotal = computed(() => data.value?.rowTotal ?? 0);
const summary = computed(() => data.value?.summary || { biz: 0, avg: 0, recharge: 0, days: 0, coin: 0, offline: 0, orders: 0, guests: 0 });
const peak = computed(() => data.value?.peak);

const chartSlice = computed(() => buildChartSlice(data.value?.chartRows || data.value?.rows || [], data.value?.today || ""));
const chartRows = computed(() => chartSlice.value.rows);
const chartGranularity = computed(() => chartSlice.value.granularity);
const chartPeak = computed(() => {
  if (!chartRows.value.length) return 0;
  return Math.max(...chartRows.value.map((r) => metricVal(r, chartMetric.value)), 0);
});
const chartTitle = computed(() => {
  const map: Record<BizMetric, string> = { biz: "营业趋势", recharge: "充值趋势", orders: "订单趋势", guests: "到店趋势" };
  return map[chartMetric.value];
});
const chartNote = computed(() => chartSlice.value.hint);

function resetTablePage() {
  tablePage.value = 1;
}

async function load(resetPage = false) {
  if (resetPage) resetTablePage();
  loadCtrl?.abort();
  loadCtrl = new AbortController();
  const ctrl = loadCtrl;
  const seq = ++loadSeq;
  const initial = !data.value;

  if (initial) loading.value = true;
  refreshing.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value, { preset: preset.value }));
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    const next = await api(`/admin/daily-biz?${params}`, { signal: ctrl.signal });
    if (seq !== loadSeq) return;
    data.value = next;
  } catch (e: any) {
    if (e?.name === "AbortError") {
      if (seq === loadSeq) refreshing.value = false;
      return;
    }
    if (seq !== loadSeq) return;
    err.value = e?.message || "加载失败";
  } finally {
    if (seq === loadSeq) {
      loading.value = false;
      refreshing.value = false;
    }
  }
}

onMounted(load);
onBeforeUnmount(() => loadCtrl?.abort());
watch([tablePage, tablePageSize], () => load());
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">营业一览</span>
      <em v-if="data" class="hdr-note">历史每日营业记录 · 共 {{ data.totalDays }} 天有记录</em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回看板</button>
    </div>

    <div class="card flt-card">
      <div class="st">筛选 <em>当前范围：{{ data?.rangeLabel || "…" }}</em></div>
      <div class="flt-chips" :class="{ refreshing }">
        <span
          v-for="[p, label] in PRESETS"
          :key="p"
          class="chip"
          :class="{ on: preset === p }"
          @click="setPreset(p)"
        >{{ label }}</span>
      </div>
      <div v-if="preset === 'custom'" class="flt-custom">
        <span class="tiny">起</span>
        <AppDateInput v-model="dateFrom" :max="data?.today || todayMax()" @change="onCustomDateChange" />
        <span class="tiny">止</span>
        <AppDateInput v-model="dateTo" :max="data?.today || todayMax()" @change="onCustomDateChange" />
        <span v-if="!dateFrom || !dateTo" class="tiny flt-custom-hint">请选择起止日期</span>
      </div>
    </div>

    <div v-if="loading && !data" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err && !data" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
      <p v-if="err" class="load-err">{{ err }} <button class="btn sm ghost" @click="load">重试</button></p>
      <div class="cards">
        <div class="mtr">
          <div class="k">区间营业额</div>
          <div class="v">¥{{ fmt(summary.biz) }}</div>
          <div class="tiny">{{ summary.days }} 天合计</div>
        </div>
        <div class="mtr">
          <div class="k">日均营业额</div>
          <div class="v">¥{{ fmt(summary.avg) }}</div>
          <div class="tiny">区间内平均</div>
        </div>
        <div class="mtr">
          <div class="k">区间充值</div>
          <div class="v">¥{{ fmt(summary.recharge) }}</div>
          <div class="tiny">现金实收口径</div>
        </div>
        <div class="mtr">
          <div class="k">峰值日</div>
          <div class="v peak-day">{{ peak ? peak.d.slice(5) : "—" }}</div>
          <div class="tiny">{{ peak ? `¥${fmt(peak.biz)}` : "无数据" }}</div>
        </div>
      </div>

      <div class="biz-blocks">
        <div class="card chart-card">
          <div class="st">{{ chartTitle }} <em>{{ chartNote }}</em></div>
          <div class="chart-body">
            <BizTrendChart
              :rows="chartRows"
              :metric="chartMetric"
              :peak-val="chartPeak"
              :granularity="chartGranularity"
            />
          </div>
        </div>

        <div class="card table-card">
        <table class="tb2 tb-biz" data-cols="lccccccc">
          <colgroup>
            <col style="width:14%" /><col style="width:9%" /><col style="width:14%" />
            <col style="width:14%" /><col style="width:14%" /><col style="width:14%" />
            <col style="width:10%" /><col style="width:11%" />
          </colgroup>
          <thead>
            <tr>
              <th>日期</th><th>星期</th><th>金币消费</th><th>现场收款</th><th>营业额</th><th>充值额</th><th>订单数</th><th>到店人次</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.d" :class="{ 'row-today': r.d === data.today }">
              <td class="col-date">
                <b>{{ r.d }}</b>
                <span v-if="r.d === data.today" class="pill today-pill">今日</span>
              </td>
              <td class="col-muted">{{ weekName(r.d) }}</td>
              <td class="col-num">¥{{ fmt(r.coin) }}</td>
              <td class="col-num">¥{{ fmt(r.offline) }}</td>
              <td class="col-num"><b>¥{{ fmt(bizOf(r)) }}</b></td>
              <td class="col-num col-recharge">¥{{ fmt(r.recharge) }}</td>
              <td class="col-num">{{ r.orders }}</td>
              <td class="col-muted">{{ r.guests }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="8" class="tiny empty-row">所选时间范围内无营业记录</td>
            </tr>
          </tbody>
          <tfoot v-if="rows.length">
            <tr class="tb-foot biz-foot">
              <td class="col-date"><b>合计</b></td>
              <td class="col-muted">{{ summary.days }} 天</td>
              <td class="col-num">¥{{ fmt(summary.coin) }}</td>
              <td class="col-num">¥{{ fmt(summary.offline) }}</td>
              <td class="col-num"><b>¥{{ fmt(summary.biz) }}</b></td>
              <td class="col-num col-recharge">¥{{ fmt(summary.recharge) }}</td>
              <td class="col-num">{{ summary.orders }}</td>
              <td class="col-muted">{{ summary.guests }}</td>
            </tr>
          </tfoot>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>
      </div>

      <div class="note">
        <b>口径：</b>营业额 = 金币消费 + 现场收款；充值额单独统计（充值只是资金进入，尚未消费，不计入营业额，避免双重计算）。<b>赠送金币消费不计收入</b>，故金币消费额按本金口径统计。<br />
        <b>到店人次口径：</b>仅统计当营业日有消费的注册会员去重数，<b>未注册顾客与纯现金客不计入，数值系统性偏小，仅供趋势参考</b>，不可用于测算人均消费。
      </div>
    </template>
  </div>
</template>

<style scoped>
.flt-card {
  margin-bottom: 12px;
}
.flt-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.flt-chips.refreshing {
  opacity: 0.72;
  pointer-events: none;
}
.load-err {
  margin: 0 0 10px;
  padding: 8px 12px;
  font-size: 12px;
  color: #a32d2d;
  background: #fcebeb;
  border-radius: 8px;
}
.flt-custom {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.flt-custom-hint {
  color: var(--ink3);
  margin-left: 2px;
}
.peak-day {
  font-size: 17px;
}
.biz-blocks {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 12px;
}
.biz-blocks .card {
  margin-bottom: 0 !important;
}
.chart-card {
  display: flex;
  flex-direction: column;
  padding-bottom: 10px;
}
.chart-body {
  margin-top: auto;
  padding-top: 6px;
}
.table-card {
  padding: 0;
  overflow: auto;
}
:deep(.tb-biz) {
  table-layout: fixed;
  font-size: 12px;
  width: 100%;
}
:deep(.tb-biz th),
:deep(.tb-biz td) {
  vertical-align: middle;
  padding: 9px 8px;
}
:deep(.tb-biz th) {
  font-size: 11px;
  font-weight: 400;
  color: var(--ink3);
  padding-top: 7px;
  padding-bottom: 7px;
  background: #fff;
}
:deep(.tb-biz td) {
  border-bottom: 1px solid var(--line);
}
.col-date {
  text-align: left !important;
}
.col-date b {
  font-weight: 500;
}
.col-num {
  text-align: center !important;
}
.col-muted {
  text-align: center !important;
  color: var(--ink3);
  font-size: 12px;
}
.row-today {
  background: var(--goldbg);
}
.row-today td {
  border-bottom-color: rgba(186, 117, 23, 0.2);
}
.today-pill {
  background: var(--gold);
  color: #fff;
  margin-left: 5px;
  font-size: 11px;
  vertical-align: middle;
  padding: 2px 9px;
}
.col-recharge {
  color: var(--blue);
}
.biz-foot td {
  background: #faf9f5 !important;
  font-weight: 600;
  border-bottom: none;
}
.biz-foot .col-muted {
  font-weight: 400;
}
.empty-row {
  text-align: center;
  padding: 26px;
  color: var(--ink3);
}
</style>

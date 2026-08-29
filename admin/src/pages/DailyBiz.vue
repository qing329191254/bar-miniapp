<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import BizTrendChart from "./BizTrendChart.vue";

const router = useRouter();
const preset = ref("7d");
const dateFrom = ref("");
const dateTo = ref("");
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");

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
function back() {
  router.push("/dash");
}
function setPreset(p: string) {
  preset.value = p;
  if (p !== "custom") {
    dateFrom.value = "";
    dateTo.value = "";
  }
  load();
}

const rows = computed(() => data.value?.rows || []);
const summary = computed(() => data.value?.summary || { biz: 0, avg: 0, recharge: 0, days: 0, coin: 0, offline: 0, orders: 0, guests: 0 });
const peak = computed(() => data.value?.peak);
const chartNote = computed(() => {
  const n = data.value?.chart?.length || 0;
  const total = rows.value.length;
  if (!n) return "";
  return n < total ? `仅显示最近 ${n} 天` : "区间全量";
});

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const q = new URLSearchParams({ preset: preset.value });
    if (preset.value === "custom") {
      if (dateFrom.value) q.set("from", dateFrom.value);
      if (dateTo.value) q.set("to", dateTo.value);
    }
    data.value = await api(`/admin/daily-biz?${q}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
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
      <div class="flt-chips">
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
        <input v-model="dateFrom" type="date" class="inp flt-date" @change="load" />
        <span class="tiny">止</span>
        <input v-model="dateTo" type="date" class="inp flt-date" @change="load" />
      </div>
    </div>

    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
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

      <div class="card chart-card">
        <div class="st">营业趋势 <em>{{ chartNote }}</em></div>
        <BizTrendChart :rows="data.chart || []" :peak-biz="peak?.biz || 0" />
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even tb-biz" data-cols="lccccccc">
          <thead>
            <tr>
              <th>日期</th><th>星期</th><th>金币消费</th><th>现场收款</th><th>营业额</th><th>充值额</th><th>订单数</th><th>到店人次</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.d" :class="{ 'row-today': r.d === data.today }">
              <td>
                <b>{{ r.d }}</b>
                <span v-if="r.d === data.today" class="pill today-pill">今日</span>
              </td>
              <td class="mut">{{ weekName(r.d) }}</td>
              <td>¥{{ fmt(r.coin) }}</td>
              <td>¥{{ fmt(r.offline) }}</td>
              <td><b>¥{{ fmt(bizOf(r)) }}</b></td>
              <td class="recharge">¥{{ fmt(r.recharge) }}</td>
              <td>{{ r.orders }}</td>
              <td class="mut">{{ r.guests }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="8" class="tiny empty-row">所选时间范围内无营业记录</td>
            </tr>
          </tbody>
          <tfoot v-if="rows.length">
            <tr class="tb-foot">
              <td><b>合计</b></td>
              <td class="mut">{{ summary.days }} 天</td>
              <td>¥{{ fmt(summary.coin) }}</td>
              <td>¥{{ fmt(summary.offline) }}</td>
              <td><b>¥{{ fmt(summary.biz) }}</b></td>
              <td class="recharge">¥{{ fmt(summary.recharge) }}</td>
              <td>{{ summary.orders }}</td>
              <td>{{ summary.guests }}</td>
            </tr>
          </tfoot>
        </table>
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
.flt-custom {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.flt-date {
  width: auto;
  max-width: 150px;
  margin: 0;
}
.peak-day {
  font-size: 17px;
}
.chart-card {
  margin-bottom: 12px;
}
.table-card {
  padding: 0;
  overflow: auto;
}
.tb-biz {
  table-layout: fixed;
}
.row-today {
  background: var(--goldbg);
}
.today-pill {
  background: var(--gold);
  color: #fff;
  margin-left: 5px;
  font-size: 11px;
}
.recharge {
  color: var(--blue);
}
.empty-row {
  text-align: center;
  padding: 26px;
  color: var(--ink3);
}
</style>

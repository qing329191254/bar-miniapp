<script setup>
import { computed, ref, watch } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const KIND_TITLE = {
  accept: "接单明细",
  pay: "收款明细",
  verify: "核销明细",
  game: "对局录入明细",
};
const PRESETS = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];
const ODST = {
  PENDING_PAY: ["待付款", "gold"],
  PENDING_ACCEPT: ["待接单", "blue"],
  MAKING: ["制作中", "blue"],
  FINISHED: ["已完成", "green"],
  CANCELLED: ["已取消", "grey"],
  CLOSED: ["已关闭", "grey"],
  REFUNDED: ["已退款", "red"],
};
const PAID_OD = ["MAKING", "FINISHED"];
const weekNames = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

const kind = ref("accept");
const preset = ref("today");
const customFrom = ref("");
const customTo = ref("");
const stat = ref(null);
const members = ref([]);
const loading = ref(false);

const memberMap = computed(() => {
  const m = {};
  members.value.forEach((x) => {
    m[x.id] = x;
  });
  return m;
});
const multiDay = computed(() => {
  const r = stat.value?.range;
  if (r?.from && r?.to) return r.from !== r.to;
  return !["today", "yday"].includes(preset.value);
});
const rangeLabel = computed(() => stat.value?.range?.label || clientRangeLabel());

const orders = computed(() => stat.value?.ods || []);
const paidOrders = computed(() => orders.value.filter((o) => PAID_OD.includes(o.status)));
const recharges = computed(() => stat.value?.rcs || []);
const verifies = computed(() => stat.value?.vfs || []);
const games = computed(() => stat.value?.gms || []);

const acceptPaidAmt = computed(() => paidOrders.value.reduce((s, o) => s + Number(o.total || 0), 0));
const verifyByTpl = computed(() => {
  const m = {};
  verifies.value.forEach((v) => {
    const k = v.tplName || "未知卡型";
    m[k] = (m[k] || 0) + 1;
  });
  return Object.entries(m).sort((a, b) => b[1] - a[1]);
});
const gameHeads = computed(() => games.value.reduce((s, g) => s + (g.players?.length || 0), 0));
const gamePts = computed(() =>
  games.value.reduce((s, g) => s + (g.players || []).reduce((a, p) => a + Number(p.pts || 0), 0), 0),
);
const gameShs = computed(() =>
  games.value.reduce((s, g) => s + (g.players || []).reduce((a, p) => a + Number(p.sh || 0), 0), 0),
);

const payByDay = computed(() => {
  const m = {};
  recharges.value.forEach((r) => {
    const d = dayOf(r.at);
    if (!d) return;
    m[d] = m[d] || { rc: 0, od: 0 };
    m[d].rc += Number(r.amount || 0);
  });
  paidOrders.value.forEach((o) => {
    const d = dayOf(o.at);
    if (!d) return;
    m[d] = m[d] || { rc: 0, od: 0 };
    m[d].od += Number(o.total || 0);
  });
  return Object.keys(m)
    .sort((a, b) => b.localeCompare(a))
    .map((d) => ({ d, ...m[d], total: m[d].rc + m[d].od }));
});

onLoad((opts) => {
  kind.value = opts?.kind || "accept";
  uni.setNavigationBarTitle({ title: KIND_TITLE[kind.value] || "作业明细" });
  load();
});

watch([preset, customFrom, customTo], () => load());

function businessTodayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function shiftDay(base, days) {
  const d = new Date(`${base}T12:00:00`);
  d.setDate(d.getDate() + days);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function clientRangeLabel() {
  const t = businessTodayStr();
  switch (preset.value) {
    case "today":
      return t;
    case "yday":
      return shiftDay(t, -1);
    case "7d":
      return `${shiftDay(t, -6)} ~ ${t}`;
    case "30d":
      return `${shiftDay(t, -29)} ~ ${t}`;
    case "month":
      return `${t.slice(0, 7)}-01 ~ ${t}`;
    case "all":
      return "全部时间";
    case "custom":
      if (customFrom.value && customTo.value) {
        return customFrom.value === customTo.value ? customFrom.value : `${customFrom.value} ~ ${customTo.value}`;
      }
      return "自定义";
    default:
      return "今天";
  }
}
function dayOf(s) {
  return String(s || "").slice(0, 10);
}
function weekName(d) {
  const dt = new Date(`${d}T12:00:00`);
  return weekNames[dt.getDay()] || "";
}
function tm(s) {
  const v = String(s || "");
  return multiDay.value ? v.slice(5) : v.slice(11);
}
function userLabel(uid, nick) {
  const m = memberMap.value[uid];
  if (m) return `${m.nick}${m.tail ? " " + m.tail : ""}`;
  return nick || "—";
}
function odStyle(status) {
  const x = ODST[status] || [status, "grey"];
  const map = {
    gold: { bg: "#FAEEDA", color: "#BA7517" },
    blue: { bg: "#E6F1FB", color: "#185FA5" },
    green: { bg: "#EAF3DE", color: "#3B6D11" },
    grey: { bg: "#F1EFE9", color: "#9C9A93" },
    red: { bg: "#FCEBEB", color: "#A32D2D" },
  };
  const s = map[x[1]] || map.grey;
  return { label: x[0], bg: s.bg, color: s.color };
}
function groupByDay(list, getT) {
  const m = {};
  list.forEach((x) => {
    const d = dayOf(getT(x));
    if (!d) return;
    (m[d] = m[d] || []).push(x);
  });
  return Object.keys(m)
    .sort((a, b) => b.localeCompare(a))
    .map((d) => ({ d, items: m[d] }));
}
function itemNames(items) {
  return (items || [])
    .map((i) => `${i.name}${Number(i.qty) > 1 ? "×" + i.qty : ""}`)
    .join("、");
}
function setPreset(p) {
  if (p !== "custom") {
    customFrom.value = "";
    customTo.value = "";
  }
  preset.value = p;
}
function onCustomFrom(e) {
  customFrom.value = e.detail.value || "";
}
function onCustomTo(e) {
  customTo.value = e.detail.value || "";
}
function jobsQuery() {
  let q = `preset=${encodeURIComponent(preset.value)}`;
  if (preset.value === "custom") {
    if (customFrom.value) q += `&from=${encodeURIComponent(customFrom.value)}`;
    if (customTo.value) q += `&to=${encodeURIComponent(customTo.value)}`;
  }
  return q;
}
async function load() {
  loading.value = true;
  try {
    stat.value = await api(`/staff/jobs?${jobsQuery()}`);
    if ((kind.value === "verify" || kind.value === "pay" || kind.value === "accept") && !members.value.length) {
      members.value = await api("/staff/members");
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <view class="pbody" v-if="stat">
    <view class="card flt-card">
      <view class="sec-head">
        <view class="h2 sec-title">时间范围</view>
        <text class="sec-hint">{{ rangeLabel }}</text>
      </view>
      <view class="chip-row">
        <text
          v-for="p in PRESETS"
          :key="p[0]"
          class="chip"
          :class="{ on: preset === p[0] }"
          @tap="setPreset(p[0])"
        >{{ p[1] }}</text>
      </view>
      <view v-if="preset === 'custom'" class="custom-range">
        <view class="custom-row">
          <text class="custom-lbl">起</text>
          <picker mode="date" :value="customFrom" @change="onCustomFrom">
            <view class="custom-inp">{{ customFrom || "选择开始日期" }}</view>
          </picker>
        </view>
        <view class="custom-row">
          <text class="custom-lbl">止</text>
          <picker mode="date" :value="customTo" @change="onCustomTo">
            <view class="custom-inp">{{ customTo || "选择结束日期" }}</view>
          </picker>
        </view>
      </view>
    </view>

    <!-- 接单 -->
    <template v-if="kind === 'accept'">
      <view class="card sum-card">
        <view class="row between">
          <view>
            <view class="tiny">{{ rangeLabel }} 接单</view>
            <view class="sum-num">{{ orders.length }} 单</view>
          </view>
          <view style="text-align:right">
            <view class="tiny">其中已收款金额</view>
            <view class="sum-gold">¥{{ fmt(acceptPaidAmt) }}</view>
          </view>
        </view>
      </view>
      <template v-if="orders.length">
        <template v-if="multiDay">
          <view v-for="g in groupByDay(orders, (o) => o.at)" :key="g.d" class="day-block">
            <view class="day-hd">
              <text class="day-date">{{ g.d.slice(5) }}</text>
              <text class="day-week">{{ weekName(g.d) }}</text>
              <text class="day-extra">{{ g.items.length }} 单 · ¥{{ fmt(g.items.filter((o) => PAID_OD.includes(o.status)).reduce((s, o) => s + o.total, 0)) }}</text>
            </view>
            <view class="card item-card" v-for="o in g.items" :key="o.id">
              <view class="row">
                <text class="item-title">{{ userLabel(o.uid, o.nick) }}</text>
                <text class="pill" :style="{ background: odStyle(o.status).bg, color: odStyle(o.status).color }">{{ odStyle(o.status).label }}</text>
                <text class="item-amt gold">¥{{ fmt(o.total) }}</text>
              </view>
              <view class="item-sub">{{ o.no }} · {{ o.tableName || "未指定桌台" }} · {{ tm(o.at) }}</view>
              <view class="item-sub" v-if="o.items?.length">{{ itemNames(o.items) }}</view>
            </view>
          </view>
        </template>
        <template v-else>
          <view class="card item-card" v-for="o in orders" :key="o.id">
            <view class="row">
              <text class="item-title">{{ userLabel(o.uid, o.nick) }}</text>
              <text class="pill" :style="{ background: odStyle(o.status).bg, color: odStyle(o.status).color }">{{ odStyle(o.status).label }}</text>
              <text class="item-amt gold">¥{{ fmt(o.total) }}</text>
            </view>
            <view class="item-sub">{{ o.no }} · {{ o.tableName || "未指定桌台" }} · {{ tm(o.at) }}</view>
            <view class="item-sub" v-if="o.items?.length">{{ itemNames(o.items) }}</view>
          </view>
        </template>
      </template>
      <view v-else class="empty">所选时间范围内暂无接单</view>
      <view class="note">仅统计本人经手（接单或确认收款）的订单，按下单时间倒序。金额只计已收款状态（制作中 / 已完成）。</view>
    </template>

    <!-- 收款 -->
    <template v-else-if="kind === 'pay'">
      <view class="card sum-card">
        <view class="sec-head" style="margin-bottom:8px">
          <view class="h2 sec-title">{{ rangeLabel }} 收款合计</view>
          <text class="sec-hint">充值 + 点单</text>
        </view>
        <view class="sum-big">¥{{ fmt(stat.amount) }}</view>
        <view class="pay-grid">
          <view class="pay-box blue">
            <view class="tiny blue-t">充值总数</view>
            <view class="pay-num blue-t">¥{{ fmt(stat.rcAmt) }}</view>
            <view class="tiny blue-t">{{ recharges.length }} 笔</view>
          </view>
          <view class="pay-box gold">
            <view class="tiny gold-t">点单总数</view>
            <view class="pay-num gold-t">¥{{ fmt(stat.odAmt) }}</view>
            <view class="tiny gold-t">{{ paidOrders.length }} 笔</view>
          </view>
        </view>
      </view>
      <view class="card" v-if="multiDay && payByDay.length > 1">
        <view class="sec-head">
          <view class="h2 sec-title">按日汇总</view>
          <text class="sec-hint">{{ payByDay.length }} 天有收款</text>
        </view>
        <view class="li" v-for="d in payByDay" :key="d.d">
          <view class="gr">
            <view style="font-weight:500">{{ d.d.slice(5) }} {{ weekName(d.d) }}</view>
            <view class="li-sub">充值 ¥{{ fmt(d.rc) }} · 点单 ¥{{ fmt(d.od) }}</view>
          </view>
          <text style="font-weight:600">¥{{ fmt(d.total) }}</text>
        </view>
      </view>
      <view class="card">
        <view class="sec-head">
          <view class="h2 sec-title">充值收款</view>
          <text class="sec-hint">{{ recharges.length }} 笔 · ¥{{ fmt(stat.rcAmt) }}</text>
        </view>
        <view v-if="recharges.length">
          <view class="li" v-for="r in recharges" :key="r.id">
            <view class="gr">
              <view style="font-weight:500">{{ userLabel(r.uid) }}</view>
              <view class="li-sub">{{ r.no }} · {{ tm(r.at) }}</view>
            </view>
            <view style="text-align:right">
              <view style="font-weight:600;color:#185FA5">¥{{ fmt(r.amount) }}</view>
              <view class="tiny">赠 {{ fmt(r.bonus) }}</view>
            </view>
          </view>
        </view>
        <view v-else class="empty-inline">所选范围无充值收款</view>
      </view>
      <view class="card">
        <view class="sec-head">
          <view class="h2 sec-title">点单收款</view>
          <text class="sec-hint">{{ paidOrders.length }} 笔 · ¥{{ fmt(stat.odAmt) }}</text>
        </view>
        <view v-if="paidOrders.length">
          <view class="li" v-for="o in paidOrders" :key="o.id">
            <view class="gr">
              <view style="font-weight:500">{{ userLabel(o.uid, o.nick) }}</view>
              <view class="li-sub">{{ o.no }} · {{ tm(o.at) }} · {{ o.payType === "COIN" ? "金币" : "现场" }}</view>
            </view>
            <text style="font-weight:600;color:#BA7517">¥{{ fmt(o.total) }}</text>
          </view>
        </view>
        <view v-else class="empty-inline">所选范围无点单收款</view>
      </view>
      <view class="note">口径：充值按实收现金额计（赠送金币不计收入）；点单按订单实付额计。两项相加即「我经手金额」。</view>
    </template>

    <!-- 核销 -->
    <template v-else-if="kind === 'verify'">
      <view class="card sum-card">
        <view class="row between">
          <view>
            <view class="tiny">{{ rangeLabel }} 核销</view>
            <view class="sum-num">{{ verifies.length }} 张</view>
          </view>
          <view style="text-align:right">
            <view class="tiny">涉及卡型</view>
            <view class="sum-gold">{{ verifyByTpl.length }} 种</view>
          </view>
        </view>
      </view>
      <view class="card" v-if="verifyByTpl.length">
        <view class="h2">按卡型汇总</view>
        <view class="li" v-for="[name, count] in verifyByTpl" :key="name">
          <view class="gr"><view style="font-weight:500">{{ name }}</view></view>
          <text style="font-weight:600">{{ count }} 张</text>
        </view>
      </view>
      <view class="card">
        <view class="sec-head">
          <view class="h2 sec-title">核销流水</view>
          <text class="sec-hint">{{ verifies.length }} 条</text>
        </view>
        <template v-if="verifies.length">
          <template v-if="multiDay">
            <view v-for="g in groupByDay(verifies, (v) => v.at)" :key="g.d">
              <view class="day-hd compact">
                <text class="day-date">{{ g.d.slice(5) }}</text>
                <text class="day-week">{{ weekName(g.d) }}</text>
                <text class="day-extra">{{ g.items.length }} 张</text>
              </view>
              <view class="li" v-for="v in g.items" :key="v.id">
                <view class="gr">
                  <view style="font-weight:500">{{ v.tplName }}</view>
                  <view class="li-sub">{{ userLabel(v.uid) }} · {{ v.cardNo }}</view>
                </view>
                <text class="tiny">{{ tm(v.at) }}</text>
              </view>
            </view>
          </template>
          <view v-else class="li" v-for="v in verifies" :key="v.id">
            <view class="gr">
              <view style="font-weight:500">{{ v.tplName }}</view>
              <view class="li-sub">{{ userLabel(v.uid) }} · {{ v.cardNo }}</view>
            </view>
            <text class="tiny">{{ tm(v.at) }}</text>
          </view>
        </template>
        <view v-else class="empty-inline">所选时间范围内暂无核销</view>
      </view>
      <view class="note">核销流水不可修改，如需撤销请联系店长在 Web 端处理。</view>
    </template>

    <!-- 对局 -->
    <template v-else-if="kind === 'game'">
      <view class="card sum-card">
        <view class="sec-head" style="margin-bottom:8px">
          <view class="h2 sec-title">{{ rangeLabel }} 录入</view>
          <text class="sec-hint">{{ games.length }} 局 · {{ gameHeads }} 人次</text>
        </view>
        <view class="pay-grid">
          <view class="pay-box purple">
            <view class="tiny purple-t">发出碎片</view>
            <view class="pay-num purple-t">{{ fmt(gameShs) }}</view>
          </view>
          <view class="pay-box gold">
            <view class="tiny gold-t">发出积分</view>
            <view class="pay-num gold-t">{{ fmt(gamePts) }}</view>
          </view>
        </view>
      </view>
      <template v-if="games.length">
        <template v-if="multiDay">
          <view v-for="g in groupByDay(games, (x) => x.time)" :key="g.d" class="day-block">
            <view class="day-hd">
              <text class="day-date">{{ g.d.slice(5) }}</text>
              <text class="day-week">{{ weekName(g.d) }}</text>
              <text class="day-extra">{{ g.items.length }} 局</text>
            </view>
            <view class="card item-card" v-for="gm in g.items" :key="gm.id">
              <view class="row">
                <text class="item-title">{{ gm.pname }}</text>
                <text v-if="gm.table" class="pill table-pill">{{ gm.table }}</text>
                <text class="tiny" style="margin-left:auto">{{ tm(gm.time) }}</text>
              </view>
              <view class="item-sub">{{ (gm.players || []).map((p) => p.nick + (p.pts ? '（冠军 +' + fmt(p.pts) + ' 分）' : '')).join('、') }}</view>
              <view class="item-sub purple">每人碎片 {{ fmt(gm.players?.[0]?.sh || 0) }} · 共 {{ gm.players?.length || 0 }} 人</view>
            </view>
          </view>
        </template>
        <template v-else>
          <view class="card item-card" v-for="gm in games" :key="gm.id">
            <view class="row">
              <text class="item-title">{{ gm.pname }}</text>
              <text v-if="gm.table" class="pill table-pill">{{ gm.table }}</text>
              <text class="tiny" style="margin-left:auto">{{ tm(gm.time) }}</text>
            </view>
            <view class="item-sub">{{ (gm.players || []).map((p) => p.nick + (p.pts ? '（冠军 +' + fmt(p.pts) + ' 分）' : '')).join('、') }}</view>
            <view class="item-sub purple">每人碎片 {{ fmt(gm.players?.[0]?.sh || 0) }} · 共 {{ gm.players?.length || 0 }} 人</view>
          </view>
        </template>
      </template>
      <view v-else class="empty">所选时间范围内暂无对局录入</view>
      <view class="note">对局录入后立即入账，C 端积分 / 碎片 / 榜单同步更新。录错需店长在 Web 端「对局记录查询」撤销。</view>
    </template>
  </view>
  <view v-else-if="loading" class="pbody empty">加载中…</view>
</template>

<style scoped>
.flt-card {
  padding: 11px 12px;
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.chip {
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  border-radius: 99px;
  padding: 5px 9px;
  font-size: 11.5px;
  color: #6b6a65;
}
.chip.on {
  background: #1c1b19;
  color: #fff;
  border-color: #1c1b19;
}
.custom-range {
  margin-top: 8px;
}
.custom-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}
.custom-row:first-child {
  margin-top: 8px;
}
.custom-lbl {
  width: 16px;
  flex-shrink: 0;
  font-size: 11px;
  color: #9c9a93;
}
.custom-inp {
  flex: 1;
  padding: 6px 8px;
  font-size: 12px;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  color: #1c1b19;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 9px;
}
.sec-title {
  margin-bottom: 0;
}
.sec-hint {
  margin-left: auto;
  font-size: 11px;
  color: #9c9a93;
  flex-shrink: 0;
}
.li-sub {
  font-size: 11px;
  color: #6b6a65;
  margin-top: 2px;
  line-height: 1.45;
}
.sum-card {
  background: #faf9f5;
}
.sum-num {
  font-size: 20px;
  font-weight: 600;
  margin-top: 2px;
}
.sum-big {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 10px;
}
.sum-gold {
  font-size: 16px;
  font-weight: 600;
  color: #ba7517;
}
.pay-grid {
  display: flex;
  gap: 8px;
}
.pay-box {
  flex: 1;
  border-radius: 9px;
  padding: 10px;
}
.pay-box.blue {
  background: #e6f1fb;
}
.pay-box.gold {
  background: #faeeda;
}
.pay-box.purple {
  background: #eeedf7;
}
.pay-num {
  font-size: 17px;
  font-weight: 600;
  margin: 2px 0;
}
.blue-t {
  color: #185fa5;
}
.gold-t {
  color: #ba7517;
}
.purple-t {
  color: #534ab7;
}
.item-card {
  padding: 11px 12px;
  margin-bottom: 8px;
}
.item-title {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
}
.item-amt {
  font-weight: 600;
  margin-left: 8px;
}
.item-amt.gold {
  color: #ba7517;
}
.item-sub {
  font-size: 11px;
  color: #6b6a65;
  margin-top: 4px;
  line-height: 1.45;
}
.item-sub.purple {
  color: #534ab7;
  margin-top: 3px;
}
.table-pill {
  background: transparent;
  border: 1px solid rgba(28, 27, 25, 0.12);
  color: #6b6a65;
  margin-left: 6px;
}
.day-block {
  margin-bottom: 4px;
}
.day-hd {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 11px 2px 6px;
}
.day-hd.compact {
  margin-top: 9px;
}
.day-date {
  font-size: 12px;
  font-weight: 600;
}
.day-week {
  font-size: 11px;
  color: #9c9a93;
}
.day-extra {
  margin-left: auto;
  font-size: 11px;
  color: #9c9a93;
}
.empty {
  text-align: center;
  color: #9c9a93;
  padding: 34px 14px;
}
.empty-inline {
  text-align: center;
  color: #9c9a93;
  padding: 16px;
  font-size: 12px;
}
</style>

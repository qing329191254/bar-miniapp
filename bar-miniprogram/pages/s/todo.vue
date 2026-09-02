<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, loadGameDraft, toastText } from "@/utils/api";
import { reminderState, syncReminderSummary } from "@/utils/staff-reminder";

const data = ref(null);
const msg = ref("");
const tab = ref("accept");
const rejectOrder = ref(null);
const rejectReason = ref("");
const rejecting = ref(false);

async function load() {
  data.value = await api("/staff/todo");
  const counts = {
    accept: data.value.accept.length,
    pay: data.value.recharges.length + data.value.payOrders.length,
    wdr: data.value.withdrawals.length,
    making: data.value.making.length,
  };
  if (!counts[tab.value]) {
    const next = Object.keys(counts).find((key) => counts[key] > 0);
    if (next) tab.value = next;
  }
}
onShow(() => {
  load();
  syncReminderSummary(false);
});

const defs = computed(() => {
  if (!data.value) return [];
  return [
    { k: "accept", label: "待接单", n: data.value.accept.length, icon: "accept", tone: "amber" },
    { k: "pay", label: "待收款", n: data.value.recharges.length + data.value.payOrders.length, icon: "pay", tone: "blue" },
    { k: "wdr", label: "待确认提分", n: data.value.withdrawals.length, icon: "wdr", tone: "indigo" },
    { k: "making", label: "制作中", n: data.value.making.length, icon: "making", tone: "slate" },
  ];
});
const total = computed(() => defs.value.reduce((s, d) => s + d.n, 0));
const summaryBrief = computed(() =>
  defs.value
    .filter((x) => x.n)
    .map((x) => `${x.n} ${x.label}`)
    .join(" · "),
);
const draft = computed(() => {
  const d = loadGameDraft();
  return d && d.step >= 1 && d.step <= 4 ? d : null;
});
const cur = computed(() => {
  return defs.value.find((x) => x.k === tab.value) || defs.value[0];
});

async function act(path, reason = "店员操作", successText = "") {
  msg.value = "";
  try {
    await api(path, { method: "POST", body: { reason } });
    await load();
    if (successText) toastText(successText);
    return true;
  } catch (e) {
    msg.value = e.message;
    return false;
  }
}

function openReject(order) {
  rejectOrder.value = order;
  rejectReason.value = "";
  msg.value = "";
}

function closeReject() {
  if (rejecting.value) return;
  rejectOrder.value = null;
  rejectReason.value = "";
}

async function confirmReject() {
  const reason = rejectReason.value.trim();
  if (!reason) {
    msg.value = "请输入拒单原因";
    return;
  }
  if (!rejectOrder.value || rejecting.value) return;
  rejecting.value = true;
  const ok = await act(`/staff/orders/${rejectOrder.value.id}/reject`, reason, "已拒单");
  rejecting.value = false;
  if (ok) closeReject();
}
</script>

<template>
  <page-meta :page-style="`overflow:${rejectOrder ? 'hidden' : 'visible'}`" />
  <app-toast />
  <view class="pbody" v-if="data">
    <view class="reminder-link" :class="{ ok: reminderState.connected, warn: reminderState.fallback }">
      <i />
      <text>{{ reminderState.connected ? "实时提醒已连接" : reminderState.fallback ? "实时连接中断，已启用定时刷新" : "正在连接实时提醒" }}</text>
    </view>
    <view class="todo-overview card" :class="{ clear: !total }">
      <view class="todo-overview-top">
        <view class="todo-overview-main">
          <text class="todo-overview-label">{{ total ? "待处理" : "全部处理完毕" }}</text>
          <view class="todo-overview-total">
            <text class="todo-overview-num">{{ total }}</text>
            <text class="todo-overview-unit">项</text>
          </view>
        </view>
        <view v-if="total" class="todo-overview-brief">{{ summaryBrief }}</view>
        <view v-else class="todo-overview-brief">当前没有需要跟进的订单或单据</view>
      </view>
    </view>
    <view v-if="draft" class="todo-draft card" @tap="go('/pages/s/game', true)">
      <view class="todo-draft-left">
        <view class="todo-draft-dot" />
        <text class="todo-draft-text">有 1 局未提交</text>
      </view>
      <text class="todo-draft-link">继续录入 ›</text>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
    <view class="stodo-tabs">
      <view
        v-for="d in defs"
        :key="d.k"
        class="stodo-tab"
        :class="{ on: cur && cur.k === d.k, empty: !d.n }"
        @tap="tab = d.k"
      >
        <app-icon class="stodo-tab-ic" :name="d.icon" :tone="d.tone" size="sm" shape="soft" />
        <text class="stodo-tab-label">{{ d.label }}</text>
        <text class="stodo-n" :class="{ zero: !d.n }">{{ d.n }}</text>
      </view>
    </view>

    <view v-if="cur && cur.k==='accept'">
      <view class="card" v-for="o in data.accept" :key="o.id" :style="o.lack ? 'border-color:#E9C4C4;background:#FCEBEB' : 'border-color:#BA7517;background:#FAEEDA'">
        <view class="between">
          <text style="font-weight:600">{{ o.user?.nick }} {{ o.user?.tail }}</text>
          <text class="pill">{{ o.tableName || "未指定" }}</text>
        </view>
        <view class="tiny" style="margin:6px 0">{{ (o.items||[]).map(i=>i.name+'×'+i.qty).join('、') }}</view>
        <view class="tiny" v-if="o.lack" style="color:#A32D2D">余额不足，差 {{ o.lack }} 金币</view>
        <view class="between" style="margin-top:8px">
          <text style="font-size:16px;font-weight:600">{{ o.total }} 金币</text>
          <view class="row">
            <button class="btn ghost" @tap="openReject(o)">拒单</button>
            <button class="btn" :disabled="!!o.lack" @tap="act('/staff/orders/'+o.id+'/accept', '店员操作', '接单成功')">接单</button>
          </view>
        </view>
      </view>
      <view class="empty" v-if="!data.accept.length">暂无待接单</view>
    </view>

    <view v-if="cur && cur.k==='pay'">
      <view class="card" v-for="r in data.recharges" :key="'r'+r.id" style="border-color:#185FA5;background:#E6F1FB">
        <view class="between">
          <text class="pill" style="background:#185FA5;color:#fff">充值单</text>
          <text class="tiny" style="color:#A32D2D">{{ r.remain }}</text>
        </view>
        <view class="between" style="margin:8px 0">
          <view><view class="tiny">应收现金</view><view style="font-size:20px;font-weight:700">¥{{ r.amount }}</view></view>
          <view style="text-align:right"><view class="tiny">单号后四位</view><view style="font-size:20px;font-weight:700;color:#A32D2D">{{ String(r.no).slice(-4) }}</view></view>
        </view>
        <view class="tiny">{{ r.user?.nick }} · 到账 {{ r.amount + r.bonus }} 金币</view>
        <view class="row" style="margin-top:8px">
          <button class="btn ghost" @tap="act('/staff/recharges/'+r.id+'/reject')">拒绝</button>
          <button class="btn" @tap="act('/staff/recharges/'+r.id+'/confirm')">确认收款</button>
        </view>
      </view>
      <view class="card" v-for="o in data.payOrders" :key="'o'+o.id">
        <view class="between"><text class="pill">点单</text><text>{{ o.user?.nick }}</text></view>
        <view class="between" style="margin-top:8px">
          <text style="font-weight:700">¥{{ o.total }}</text>
          <button class="btn" @tap="act('/staff/orders/'+o.id+'/confirm-pay')">确认收款</button>
        </view>
      </view>
      <view class="empty" v-if="!data.recharges.length && !data.payOrders.length">暂无待收款</view>
    </view>

    <view v-if="cur && cur.k==='wdr'">
      <view class="card" v-for="w in data.withdrawals" :key="w.id" style="border-color:#534AB7;background:#EEEDFE">
        <view class="between">
          <text class="pill" style="background:#534AB7;color:#fff">提分单</text>
          <text class="tiny">{{ w.remain }}</text>
        </view>
        <view style="font-size:20px;font-weight:700;margin:8px 0">{{ w.pts }} 分</view>
        <view class="tiny">{{ w.user?.nick }} · {{ String(w.no).slice(-4) }}</view>
        <view class="row" style="margin-top:8px">
          <button class="btn ghost" @tap="act('/staff/withdrawals/'+w.id+'/reject')">驳回</button>
          <button class="btn" @tap="act('/staff/withdrawals/'+w.id+'/grant')">确认发放</button>
        </view>
      </view>
      <view class="empty" v-if="!data.withdrawals.length">暂无待确认提分</view>
    </view>

    <view v-if="cur && cur.k==='making'">
      <view class="card" v-for="o in data.making" :key="o.id">
        <view class="between">
          <text style="font-weight:600">{{ o.user?.nick }}</text>
          <text class="tiny">{{ o.tableName }}</text>
        </view>
        <view class="tiny">{{ (o.items||[]).map(i=>i.name+'×'+i.qty).join('、') }}</view>
        <view class="row" style="margin-top:8px;justify-content:flex-end">
          <button class="btn" @tap="act('/staff/orders/'+o.id+'/finish')">出单</button>
        </view>
      </view>
      <view class="empty" v-if="!data.making.length">暂无制作中</view>
    </view>

    <view class="card todo-stat-card">
      <view class="h2">我的今日</view>
      <view class="stat5">
        <view><view class="sb">¥{{ data.stat.amount }}</view><view class="tiny">今日收款</view></view>
        <view><view class="sb">{{ data.stat.orders }}</view><view class="tiny">接单</view></view>
        <view><view class="sb">{{ data.stat.verifies }}</view><view class="tiny">核销</view></view>
        <view><view class="sb">{{ data.stat.games }}</view><view class="tiny">录局</view></view>
        <view><view class="sb">{{ data.stat.wds }}</view><view class="tiny">发分</view></view>
      </view>
      <view class="between todo-shop-amt" v-if="data.shopAmt!=null">
        <text class="tiny">全店今日营业额</text>
        <text class="gold" style="font-weight:700">¥{{ data.shopAmt }}</text>
      </view>
    </view>
    <tab-bar current="todo" />

    <view v-if="rejectOrder" class="reject-mask" @tap="closeReject" @touchmove.stop.prevent>
      <view class="reject-dialog" @tap.stop>
        <view class="reject-title">拒单</view>
        <view class="reject-label">原因 <text class="reject-required">*必填</text></view>
        <textarea
          class="reject-input"
          v-model="rejectReason"
          placeholder="请输入原因"
          maxlength="100"
          :show-confirm-bar="false"
          :focus="true"
        />
        <view class="err" v-if="msg">{{ msg }}</view>
        <view class="reject-actions">
          <button class="btn ghost" :disabled="rejecting" @tap="closeReject">取消</button>
          <button class="btn reject-submit" :disabled="rejecting" @tap="confirmReject">
            {{ rejecting ? "提交中…" : "确认拒单" }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.reminder-link{display:flex;align-items:center;gap:7px;margin:0 2px 9px;color:#9c9a93;font-size:11px}.reminder-link i{display:block;width:7px;height:7px;border-radius:50%;background:#9c9a93}.reminder-link.ok{color:#3b6d11}.reminder-link.ok i{background:#61a72b;box-shadow:0 0 0 4px rgba(97,167,43,.12)}.reminder-link.warn{color:#ba7517}.reminder-link.warn i{background:#d7932e}
.todo-overview {
  padding: 14px 12px 12px;
  background: linear-gradient(180deg, #fff 0%, #faf9f5 100%);
  border-color: rgba(28, 27, 25, 0.1);
}
.todo-overview:not(.clear) {
  border-color: rgba(186, 117, 23, 0.18);
  box-shadow: 0 4px 14px rgba(28, 27, 25, 0.06);
}
.todo-overview.clear {
  background: #f7faf4;
  border-color: #c5ddb0;
}
.todo-overview-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.todo-overview-main {
  flex-shrink: 0;
}
.todo-overview-label {
  display: block;
  font-size: 12px;
  color: #9c9a93;
  line-height: 1.3;
}
.todo-overview-total {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-top: 2px;
}
.todo-overview-num {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: #1c1b19;
  letter-spacing: -0.02em;
}
.todo-overview.clear .todo-overview-num {
  color: #3b6d11;
}
.todo-overview-unit {
  font-size: 13px;
  font-weight: 500;
  color: #6b6a65;
}
.todo-overview-brief {
  flex: 1;
  min-width: 0;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.65;
  color: #6b6a65;
}
.stodo-tab-label {
  flex: 1;
  min-width: 0;
  text-align: left;
}
.stodo-tab.empty .stodo-tab-label {
  color: #9c9a93;
}
.stodo-tab :deep(.app-icon) {
  box-shadow: none;
}
.stodo-tab.on :deep(.app-icon) {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
}
.stodo-n.zero {
  background: #edede8;
  color: #9c9a93;
  min-width: 17px;
}
.stodo-tab.on .stodo-n.zero {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.75);
}
.todo-draft {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #faf5ea, #fff8eb);
  border-color: #e8d4a8;
}
.todo-draft-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.todo-draft-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ba7517;
  flex-shrink: 0;
}
.todo-draft-text {
  font-size: 13px;
  font-weight: 600;
  color: #7a5310;
}
.todo-draft-link {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #ba7517;
}
.todo-stat-card {
  background: linear-gradient(180deg, #faf9f5 0%, #fff 100%);
  border-color: rgba(28, 27, 25, 0.08);
}
.todo-shop-amt {
  border-top: 1px solid rgba(28, 27, 25, 0.08);
  margin-top: 10px;
  padding-top: 9px;
}
.reject-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 30px;
  background: rgba(0, 0, 0, 0.42);
}
.reject-dialog {
  width: 100%;
  max-width: 320px;
  box-sizing: border-box;
  padding: 20px 16px 16px;
  border-radius: 18px;
  background: #fff;
}
.reject-title {
  margin-bottom: 22px;
  color: #1c1b19;
  font-size: 18px;
  font-weight: 700;
}
.reject-label {
  margin-bottom: 7px;
  color: #6b6a65;
  font-size: 13px;
}
.reject-required { color: #b52d2d; }
.reject-input {
  width: 100%;
  height: 72px;
  min-height: 72px;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #d3d1cc;
  border-radius: 10px;
  color: #1c1b19;
  background: #fff;
  font-size: 14px;
}
.reject-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}
.reject-actions .btn {
  flex: 1;
  margin: 0;
  padding: 11px 8px;
}
.reject-submit {
  border-color: #b52d2d;
  background: #b52d2d;
  color: #fff;
}
</style>

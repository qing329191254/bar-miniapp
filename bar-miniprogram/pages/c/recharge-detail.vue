<script setup>
import { computed, onUnmounted, ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { api, toastText } from "@/utils/api";

const data = ref(null);
const me = ref(null);
const now = ref(Date.now());
const msg = ref("");
const createdNo = ref("");
let timer = null;

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const order = computed(() => data.value?.pending || data.value?.latest || null);
const remaining = computed(() => {
  if (!order.value?.expireAt || order.value.status !== "PENDING_PAY") return "—";
  const seconds = Math.max(0, Math.floor((Number(order.value.expireAt) - now.value) / 1000));
  return `${Math.floor(seconds / 60)} 分 ${String(seconds % 60).padStart(2, "0")} 秒`;
});
const noPrefix = computed(() => String(order.value?.no || "").slice(0, -4));
const noTail = computed(() => String(order.value?.no || "").slice(-4));
const paid = computed(() => order.value?.status === "PAID");

async function load(withLoading = true) {
  try {
    const [recharges, mine] = await Promise.all([
      api("/recharges", { loading: withLoading }),
      api("/me", { loading: withLoading }),
    ]);
    data.value = recharges;
    me.value = mine;
    now.value = Date.now();
    if (createdNo.value) {
      toastText("充值单已生成", 2200);
      createdNo.value = "";
    }
  } catch (e) {
    msg.value = e.message;
  }
}

async function cancel() {
  if (!order.value || order.value.status !== "PENDING_PAY") return;
  try {
    await api(`/recharges/${order.value.id}/cancel`, { method: "POST" });
    toastText("充值单已取消");
    setTimeout(() => uni.navigateBack(), 700);
  } catch (e) {
    msg.value = e.message;
  }
}

onLoad((options) => {
  createdNo.value = decodeURIComponent(options?.created || "");
});
onShow(() => {
  load();
  clearInterval(timer);
  let ticks = 0;
  timer = setInterval(() => {
    now.value = Date.now();
    ticks += 1;
    if (ticks % 5 === 0 && order.value?.status === "PENDING_PAY") load(false);
  }, 1000);
});
onUnmounted(() => clearInterval(timer));

function viewMyCoins() {
  uni.navigateTo({ url: "/pages/c/mine" });
}
</script>

<template>
  <view class="detail-page" v-if="order && paid">
    <view class="pay-success">
      <view class="success-ring">✓</view>
      <view class="success-title">充值到账成功</view>
      <view class="success-desc">¥{{ fmt(order.amount) }} + 赠 {{ fmt(order.bonus) }} = {{ fmt(order.amount + order.bonus) }} 金币已入库</view>
    </view>
    <button class="btn block success-btn" @tap="viewMyCoins">查看我的金币</button>
  </view>

  <view class="detail-page" v-else-if="order">
    <view class="card recharge-card">
      <view class="between detail-head">
        <text class="pay-pill">{{ order.status === "PENDING_PAY" ? "待付款" : "已处理" }}</text>
        <text class="remain">{{ remaining }}</text>
      </view>
      <view class="amount-label">充值金额</view>
      <view class="amount">¥{{ fmt(order.amount) }}</view>
      <view class="arrive">到账 {{ fmt(order.amount + order.bonus) }} 金币{{ order.bonus ? "（含赠送 " + fmt(order.bonus) + "）" : "" }}</view>
      <view class="order-info">
        <view class="info-row"><text>单号</text><view class="order-no"><text>{{ noPrefix }}</text><text class="tail">{{ noTail }}</text></view></view>
        <view class="info-row"><text>会员</text><text>{{ me?.user?.nick || "—" }} · {{ me?.user?.no || "—" }}</text></view>
        <view class="info-row"><text>生成时间</text><text>{{ order.created || "—" }}</text></view>
      </view>
    </view>

    <view class="card guide-card">
      <view class="guide-title">到吧台出示此单号</view>
      <view>1. 向店员报单号后四位 <text class="strong">{{ noTail }}</text></view>
      <view>2. 付现金或扫店内收款码</view>
      <view>3. <text class="strong">店员在后台确认后金币立即到账</text></view>
      <view>4. 到账后本页自动跳转</view>
    </view>

    <view class="detail-actions">
      <button class="btn ghost action" @tap="cancel">取消此单</button>
      <button class="btn ghost action" @tap="load">刷新状态</button>
    </view>
    <view v-if="msg" class="err">{{ msg }}</view>
  </view>
  <view v-else class="empty-detail">正在读取充值单…</view>
  <app-toast />
</template>

<style scoped>
.detail-page { padding: 14px 15px 24px; }
.recharge-card { padding: 14px; border: 2px solid #ba7517; background: #fdf4e3; }
.detail-head { margin-bottom: 14px; }
.pay-pill { padding: 5px 11px; border-radius: 18px; background: #c2770b; color: #fff; font-size: 12px; }
.remain { color: #c5221f; font-size: 12px; }
.amount-label { text-align: center; color: #ba7517; font-size: 12px; }
.amount { margin-top: 3px; text-align: center; color: #633806; font-size: 38px; line-height: 1.25; font-weight: 700; }
.arrive { margin: 8px 0 13px; text-align: center; color: #3b6d11; font-size: 13px; }
.order-info { padding: 12px; border-radius: 10px; background: #fff; color: #9c9a93; }
.info-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 3px 0; font-size: 12px; }
.order-no { color: #1c1b19; font-size: 16px; font-weight: 700; letter-spacing: 1px; }
.order-no .tail { margin-left: 5px; color: #a32d2d; font-size: 19px; }
.guide-card { padding: 13px 14px; background: #f5f4f0; color: #9c9a93; font-size: 12px; line-height: 1.9; }
.guide-title { margin-bottom: 5px; color: #1c1b19; font-size: 15px; font-weight: 700; }
.strong { color: #1c1b19; font-weight: 700; }
.detail-actions { display: flex; gap: 8px; }
.detail-actions .action { flex: 1; color: #1c1b19; background: #fff; }
.pay-success { padding: 48px 6px 28px; text-align: center; }
.success-ring {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border: 2px solid #3b6d11;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b6d11;
  background: #eaf3de;
  font-size: 28px;
  line-height: 1;
}
.success-title { color: #1c1b19; font-size: 21px; font-weight: 700; }
.success-desc { margin-top: 8px; color: #6b6a65; font-size: 14px; }
.success-btn { margin-top: 4px; }
.empty-detail { padding: 40px 15px; text-align: center; color: #9c9a93; font-size: 12px; }
</style>

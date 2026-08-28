<script setup>
import { computed, ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { api, go, saveCart } from "@/utils/api";

const TABS = [
  { key: "coin", label: "金币订单" },
  { key: "card", label: "卡包订单" },
  { key: "point", label: "积分订单" },
];
const STATUS = {
  PENDING_PAY: { text: "待付款", tone: "gold" },
  PENDING_ACCEPT: { text: "待接单", tone: "blue" },
  MAKING: { text: "制作中", tone: "blue" },
  FINISHED: { text: "已完成", tone: "green" },
  CANCELLED: { text: "已取消", tone: "grey" },
  CLOSED: { text: "已关闭", tone: "grey" },
  REFUNDED: { text: "已退款", tone: "red" },
};

const tab = ref("coin");
const orders = ref([]);
const cards = ref([]);
const loading = ref(false);
const msg = ref("");
const notice = ref("");
const codeOrder = ref(null);
let noticeTimer = null;

const shownCards = computed(() => {
  if (tab.value === "card") return cards.value.filter((card) => card.status === "USED");
  if (tab.value === "point") return cards.value.filter((card) => card.src === "EXCHANGE");
  return [];
});

function statusOf(order) {
  return STATUS[order.status] || { text: order.status || "未知状态", tone: "grey" };
}
function titleOf(order) {
  return (order.items || []).map((item) => item.name + (item.qty > 1 ? "×" + item.qty : "")).join("、") || order.no;
}
function payText(order) {
  return order.payType === "COIN" ? "金币支付" : "到吧台付款";
}
function orderMeta(order) {
  const parts = [order.ago || order.at, order.tableName || "未指定桌台", payText(order) + " " + order.total];
  if (order.remark) parts.push("备注：" + order.remark);
  return parts.filter(Boolean).join(" · ");
}
function cardMeta(card) {
  return card.srcDesc || (tab.value === "point" ? "积分兑换" : "卡券核销");
}
function showNotice(text) {
  if (noticeTimer) clearTimeout(noticeTimer);
  notice.value = text;
  noticeTimer = setTimeout(() => { notice.value = ""; }, 2200);
}
function finderCell(x, y, left, top) {
  const dx = x - left;
  const dy = y - top;
  if (dx < 0 || dx > 6 || dy < 0 || dy > 6) return null;
  return dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4);
}
function qrCells(code) {
  let seed = 0;
  for (const ch of String(code || "")) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
  return Array.from({ length: 21 * 21 }, (_, index) => {
    const x = index % 21;
    const y = Math.floor(index / 21);
    const finder = finderCell(x, y, 0, 0) ?? finderCell(x, y, 14, 0) ?? finderCell(x, y, 0, 14);
    if (finder !== null) return { index, on: finder };
    seed = (seed * 1103515245 + 12345) >>> 0;
    return { index, on: ((seed >>> 16) % 100) < 48 };
  });
}
function switchTab(next) {
  tab.value = next;
  msg.value = "";
}

async function load() {
  loading.value = true;
  msg.value = "";
  try {
    const [orderList, cardList] = await Promise.all([
      api("/orders", { silent: true }),
      api("/cards", { silent: true }),
    ]);
    orders.value = Array.isArray(orderList) ? orderList : [];
    cards.value = Array.isArray(cardList) ? cardList : [];
  } catch (error) {
    msg.value = error.message || "加载失败";
  } finally {
    loading.value = false;
  }
}
onShow(load);
onLoad((options) => {
  if (!options?.notice) return;
  showNotice(decodeURIComponent(options.notice));
});

function cancel(order) {
  uni.showModal({
    title: "取消订单",
    content: `确认取消订单 ${order.no}？`,
    success: async ({ confirm }) => {
      if (!confirm) return;
      try {
        await api(`/orders/${order.id}/cancel`, { method: "POST" });
        showNotice("订单已取消");
        await load();
      } catch (error) {
        msg.value = error.message || "取消失败";
      }
    },
  });
}

function showOrderCode(order) {
  codeOrder.value = order;
}
function closeOrderCode() {
  codeOrder.value = null;
}

function reorder(order) {
  const lines = (order.items || []).filter((item) => item.pid).map((item) => ({
    pid: Number(item.pid),
    qty: Number(item.qty) || 1,
    specIds: Array.isArray(item.specIds) ? item.specIds : [],
  }));
  if (!lines.length) {
    uni.showToast({ title: "该订单商品已失效", icon: "none" });
    return;
  }
  saveCart(lines);
  uni.showToast({ title: "已加入购物车", icon: "success" });
  go("/pages/c/order");
}
</script>

<template>
  <view class="pbody orders-page">
    <view v-if="notice" class="order-notice">{{ notice }}</view>
    <view class="order-tabs">
      <button
        v-for="item in TABS"
        :key="item.key"
        class="order-tab"
        :class="{ on: tab === item.key }"
        @tap="switchTab(item.key)"
      >{{ item.label }}</button>
    </view>

    <view v-if="loading && !orders.length && !cards.length" class="empty">加载中…</view>
    <view v-else-if="msg && !orders.length && !cards.length" class="card empty-box">
      <view class="err">{{ msg }}</view>
      <button class="btn ghost" @tap="load">重新加载</button>
    </view>

    <template v-else-if="tab === 'coin'">
      <view v-if="!orders.length" class="empty">暂无订单，去点一单吧</view>
      <view v-for="order in orders" :key="order.id" class="card order-card">
        <view class="between">
          <text class="order-name">{{ titleOf(order) }}</text>
          <text class="order-status" :class="'status-' + statusOf(order).tone">{{ statusOf(order).text }}</text>
        </view>
        <view class="order-meta">{{ orderMeta(order) }}</view>
        <view v-if="order.status === 'PENDING_PAY'" class="order-actions">
          <button class="btn ghost" @tap="cancel(order)">取消订单</button>
          <button class="btn" @tap="showOrderCode(order)">出示订单码</button>
        </view>
        <button v-else-if="order.status === 'FINISHED'" class="btn ghost reorder-btn" @tap="reorder(order)">再来一单</button>
      </view>
    </template>

    <template v-else>
      <view v-if="!shownCards.length" class="empty">暂无记录</view>
      <view v-for="card in shownCards" :key="card.id" class="card order-card">
        <view class="between">
          <text class="order-name">{{ card.tplInfo?.name || "卡券" }}</text>
          <text class="order-status" :class="tab === 'card' ? 'status-green' : 'status-blue'">
            {{ tab === "card" ? "已核销" : "兑换成功" }}
          </text>
        </view>
        <view class="order-meta">{{ cardMeta(card) }}</view>
      </view>
    </template>

    <view v-if="msg && (orders.length || cards.length)" class="err">{{ msg }}</view>

    <view v-if="codeOrder" class="code-mask" @tap="closeOrderCode">
      <view class="code-sheet" @tap.stop>
        <view class="code-title">到吧台出示此单号</view>
        <view class="qr-box">
          <view v-for="cell in qrCells(codeOrder.no)" :key="cell.index" class="qr-cell" :class="{ on: cell.on }"></view>
        </view>
        <view class="code-no">{{ codeOrder.no }}</view>
        <view class="code-tip">应付 ¥{{ codeOrder.total }} · 生成后 30 分钟内有效</view>
        <button class="btn ghost code-close" @tap="closeOrderCode">关闭</button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.orders-page { padding-top: 13px; }
.order-notice {
  position: fixed;
  z-index: 100;
  top: 22vh;
  left: 50%;
  max-width: calc(100vw - 56px);
  padding: 10px 18px;
  border-radius: 99px;
  transform: translateX(-50%);
  background: rgba(28, 27, 25, .92);
  color: #fff;
  font-size: 14px;
  line-height: 1.35;
  text-align: center;
  box-shadow: 0 8px 20px rgba(28, 27, 25, .18);
}
.order-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.order-tab {
  margin: 0;
  padding: 8px 14px;
  border: 1px solid rgba(28, 27, 25, .14);
  border-radius: 99px;
  background: #fff;
  color: #6b6a65;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.2;
}
.order-tab.on { border-color: #1c1b19; background: #1c1b19; color: #fff; }
.order-card { margin-bottom: 12px; padding: 15px 14px 13px; }
.order-name { max-width: 68%; font-size: 15px; font-weight: 600; line-height: 1.4; }
.order-status { flex: none; margin-left: 10px; font-size: 13px; }
.status-gold { padding: 3px 10px; border-radius: 99px; background: #faeeda; color: #ba7517; }
.status-blue { padding: 3px 10px; border-radius: 99px; background: #e6f1fb; color: #185fa5; }
.status-green { padding: 3px 10px; border-radius: 99px; background: #edf6df; color: #3b6d11; }
.status-grey { color: #6b6a65; }
.status-red { padding: 3px 10px; border-radius: 99px; background: #fcebeb; color: #a32d2d; }
.order-meta { margin-top: 6px; color: #6b6a65; font-size: 13px; line-height: 1.55; }
.order-actions { display: flex; gap: 8px; margin-top: 12px; }
.order-actions .btn, .reorder-btn { flex: 1; margin: 0; padding: 9px 10px; font-size: 13px; }
.reorder-btn { display: block; width: 100%; margin-top: 12px; }
.empty-box { padding: 28px 14px; text-align: center; }
.code-mask { position: fixed; z-index: 110; inset: 0; display: flex; align-items: flex-end; background: rgba(0, 0, 0, .42); }
.code-sheet { width: 100%; padding: 22px 20px calc(20px + env(safe-area-inset-bottom)); border-radius: 22px 22px 0 0; background: #fff; text-align: center; animation: sheet-up .18s ease-out; }
.code-title { margin-bottom: 16px; text-align: left; font-size: 17px; font-weight: 600; }
.qr-box { display: grid; grid-template-columns: repeat(21, 1fr); width: 150px; height: 150px; margin: 0 auto; padding: 9px; border: 1px solid rgba(28, 27, 25, .14); border-radius: 12px; background: #fff; }
.qr-cell { background: transparent; }
.qr-cell.on { background: #1c1b19; }
.code-no { margin-top: 15px; font-size: 25px; font-weight: 700; letter-spacing: .5px; line-height: 1.25; }
.code-tip { margin-top: 6px; color: #9c9a93; font-size: 13px; }
.code-close { display: block; width: 100%; margin-top: 18px; padding: 11px; font-size: 15px; }
@keyframes sheet-up { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onReachBottom, onShow } from "@dcloudio/uni-app";
import { api, go, saveCart, toastText } from "@/utils/api";

const TABS = [
  { key: "coin", label: "金币订单" },
  { key: "card", label: "卡包订单" },
  { key: "point", label: "积分订单" },
  { key: "all", label: "全部变更" },
];

const PAGE_SIZE = 30;
const tab = ref("coin");
const items = ref([]);
const cacheByTab = ref({});
const pageByTab = ref({});
const loading = ref(false);
const loadingMore = ref(false);
const hasMore = computed(() => !!pageByTab.value[tab.value]?.hasMore);
const msg = ref("");
const notice = ref("");
const codeOrder = ref(null);
const cancelOrder = ref(null);
const canceling = ref(false);
let noticeTimer = null;
let loadSeq = 0;

const emptyHint = computed(() => {
  if (tab.value === "coin") return "暂无金币相关记录";
  if (tab.value === "card") return "暂无卡券相关记录";
  if (tab.value === "point") return "暂无积分相关记录";
  return "暂无变更记录";
});

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
  if (tab.value === next) return;
  tab.value = next;
  msg.value = "";
  // 先展示该 Tab 缓存，避免整页清空造成闪烁
  const cached = cacheByTab.value[next];
  items.value = Array.isArray(cached) ? cached : [];
  load({ soft: true });
}

async function load({ soft = false } = {}) {
  const kind = tab.value;
  const seq = ++loadSeq;
  const hasCache = Array.isArray(cacheByTab.value[kind]);
  // 有缓存的软刷新不打断当前列表；仅首次无数据时显示「加载中」
  if (!soft || !hasCache) loading.value = !hasCache;
  msg.value = "";
  try {
    const res = await api(`/ledger?kind=${kind}&limit=${PAGE_SIZE}`, { silent: true, loading: false });
    if (seq !== loadSeq || tab.value !== kind) return;
    const list = Array.isArray(res?.items) ? res.items : [];
    cacheByTab.value = { ...cacheByTab.value, [kind]: list };
    pageByTab.value = { ...pageByTab.value, [kind]: { cursor: res?.cursor || "", hasMore: !!res?.hasMore } };
    items.value = list;
  } catch (error) {
    if (seq !== loadSeq || tab.value !== kind) return;
    msg.value = error.message || "加载失败";
    if (!hasCache) items.value = [];
  } finally {
    if (seq === loadSeq) loading.value = false;
  }
}

function rowKey(row) {
  return `${row.kind}-${row.id}`;
}

async function loadMore() {
  const kind = tab.value;
  const page = pageByTab.value[kind];
  if (!page?.hasMore || loadingMore.value || loading.value) return;
  const seq = loadSeq;
  loadingMore.value = true;
  try {
    const before = encodeURIComponent(page.cursor || "");
    const res = await api(`/ledger?kind=${kind}&limit=${PAGE_SIZE}&before=${before}`, { silent: true, loading: false });
    if (seq !== loadSeq || tab.value !== kind) return;
    const seen = new Set(items.value.map(rowKey));
    const more = (Array.isArray(res?.items) ? res.items : []).filter((row) => !seen.has(rowKey(row)));
    const list = [...items.value, ...more];
    cacheByTab.value = { ...cacheByTab.value, [kind]: list };
    pageByTab.value = { ...pageByTab.value, [kind]: { cursor: res?.cursor || page.cursor, hasMore: !!res?.hasMore } };
    items.value = list;
  } catch (error) {
    if (seq === loadSeq && tab.value === kind) toastText(error.message || "加载失败");
  } finally {
    loadingMore.value = false;
  }
}
onShow(() => load({ soft: true }));
onReachBottom(() => loadMore());
onLoad((options) => {
  if (TABS.some((item) => item.key === options?.tab)) tab.value = options.tab;
  if (options?.notice) showNotice(decodeURIComponent(options.notice));
});

function cancel(order) {
  cancelOrder.value = order;
  msg.value = "";
}
function closeCancelDlg() {
  if (canceling.value) return;
  cancelOrder.value = null;
}
async function confirmCancel() {
  if (!cancelOrder.value || canceling.value) return;
  canceling.value = true;
  msg.value = "";
  try {
    await api(`/orders/${cancelOrder.value.id}/cancel`, { method: "POST", loading: false });
    cancelOrder.value = null;
    showNotice("订单已取消");
    // 取消后清掉相关缓存，强制刷新
    cacheByTab.value = {};
    await load();
  } catch (error) {
    msg.value = error.message || "取消失败";
  } finally {
    canceling.value = false;
  }
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
    toastText("订单商品已失效");
    return;
  }
  saveCart(lines);
  uni.showToast({ title: "已加入购物车", icon: "success" });
  go("/pages/c/order");
}
</script>

<template>
  <page-meta :page-style="`overflow:${codeOrder || cancelOrder ? 'hidden' : 'visible'}`" />
  <view class="pbody orders-page">
    <view v-if="notice" class="order-notice">{{ notice }}</view>
    <view class="order-tabs">
      <view
        v-for="item in TABS"
        :key="item.key"
        class="order-tab"
        :class="{ on: tab === item.key }"
        @tap="switchTab(item.key)"
      >{{ item.label }}</view>
    </view>

    <view class="order-hint">{{ tab === 'point' ? '积分变更明细：备注、数量、时间、余额变化与操作员' : tab === 'coin' ? '金币变更明细：备注、数量、时间、余额变化与操作员' : tab === 'card' ? '卡券变更明细：新增、核销与作废，含卡券号与操作员' : '以下为资产变更明细，含下单、充值、提分、兑换、签到、对局与店员调整' }}</view>

    <view v-if="loading && !items.length" class="empty">加载中…</view>
    <view v-else-if="msg && !items.length" class="card empty-box">
      <view class="err">{{ msg }}</view>
      <button class="btn ghost" @tap="load">重新加载</button>
    </view>
    <view v-else-if="!items.length" class="empty">{{ emptyHint }}</view>

    <view v-for="row in items" :key="tab + '-' + rowKey(row)" class="card order-card">
      <view class="between">
        <text class="order-name">{{ row.title }}</text>
        <text class="order-status" :class="'status-' + (row.statusTone || 'grey')">{{ row.status }}</text>
      </view>

      <!-- 卡包订单：每条是一次卡券变更（新增 / 核销 / 作废） -->
      <view v-if="row.kind === 'card'" class="point-grid">
        <view class="point-row">
          <text class="point-k">备注</text>
          <text class="point-v">{{ row.content || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">数量</text>
          <text
            class="point-v order-amt"
            :class="{ plus: String(row.amount).startsWith('+'), minus: String(row.amount).startsWith('−') }"
          >{{ row.amount || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">时间</text>
          <text class="point-v">{{ row.at || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">卡券号</text>
          <text class="point-v">{{ row.cardNo || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">操作员</text>
          <text class="point-v">{{ row.operator || '—' }}</text>
        </view>
      </view>

      <!-- 金币/积分订单统一：显示内容 / 加减数量 / 时间 / 变更过程 / 操作员 -->
      <view v-else-if="row.kind === 'point' || row.kind === 'coin'" class="point-grid">
        <view class="point-row">
          <text class="point-k">备注</text>
          <text class="point-v">{{ row.content || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">数量</text>
          <text
            class="point-v order-amt"
            :class="{ plus: String(row.amount).startsWith('+'), minus: String(row.amount).startsWith('−') || String(row.amount).startsWith('-'), void: row.struck !== undefined ? row.struck : ['已作废', '已驳回', '已取消', '已关闭', '超时关闭', '已拒绝'].includes(row.status) }"
          >{{ row.amount || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">时间</text>
          <text class="point-v">{{ row.at || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">余额</text>
          <text class="point-v">{{ row.process || '—' }}</text>
        </view>
        <view class="point-row">
          <text class="point-k">操作员</text>
          <text class="point-v">{{ row.operator || '—' }}</text>
        </view>
      </view>

      <view v-else class="order-meta">
        <text v-if="row.amount" class="order-amt" :class="{ plus: String(row.amount).startsWith('+'), minus: String(row.amount).startsWith('−') || String(row.amount).startsWith('-') }">{{ row.amount }}</text>
        <text>{{ row.meta }}</text>
      </view>
      <view v-if="row.type === 'order' && row.order?.status === 'PENDING_PAY'" class="order-actions">
        <button class="btn ghost" @tap="cancel(row.order)">取消订单</button>
        <button class="btn" @tap="showOrderCode(row.order)">出示订单码</button>
      </view>
      <button
        v-else-if="row.type === 'order' && row.order?.status === 'FINISHED'"
        class="btn ghost reorder-btn"
        @tap="reorder(row.order)"
      >再来一单</button>
    </view>

    <view v-if="msg && items.length" class="err">{{ msg }}</view>
    <view v-if="items.length" class="list-foot" @tap="loadMore">
      {{ loadingMore ? "加载中…" : hasMore ? "上拉或点此加载更早记录" : `已显示全部 ${items.length} 条` }}
    </view>

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

    <view v-if="cancelOrder" class="confirm-mask" @tap="closeCancelDlg" @touchmove.stop.prevent>
      <view class="confirm-dialog" @tap.stop>
        <view class="confirm-title">取消订单</view>
        <view class="confirm-body">确认取消订单 {{ cancelOrder.no }}？</view>
        <view v-if="msg" class="err">{{ msg }}</view>
        <view class="confirm-actions">
          <button class="btn ghost confirm-btn" @tap="closeCancelDlg">再想想</button>
          <button class="btn confirm-btn confirm-danger" :disabled="canceling" @tap="confirmCancel">
            {{ canceling ? "取消中…" : "确认取消" }}
          </button>
        </view>
      </view>
    </view>
    <app-toast />
  </view>
</template>

<style scoped>
.orders-page { padding-top: 13px; }
.list-foot { padding: 14px 0 22px; text-align: center; color: #9c9a93; font-size: 12px; }
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-shadow: 0 8px 20px rgba(28, 27, 25, .18);
}
.order-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
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
.order-hint {
  margin: 0 0 12px;
  color: #9c9a93;
  font-size: 12px;
  line-height: 1.5;
}
.order-card { margin-bottom: 12px; padding: 15px 14px 13px; }
.order-name { max-width: 68%; font-size: 15px; font-weight: 600; line-height: 1.4; }
.order-status { flex: none; margin-left: 10px; font-size: 13px; }
.status-gold { padding: 3px 10px; border-radius: 99px; background: #faeeda; color: #ba7517; }
.status-blue { padding: 3px 10px; border-radius: 99px; background: #e6f1fb; color: #185fa5; }
.status-green { padding: 3px 10px; border-radius: 99px; background: #edf6df; color: #3b6d11; }
.status-grey { color: #6b6a65; }
.status-red { padding: 3px 10px; border-radius: 99px; background: #fcebeb; color: #a32d2d; }
.order-meta { margin-top: 6px; color: #6b6a65; font-size: 13px; line-height: 1.55; }
.order-amt { margin-right: 8px; font-weight: 600; color: #1c1b19; }
.order-amt.plus { color: #3b6d11; }
.order-amt.minus { color: #a32d2d; }
.order-amt.void { color: #9c9a93; text-decoration: line-through; }
.point-grid { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.point-row { display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.45; }
.point-k { flex: none; width: 48px; color: #9c9a93; }
.point-v { flex: 1; min-width: 0; color: #6b6a65; word-break: break-all; }
.point-v.order-amt { margin-right: 0; font-size: 15px; }
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
.confirm-mask {
  position: fixed;
  z-index: 110;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 30px;
  background: rgba(0, 0, 0, 0.35);
}
.confirm-dialog {
  width: 84%;
  max-width: 320px;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
}
.confirm-title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1b19;
  margin-bottom: 9px;
}
.confirm-body {
  font-size: 12.5px;
  color: #6b6a65;
  line-height: 1.7;
  margin-bottom: 13px;
}
.confirm-actions {
  display: flex;
  gap: 8px;
}
.confirm-btn {
  flex: 1;
  margin: 0;
}
.confirm-actions .btn + .btn {
  margin-left: 0;
}
.confirm-danger {
  border-color: #b52d2d;
  background: #b52d2d;
  color: #fff;
}
@keyframes sheet-up { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go } from "@/utils/api";

const GROUPS = [
  { cat: "GAME", title: "游戏卡", sub: "兑换后 30 天有效" },
  { cat: "FOOD", title: "酒水小食卡", sub: "兑换后 30 天有效" },
];

const data = ref(null);
const cards = ref([]);
const dlg = ref(null);
const qty = ref(1);
const msg = ref("");
const notice = ref("");
let noticeTimer = null;

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const av = computed(() => data.value?.point?.av || 0);

function tplsOf(cat) {
  return (data.value?.tpls || []).filter((t) => t.cat === cat);
}

function gotCount(tid) {
  return cards.value.filter((c) => c.tpl === tid && c.src === "EXCHANGE").length;
}

function tipOf(t) {
  const stk = t.stock == null ? -1 : Number(t.stock);
  const per = t.perLimit == null ? -1 : Number(t.perLimit);
  const got = gotCount(t.id);
  if (stk >= 0 && stk <= 0) return { text: "已兑完", bad: true };
  if (per >= 0 && got >= per) return { text: "已达每人上限", bad: true };
  if (stk >= 0) return { text: "仅剩 " + stk + " 张", bad: false };
  return null;
}

function disabled(t) {
  const tip = tipOf(t);
  return av.value < t.cost || (tip && tip.bad);
}

const maxQty = computed(() => {
  if (!dlg.value) return 1;
  const byPoints = Math.floor(Math.max(0, av.value) / Math.max(1, dlg.value.cost));
  const stock = dlg.value.stock == null || Number(dlg.value.stock) < 0 ? Infinity : Number(dlg.value.stock);
  const per = dlg.value.perLimit == null || Number(dlg.value.perLimit) < 0
    ? Infinity
    : Math.max(0, Number(dlg.value.perLimit) - gotCount(dlg.value.id));
  return Math.max(0, Math.min(byPoints, stock, per));
});

function openDlg(t) {
  dlg.value = t;
  qty.value = 1;
  msg.value = "";
}

function showNotice(text) {
  if (noticeTimer) clearTimeout(noticeTimer);
  notice.value = text;
  noticeTimer = setTimeout(() => { notice.value = ""; }, 2200);
}

function tryOpenDlg(t) {
  const tip = tipOf(t);
  if (av.value < t.cost) {
    showNotice("积分不足");
    return;
  }
  if (tip?.bad) {
    showNotice(tip.text);
    return;
  }
  openDlg(t);
}

function closeDlg() {
  dlg.value = null;
}

async function load() {
  const [pt, cs] = await Promise.all([api("/points"), api("/cards")]);
  data.value = pt;
  cards.value = cs;
}

async function confirm() {
  if (!dlg.value) return;
  if (qty.value > maxQty.value) {
    showNotice(av.value < dlg.value.cost * qty.value ? "积分不足" : "兑换数量不可用");
    return;
  }
  msg.value = "";
  try {
    await api("/exchange", { method: "POST", body: { tplId: dlg.value.id, qty: qty.value } });
    closeDlg();
    await load();
    showNotice("兑换成功");
    setTimeout(() => go("/pages/c/cards"), 1200);
  } catch (e) {
    showNotice(e.message || "兑换失败");
  }
}

onShow(load);
</script>

<template>
  <view class="pbody" v-if="data">
    <view v-if="notice" class="exchange-notice">{{ notice }}</view>
    <view v-for="g in GROUPS" :key="g.cat">
      <view class="st exchange-head"><text class="exchange-title">{{ g.title }}</text><text class="st-sub">{{ g.sub }}</text></view>
      <view class="card" v-if="tplsOf(g.cat).length">
        <view class="li exch-li" v-for="t in tplsOf(g.cat)" :key="t.id">
          <view class="ph-lg">卡</view>
          <view class="gr">
            <view style="font-weight:600">{{ t.name }}</view>
            <view class="tiny">{{ t.desc }}{{ t.use ? " · " + t.use : "" }}</view>
            <view v-if="tipOf(t)" class="tiny tip" :class="{ bad: tipOf(t).bad }">{{ tipOf(t).text }}</view>
          </view>
          <view class="exch-act">
            <view style="font-weight:600;color:#185FA5">{{ fmt(t.cost) }}</view>
            <button class="btn sm" :style="{ opacity: disabled(t) ? .45 : 1 }" @tap="tryOpenDlg(t)">兑换</button>
          </view>
        </view>
      </view>
    </view>
    <view class="note">宝箱卡属「其他卡」，不出现在兑换页。兑换 N 张时积分扣减 = N × 单价，不足则整单失败。</view>
    <view class="err" v-if="msg">{{ msg }}</view>

    <view v-if="dlg" class="mask" @tap="closeDlg">
      <view class="exchange-dialog" @tap.stop>
        <view class="exchange-dialog-title">兑换 {{ dlg.name }}</view>
        <view class="qty-row">
          <button class="btn ghost" @tap="qty = Math.max(1, qty - 1)">−</button>
          <text class="qty-num">{{ qty }}</text>
          <button class="btn ghost" :disabled="qty >= maxQty" @tap="qty = Math.min(maxQty, qty + 1)">+</button>
        </view>
        <view class="exchange-cost">
          需积分 <text style="font-weight:600;color:#185FA5">{{ fmt(dlg.cost * qty) }}</text>
          · 可用 {{ fmt(av) }}
        </view>
        <view class="exchange-actions">
          <button class="btn ghost" @tap="closeDlg">取消</button>
          <button class="btn" :disabled="qty > maxQty" @tap="confirm">确认兑换</button>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.st { font-size: 13px; margin: 4px 0 8px; color: #1c1b19; }
.exchange-head { display: flex; align-items: center; justify-content: space-between; }
.exchange-title { font-weight: 700; }
.st-sub { font-weight: 400; color: #9c9a93; font-size: 11px; text-align: right; }
.exch-li { align-items: flex-start; }
.ph-lg {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #edede8;
  color: #6b6a65;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
  flex-shrink: 0;
}
.tip { display: block; margin-top: 2px; color: #ba7517; }
.tip.bad { color: #e24b4a; }
.exch-act { text-align: right; flex-shrink: 0; }
.btn.sm {
  margin-top: 4px;
  font-size: 12px;
  padding: 6px 12px;
  background: #1c1b19;
  color: #fff;
  border-radius: 8px;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22px;
}
.exchange-dialog {
  width: 100%;
  max-width: 320px;
  background: #fff;
  border-radius: 18px;
  padding: 20px 16px 16px;
  animation: dialog-in .16s ease-out;
}
.exchange-dialog-title { margin-bottom: 16px; font-size: 16px; font-weight: 700; }
.qty-row { display: flex; align-items: center; justify-content: center; gap: 14px; }
.qty-row .btn { width: 40px; height: 40px; padding: 0 0 2px; border-radius: 10px; font-size: 18px; line-height: 1; display: flex; align-items: center; justify-content: center; }
.qty-num { font-size: 20px; font-weight: 600; min-width: 40px; text-align: center; }
.exchange-cost { margin-top: 12px; text-align: center; color: #9c9a93; font-size: 13px; }
.exchange-actions { display: flex; gap: 8px; margin-top: 18px; }
.exchange-actions .btn { flex: 1; margin: 0; padding: 11px 8px; font-size: 14px; }
@keyframes dialog-in { from { transform: scale(.96); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.exchange-notice {
  position: fixed;
  z-index: 120;
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
</style>

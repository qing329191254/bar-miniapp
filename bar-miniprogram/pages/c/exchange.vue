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

function fmt(n) {
  return Number(n || 0).toLocaleString("zh-CN");
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

function closeDlg() {
  dlg.value = null;
}

async function load() {
  const [pt, cs] = await Promise.all([api("/points"), api("/cards")]);
  data.value = pt;
  cards.value = cs;
}

async function confirm() {
  if (!dlg.value || qty.value > maxQty.value) return;
  msg.value = "";
  try {
    await api("/exchange", { method: "POST", body: { tplId: dlg.value.id, qty: qty.value } });
    uni.showToast({ title: "兑换成功", icon: "success" });
    closeDlg();
    await load();
    setTimeout(() => go("/pages/c/cards"), 400);
  } catch (e) {
    msg.value = e.message;
  }
}

onShow(load);
</script>

<template>
  <view class="pbody" v-if="data">
    <view v-for="g in GROUPS" :key="g.cat">
      <view class="st">{{ g.title }} <text class="st-sub">{{ g.sub }}</text></view>
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
            <button class="btn sm" :disabled="disabled(t)" @tap="openDlg(t)">兑换</button>
          </view>
        </view>
      </view>
    </view>
    <view class="note">宝箱卡属「其他卡」，不出现在兑换页。兑换 N 张时积分扣减 = N × 单价，不足则整单失败。</view>
    <view class="err" v-if="msg">{{ msg }}</view>

    <view v-if="dlg" class="mask" @tap="closeDlg">
      <view class="sheet" @tap.stop>
        <view style="font-weight:600;text-align:center;margin-bottom:12px">兑换 {{ dlg.name }}</view>
        <view class="qty-row">
          <button class="btn ghost" @tap="qty = Math.max(1, qty - 1)">−</button>
          <text class="qty-num">{{ qty }}</text>
          <button class="btn ghost" :disabled="qty >= maxQty" @tap="qty = Math.min(maxQty, qty + 1)">+</button>
        </view>
        <view class="tiny" style="text-align:center;margin-top:9px">
          需积分 <text style="font-weight:600;color:#185FA5">{{ fmt(dlg.cost * qty) }}</text>
          · 可用 {{ fmt(av) }}
        </view>
        <button class="btn block gold" style="margin-top:14px" :disabled="qty > maxQty" @tap="confirm">确认兑换</button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.st { font-size: 13px; font-weight: 600; margin: 4px 0 8px; color: #1c1b19; }
.st-sub { font-weight: 400; color: #9c9a93; font-size: 11px; margin-left: 6px; }
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
.btn.sm[disabled] { opacity: 0.45; }
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 100;
  display: flex;
  align-items: flex-end;
}
.sheet {
  width: 100%;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 18px 16px 28px;
}
.qty-row { display: flex; align-items: center; justify-content: center; gap: 14px; }
.qty-num { font-size: 20px; font-weight: 600; min-width: 32px; text-align: center; }
</style>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go } from "@/utils/api";

const TABS = [
  { k: "GAME", n: "游戏卡", color: "#534AB7" },
  { k: "FOOD", n: "酒水小食", color: "#1D9E75" },
  { k: "OTHER", n: "其他", color: "#993556" },
  { k: "VOID", n: "已失效", color: "#9C9A93" },
];
const VOID_ST = ["USED", "EXPIRED", "VOID"];

const list = ref([]);
const tab = ref("GAME");
const sel = ref([]);
const msg = ref("");

onShow(async () => {
  list.value = await api("/cards");
});

function catOf(c) {
  return c.tplInfo?.cat || "OTHER";
}
function count(k) {
  if (k === "VOID") return list.value.filter((c) => VOID_ST.includes(c.status)).length;
  return list.value.filter((c) => c.status === "UNUSED" && catOf(c) === k).length;
}
const shown = computed(() => {
  if (tab.value === "VOID") return list.value.filter((c) => VOID_ST.includes(c.status));
  return list.value.filter((c) => c.status === "UNUSED" && catOf(c) === tab.value);
});
const voidable = computed(() => tab.value !== "VOID");
function selected(id) {
  return sel.value.includes(id);
}
function switchTab(k) {
  tab.value = k;
  sel.value = [];
}
function toggle(c) {
  if (!voidable.value || c.status !== "UNUSED") return;
  sel.value = selected(c.id) ? sel.value.filter((x) => x !== c.id) : [...sel.value, c.id];
}
function accent(c) {
  return (TABS.find((t) => t.k === catOf(c)) || TABS[2]).color;
}

async function gen() {
  if (!sel.value.length) return;
  msg.value = "";
  try {
    const result = await api("/cards/verify-code", { method: "POST", body: { cardIds: sel.value } });
    sel.value = [];
    uni.navigateTo({ url: `/pages/c/verify-code?code=${encodeURIComponent(result.code)}` });
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pack">
    <view class="tabs">
      <view
        v-for="t in TABS"
        :key="t.k"
        class="chip"
        :class="{ on: tab === t.k }"
        @tap="switchTab(t.k)"
      >
        {{ t.n }} {{ count(t.k) }}
        <view v-if="t.k === 'OTHER' && count('OTHER')" class="dot"></view>
      </view>
    </view>

    <view v-if="!shown.length" class="card empty-box">
      <view style="font-weight:600">{{ tab === "VOID" ? "暂无历史记录" : "暂无可用卡券" }}</view>
      <view class="tiny" style="margin-top:4px">{{ tab === "VOID" ? "" : "去兑换看看" }}</view>
      <button v-if="tab !== 'VOID'" class="btn ghost" style="margin-top:12px" @tap="go('/pages/c/exchange')">去兑换</button>
    </view>

    <view
      v-for="c in shown"
      :key="c.id"
      class="card pack-card"
      :class="{ on: selected(c.id) }"
      :style="{ borderLeftColor: accent(c) }"
      @tap="toggle(c)"
    >
      <view class="pack-row">
        <view class="gr">
          <view class="pack-name">{{ c.tplInfo?.name }}</view>
          <view class="tiny" style="margin-top:2px">{{ c.srcDesc }}</view>
          <view class="tiny" style="margin-top:2px" :style="c.daysLeft <= 3 && c.status === 'UNUSED' ? 'color:#A32D2D;font-weight:600' : ''">
            {{ c.expire ? c.expire + " 到期" : "兑换后 " + (c.tplInfo?.days || 30) + " 天有效" }}
            · 剩 {{ c.daysLeft }} 天
            <text v-if="c.daysLeft <= 3 && c.status === 'UNUSED'"> · 临期请尽快使用</text>
          </view>
          <view v-if="c.tplInfo?.use" class="tiny gold" style="margin-top:2px">{{ c.tplInfo.use }}</view>
        </view>
        <view v-if="voidable" class="pick">
          <view class="box" :class="{ on: selected(c.id) }">{{ selected(c.id) ? "✓" : "" }}</view>
          <view class="tiny">{{ selected(c.id) ? "已选" : "选择" }}</view>
        </view>
        <text v-else class="pill">{{ c.status === "USED" ? "已核销" : c.status === "VOID" ? "已作废" : "已过期" }}</text>
      </view>
    </view>
    <view style="height:72px"></view>

    <view v-if="voidable" class="pack-bar">
      <button class="btn block gold" :disabled="!sel.length" @tap="gen">生成核销码（{{ sel.length }} 张）</button>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

<style scoped>
.pack { padding: 13px 15px 20px; }
.tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.chip { position: relative; }
.dot {
  position: absolute;
  top: -2px; right: -2px;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #E24B4A;
}
.empty-box { text-align: center; padding: 34px 14px; }
.pack-card {
  border-left: 3px solid #534AB7;
  padding: 12px 12px 12px 14px;
}
.pack-card.on { background: #E6F1FB; border-color: #185FA5; }
.pack-row { display: flex; align-items: flex-start; gap: 10px; }
.pack-name { font-size: 14px; font-weight: 600; }
.pick { margin-left: auto; text-align: center; flex: none; }
.box {
  width: 17px; height: 17px; border-radius: 4px;
  border: 1px solid rgba(28,27,25,.24);
  margin: 0 auto 3px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; color: #fff;
}
.box.on { background: #1C1B19; border-color: #1C1B19; }
.pack-bar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  padding: 11px 16px;
  padding-bottom: calc(11px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid rgba(28,27,25,.12);
  z-index: 5;
}
.pack-bar .btn[disabled] { background: #EDEBE4; color: #9C9A93; }
</style>

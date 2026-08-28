<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const data = ref(null);
const selId = ref(null);
const msg = ref("");
const creating = ref(false);
const showTierDialog = ref(false);

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const coin = computed(() => data.value?.coin || { p: 0, b: 0 });
const coinTotal = computed(() => (coin.value.p || 0) + (coin.value.b || 0));
const tiers = computed(() => data.value?.tiers || []);
const pending = computed(() => data.value?.pending);
const singleLimit = computed(() => Number(data.value?.singleLimit || 0));

const selected = computed(() => tiers.value.find((t) => t.id === selId.value) || null);

async function load() {
  data.value = await api("/recharges");
  if (!selId.value && data.value?.tiers?.length) {
    const rec = data.value.tiers.find((t) => t.rec);
    selId.value = rec ? rec.id : data.value.tiers[0].id;
  }
}
onShow(load);

function pick(id) {
  selId.value = id;
  msg.value = "";
}

function openTierDialog() {
  if (pending.value) {
    goRechargeDetail();
    return;
  }
  showTierDialog.value = true;
}

function goRechargeDetail() {
  uni.navigateTo({ url: "/pages/c/recharge-detail" });
}

function closeTierDialog() {
  if (!creating.value) showTierDialog.value = false;
}

async function create() {
  if (!selected.value || creating.value) return;
  if (pending.value) {
    goRechargeDetail();
    return;
  }
  creating.value = true;
  msg.value = "";
  try {
    const order = await api("/recharges", { method: "POST", body: { tierId: selected.value.id } });
    showTierDialog.value = false;
    uni.navigateTo({ url: "/pages/c/recharge-detail?created=" + encodeURIComponent(order.no || "") });
  } catch (e) {
    msg.value = e.message;
  } finally {
    creating.value = false;
  }
}

</script>

<template>
  <view class="rc-page" v-if="data">
    <view class="card coin-card">
      <view class="tiny gold-t">当前金币</view>
      <view class="coin-num">{{ fmt(coinTotal) }}</view>
      <view class="coin-row">
        <text class="tiny gold-t">本金 {{ fmt(coin.p) }}</text>
        <text class="tiny gold-t">赠送 {{ fmt(coin.b) }}</text>
        <text class="pill warn-pill">赠送金币不可退</text>
      </view>
    </view>

    <view class="st-row">
      <text class="st">充值档位</text>
      <text class="st-sub">1 元 = 1 金币 · 单笔上限 {{ fmt(singleLimit) }}</text>
    </view>

    <view class="tier-grid">
      <view
        v-for="t in tiers"
        :key="t.id"
        class="card tier"
        :class="{ on: selId === t.id, rec: t.rec }"
        @tap="pick(t.id)"
      >
        <view class="tier-amt">{{ fmt(t.amount) }}</view>
        <view class="tiny tier-sub" :class="{ gift: t.bonus > 0 }">
          {{ t.bonus > 0 ? "赠 " + fmt(t.bonus) + (t.rec ? " · 最划算" : "") : "无赠送" }}
        </view>
      </view>
    </view>

    <view class="card rules">
      <view style="font-weight:600;margin-bottom:6px">充值规则</view>
      <view class="rules-t">
        · 本金金币与赠送金币分账记录
        <br />· 消费时<text style="font-weight:600">优先扣减本金金币</text>，赠送金币后扣
        <br />· <text class="red-t" style="font-weight:600">赠送金币不可退款、不可提现、不可转让</text>
        <br />· 本金金币未消费部分可申请退回（到店办理）
      </view>
    </view>

    <view class="rc-bar">
      <button
        v-if="pending"
        class="btn block"
        @tap="goRechargeDetail"
      >查看待付单（{{ pending.no.slice(-4) }}）</button>
      <button
        v-else
        class="btn block"
        :disabled="!selected || creating"
        @tap="openTierDialog"
      >生成充值单</button>
      <view class="tiny rc-tip">
        {{ pending ? "你有一张待付充值单，请先付款或取消" : "生成后请到吧台向店员出示单号" }}
      </view>
    </view>

    <view class="err" v-if="msg">{{ msg }}</view>
    <view style="height:88px"></view>

    <view v-if="showTierDialog" class="tier-mask" @tap="closeTierDialog" @touchmove.stop.prevent></view>
    <view v-if="showTierDialog" class="tier-dialog" @touchmove.stop>
      <view class="tier-dialog-title">选择充值档位</view>
      <view class="tier-dialog-list">
        <view
          v-for="t in tiers"
          :key="t.id"
          class="tier-dialog-item"
          :class="{ on: selId === t.id }"
          @tap="pick(t.id)"
        >
          <view class="tier-dialog-copy">
            <view class="tier-dialog-amount">¥{{ fmt(t.amount) }}</view>
            <view class="tier-dialog-sub">
              到账 {{ fmt(t.amount + t.bonus) }} 金币{{ t.bonus > 0 ? "（含赠送 " + fmt(t.bonus) + "）" : "" }}
            </view>
          </view>
          <text v-if="t.rec" class="tier-best">最划算</text>
        </view>
      </view>
      <view class="tier-dialog-actions">
        <button class="btn ghost tier-dialog-btn" :disabled="creating" @tap="closeTierDialog">取消</button>
        <button class="btn tier-dialog-btn confirm" :disabled="!selected || creating" @tap="create">
          {{ creating ? "生成中…" : "生成充值单" }}
        </button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.rc-page { padding: 13px 15px 20px; }
.coin-card {
  background: #fdf4e3;
  border-color: #ba7517;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.gold-t { color: #ba7517; }
.coin-num { font-size: 32px; font-weight: 700; color: #633806; margin-top: 2px; }
.coin-row { display: flex; align-items: center; gap: 10px; margin-top: 5px; flex-wrap: wrap; }
.warn-pill { background: #fff; color: #e24b4a; margin-left: auto; }
.st-row { display: flex; align-items: baseline; gap: 8px; margin: 4px 0 8px; }
.st { font-size: 13px; font-weight: 600; }
.st-sub { font-size: 11px; color: #9c9a93; margin-left: auto; }
.tier-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.tier {
  width: calc(50% - 5px);
  box-sizing: border-box;
  text-align: center;
  padding: 15px 8px;
  margin-bottom: 0;
  cursor: pointer;
}
.tier.on { border: 2px solid #ba7517; background: #fdf4e3; }
.tier.rec.on .tier-amt { color: #633806; }
.tier-amt { font-size: 19px; font-weight: 700; }
.tier-sub { color: #9c9a93; margin-top: 2px; }
.tier-sub.gift { color: #3b6d11; }
.rules { background: #f5f4f0; padding: 12px 14px; margin-bottom: 12px; }
.rules-t { font-size: 11px; color: #6b6a65; line-height: 1.75; }
.rc-bar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  padding: 11px 16px 20px;
  background: #f5f4f0;
  border-top: 1px solid rgba(28, 27, 25, 0.12);
  z-index: 5;
}
.rc-tip { text-align: center; margin-top: 7px; color: #9c9a93; }
.tier-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(28,27,25,.38);
}
.tier-dialog {
  position: fixed;
  left: 28px;
  right: 28px;
  top: 50%;
  z-index: 21;
  transform: translateY(-50%);
  padding: 20px 16px 16px;
  border-radius: 16px;
  background: #fff;
  box-sizing: border-box;
  box-shadow: 0 16px 40px rgba(28,27,25,.2);
}
.tier-dialog-title { font-size: 17px; font-weight: 700; margin-bottom: 13px; }
.tier-dialog-list { display: flex; flex-direction: column; gap: 7px; }
.tier-dialog-item {
  min-height: 64px;
  padding: 10px 12px;
  border: 1px solid rgba(28,27,25,.13);
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-sizing: border-box;
  background: #fff;
}
.tier-dialog-item.on { border-color: #ba7517; background: #fdf4e3; }
.tier-dialog-copy { flex: 1; min-width: 0; }
.tier-dialog-amount { font-size: 16px; color: #6b6a65; }
.tier-dialog-sub { margin-top: 3px; font-size: 12px; color: #6b6a65; }
.tier-best { padding: 5px 10px; border-radius: 16px; background: #c2770b; color: #fff; font-size: 11px; flex: none; }
.tier-dialog-actions { display: flex; gap: 8px; margin-top: 16px; }
.tier-dialog-btn { flex: 1; margin: 0; }
.tier-dialog-btn.confirm { flex: 1.5; }
</style>

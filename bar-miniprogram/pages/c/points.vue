<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, isLoggedIn } from "@/utils/api";

const guest = !isLoggedIn();

const data = ref(null);

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const negative = computed(() => (data.value?.point?.av || 0) < 0);
const av = computed(() => data.value?.point?.av || 0);
const clearLabel = computed(() => data.value?.clearLabel || "每月 1 日 13:00 清零");

async function load() {
  data.value = await api("/points");
}
onShow(() => {
  if (guest) return;
  load();
});
</script>

<template>
  <guest-gate v-if="guest" text="登录后查看我的积分" />
  <view class="pbody" v-if="data">
    <view class="pt-card">
      <view class="tiny pt-label">可用积分</view>
      <view class="pt-num number-display" :class="{ neg: negative }">{{ negative ? "−" + fmt(-av) : fmt(av) }}</view>
      <view v-if="negative" class="row" style="margin-top:5px">
        <text class="pill pt-pill-warn">余额为负 · 待抵扣 {{ fmt(data.point.pd || -av) }} 分，后续获得将优先冲抵</text>
      </view>
      <view v-if="data.point.fz > 0" class="row" style="margin-top:5px">
        <text class="pill pt-pill-gold">冻结中 {{ fmt(data.point.fz) }} 分 · 使用单待店员确认</text>
      </view>
      <view class="row pt-foot">
        <text class="pill pt-pill-warn">{{ clearLabel }}</text>
        <text class="tiny pt-month">本月已获 {{ fmt(data.point.mg) }}</text>
      </view>
    </view>

    <view class="card menu">
      <view class="li menu-li" @tap="go('/pages/c/exchange')">
        <view class="ph">兑</view>
        <view class="gr">
          <view style="font-weight:600">积分兑换</view>
          <view class="tiny">兑换游戏卡、酒水小食卡，即时到卡包</view>
        </view>
        <text class="mut">›</text>
      </view>
      <view class="li menu-li" style="border-bottom:none" @tap="go('/pages/c/withdraw')">
        <view class="ph">店</view>
        <view class="gr">
          <view style="font-weight:600">积分到店使用</view>
          <view class="tiny">生成使用单，到吧台由店员当面确认</view>
        </view>
        <text v-if="data.pending" class="pill pill-gold">待确认</text>
        <text v-else class="mut">›</text>
      </view>
    </view>

    <view v-if="data.point.wd > 0" class="card wd-total">
      <view class="between">
        <text class="tiny">累计到店使用</text>
        <text style="font-weight:600;color:#185FA5">{{ fmt(data.point.wd) }} 分</text>
      </view>
    </view>

    <view class="note">兑换即时生效；到店使用需店员当面确认，确认前积分处于冻结状态，不可再用于兑换。积分仅限本店会员权益使用，不可兑换现金、不可转让。</view>
  </view>
</template>

<style scoped>
.pt-card {
  background: linear-gradient(135deg, #185FA5, #2E7CC4);
  border: none;
  color: #fff;
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(24, 95, 165, 0.22);
}
.pt-label { color: rgba(255, 255, 255, 0.8); }
.pt-num { font-size: 32px; margin-top: 2px; }
.pt-num.neg { color: #ffc9c9; }
.pt-pill-warn { background: rgba(255, 255, 255, 0.18); color: #ffd9d9; }
.pt-pill-gold { background: rgba(255, 255, 255, 0.18); color: #ffe9b8; }
.pt-foot { margin-top: 8px; justify-content: space-between; }
.pt-month { margin-left: auto; color: rgba(255, 255, 255, 0.8); }
.menu { padding: 11px 12px; }
.menu-li { cursor: pointer; padding: 11px 0; }
.ph {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #edede8;
  color: #6b6a65;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
}
.mut { color: #9c9a93; font-size: 17px; }
.pill-gold { background: #ba7517; color: #fff; }
.wd-total { padding: 11px 12px; }
</style>

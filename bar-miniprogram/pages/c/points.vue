<script setup>
import { computed, onMounted, ref } from "vue";
import { api, go } from "@/utils/api";

const data = ref(null);
const CLEAR_LABEL = "8 月 31 日 24:00 清零";
const DAYS_LEFT = 7;

function fmt(n) {
  return Number(n || 0).toLocaleString("zh-CN");
}

const negative = computed(() => (data.value?.point?.av || 0) < 0);
const av = computed(() => data.value?.point?.av || 0);
const exchCount = computed(() => Math.floor(Math.max(0, av.value) / 3000));
const showUrgency = computed(() => DAYS_LEFT <= 7 && !negative.value && av.value > 0);

async function load() {
  data.value = await api("/points");
}
onMounted(load);
</script>

<template>
  <view class="pbody" v-if="data">
    <view class="pt-card">
      <view class="tiny pt-label">可用积分</view>
      <view class="pt-num" :class="{ neg: negative }">{{ negative ? "−" + fmt(-av) : fmt(av) }}</view>
      <view v-if="negative" class="row" style="margin-top:5px">
        <text class="pill pt-pill-warn">余额为负 · 待抵扣 {{ fmt(data.point.pd || -av) }} 分，后续获得将优先冲抵</text>
      </view>
      <view v-if="data.point.fz > 0" class="row" style="margin-top:5px">
        <text class="pill pt-pill-gold">冻结中 {{ fmt(data.point.fz) }} 分 · 提分单待店员确认</text>
      </view>
      <view class="row pt-foot">
        <text class="pill pt-pill-warn">{{ CLEAR_LABEL }}</text>
        <text class="tiny pt-month">本月已获 {{ fmt(data.point.mg) }}</text>
      </view>
    </view>

    <view v-if="showUrgency" class="card urg">
      <view style="font-size:13px;font-weight:600;color:#E24B4A">
        还有 {{ DAYS_LEFT }} 天清零，{{ fmt(av) }} 分可兑 {{ exchCount }} 张游戏卡
      </view>
      <button class="btn urg-btn" @tap="go('/pages/c/exchange')">立即兑换</button>
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
        <view class="ph">提</view>
        <view class="gr">
          <view style="font-weight:600">积分提取</view>
          <view class="tiny">生成提分单，到吧台由店员确认后发放</view>
        </view>
        <text v-if="data.pending" class="pill pill-gold">待确认</text>
        <text v-else class="mut">›</text>
      </view>
    </view>

    <view v-if="data.point.wd > 0" class="card wd-total">
      <view class="between">
        <text class="tiny">累计已提出</text>
        <text style="font-weight:600;color:#185FA5">{{ fmt(data.point.wd) }} 分</text>
      </view>
    </view>

    <view class="note">兑换即时生效；提取需店员当面确认后才发放，确认前积分处于冻结状态，不可再用于兑换。</view>
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
.pt-num { font-size: 32px; font-weight: 700; margin-top: 2px; }
.pt-num.neg { color: #ffc9c9; }
.pt-pill-warn { background: rgba(255, 255, 255, 0.18); color: #ffd9d9; }
.pt-pill-gold { background: rgba(255, 255, 255, 0.18); color: #ffe9b8; }
.pt-foot { margin-top: 8px; justify-content: space-between; }
.pt-month { margin-left: auto; color: rgba(255, 255, 255, 0.8); }
.urg { background: #fcebeb; border-color: #e24b4a; padding: 12px 14px; }
.urg-btn {
  margin-top: 9px;
  width: 100%;
  background: #e24b4a;
  color: #fff;
  border-radius: 10px;
  font-weight: 600;
  padding: 10px 14px;
}
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

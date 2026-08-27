<script setup>
import { onMounted, ref } from "vue";
import { api } from "@/utils/api";

const data = ref(null);
const pts = ref(100);
const msg = ref("");

async function load() {
  data.value = await api("/points");
}
onMounted(load);

async function wdr() {
  try {
    await api("/withdrawals", { method: "POST", body: { pts: Number(pts.value) } });
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}
async function cancel() {
  await api("/withdrawals/cancel", { method: "POST" });
  await load();
}
async function exch(id) {
  try {
    await api("/exchange", { method: "POST", body: { tplId: id, qty: 1 } });
    msg.value = "兑换成功";
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view class="card">
      <view class="tiny">可用积分</view>
      <view style="font-size:24px;font-weight:700">{{ data.point.av }}</view>
      <view class="tiny">冻结 {{ data.point.fz }} · 本周获得 {{ data.point.wg }}</view>
    </view>
    <view class="card" v-if="data.pending">
      <view style="font-weight:600">待确认提分 {{ data.pending.pts }}</view>
      <view class="tiny">{{ data.pending.no }} · 剩余 {{ data.remain }}</view>
      <button class="btn ghost" @tap="cancel">取消并解冻</button>
    </view>
    <view class="card" v-else>
      <view style="font-weight:600">提分到店核销</view>
      <input class="field" type="number" v-model="pts" />
      <button class="btn block" @tap="wdr">提交提分单</button>
    </view>
    <view class="h2">兑换卡券</view>
    <view class="card" v-for="t in data.tpls" :key="t.id">
      <view class="between">
        <view>
          <view style="font-weight:600">{{ t.name }}</view>
          <view class="tiny">{{ t.cost }} 积分 · {{ t.days }} 天</view>
        </view>
        <button class="btn gold" @tap="exch(t.id)">兑</button>
      </view>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

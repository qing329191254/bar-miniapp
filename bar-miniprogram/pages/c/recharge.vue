<script setup>
import { onMounted, ref } from "vue";
import { api } from "@/utils/api";

const data = ref(null);
const msg = ref("");

async function load() {
  data.value = await api("/recharges");
}
onMounted(load);

async function create(id) {
  msg.value = "";
  try {
    await api("/recharges", { method: "POST", body: { tierId: id } });
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}
async function cancel() {
  if (!data.value?.pending) return;
  await api(`/recharges/${data.value.pending.id}/cancel`, { method: "POST" });
  await load();
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view class="card" v-if="data.pending" style="border-color:#BA7517;background:#FAEEDA">
      <view class="tiny gold">待付款 · {{ data.remain }}</view>
      <view style="font-weight:700">{{ data.pending.no }}</view>
      <view>¥{{ data.pending.amount }} 到账 {{ data.pending.amount + data.pending.bonus }} 金币</view>
      <view class="tiny">请到吧台出示此单，店员确认后到账。同时仅 1 张待付单。</view>
      <button class="btn ghost" style="margin-top:8px" @tap="cancel">取消</button>
    </view>
    <view class="g2">
      <view
        class="card"
        v-for="t in data.tiers"
        :key="t.id"
        :style="t.rec ? 'border:2px solid #BA7517;background:#FAEEDA' : ''"
        @tap="create(t.id)"
      >
        <view style="font-size:20px;font-weight:700">{{ t.amount }}</view>
        <view class="tiny">{{ t.bonus ? "赠 " + t.bonus : "无赠送" }}{{ t.rec ? " · 最划算" : "" }}</view>
      </view>
    </view>
    <view class="tiny">赠送金币不可退。金币支付接单时优先扣本金。</view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

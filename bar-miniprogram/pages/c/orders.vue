<script setup>
import { onMounted, ref } from "vue";
import { api } from "@/utils/api";

const list = ref([]);
const map = {
  PENDING_ACCEPT: "待接单",
  PENDING_PAY: "待付款",
  MAKING: "制作中",
  FINISHED: "已完成",
  CANCELLED: "已取消",
  CLOSED: "已关闭",
};
onMounted(async () => {
  list.value = await api("/orders");
});
</script>

<template>
  <view class="pbody">
    <view class="card" v-for="o in list" :key="o.id">
      <view class="between">
        <text style="font-weight:600">{{ o.no }}</text>
        <text class="pill">{{ map[o.status] || o.status }}</text>
      </view>
      <view class="tiny">{{ o.at }} · {{ o.payType === "COIN" ? "金币" : "到店付" }}</view>
      <view v-for="it in o.items" :key="it.pid" class="tiny">{{ it.name }} ×{{ it.qty }}</view>
      <text class="gold" style="font-weight:700">{{ o.total }} 金币</text>
    </view>
  </view>
</template>

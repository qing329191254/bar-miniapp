<script setup>
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const list = ref([]);
const loading = ref(false);
const msg = ref("");
const map = {
  PENDING_ACCEPT: "待接单",
  PENDING_PAY: "待付款",
  MAKING: "制作中",
  FINISHED: "已完成",
  CANCELLED: "已取消",
  CLOSED: "已关闭",
};
async function load() {
  loading.value = true;
  msg.value = "";
  try {
    list.value = await api("/orders", { silent: true });
  } catch (e) {
    msg.value = e.message;
  } finally {
    loading.value = false;
  }
}
onShow(load);

function cancel(o) {
  uni.showModal({
    title: "取消订单",
    content: `确认取消订单 ${o.no}？`,
    success: async ({ confirm }) => {
      if (!confirm) return;
      try {
        await api(`/orders/${o.id}/cancel`, { method: "POST" });
        uni.showToast({ title: "订单已取消", icon: "success" });
        await load();
      } catch (e) {
        msg.value = e.message;
      }
    },
  });
}
</script>

<template>
  <view class="pbody">
    <view v-if="loading && !list.length" class="empty">加载中…</view>
    <view v-else-if="msg && !list.length" class="card empty-box">
      <view class="err">{{ msg }}</view>
      <button class="btn ghost" @tap="load">重新加载</button>
    </view>
    <view v-else-if="!list.length" class="empty">暂无订单</view>
    <view class="card" v-for="o in list" :key="o.id">
      <view class="between">
        <text style="font-weight:600">{{ o.no }}</text>
        <text class="pill">{{ map[o.status] || o.status }}</text>
      </view>
      <view class="tiny">{{ o.at }} · {{ o.payType === "COIN" ? "金币" : "到店付" }}</view>
      <view v-for="(it, i) in o.items" :key="it.pid + '-' + (it.spec || '') + '-' + i" class="tiny">
        {{ it.name }}{{ it.spec ? "（" + it.spec + "）" : "" }} ×{{ it.qty }}
      </view>
      <view class="between" style="margin-top:6px">
        <text class="gold" style="font-weight:700">{{ o.total }} 金币</text>
        <button v-if="o.status === 'PENDING_PAY'" class="btn ghost cancel-btn" @tap="cancel(o)">取消订单</button>
      </view>
    </view>
    <view class="err" v-if="msg && list.length">{{ msg }}</view>
  </view>
</template>

<style scoped>
.empty-box { text-align: center; padding: 28px 14px; }
.cancel-btn { padding: 6px 10px; font-size: 12px; }
</style>

<script setup>
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const data = ref(null);
onShow(async () => {
  data.value = await api("/shards");
});
</script>

<template>
  <view class="pbody" v-if="data">
    <view class="card">
      <view class="tiny">本周碎片</view>
      <view style="font-size:24px;font-weight:700;color:#3B6D11">{{ data.shard.w }}</view>
      <view class="tiny">累计 {{ data.shard.t }} · 只用于周榜，不能兑换实物</view>
    </view>
    <view class="h2">近期对局</view>
    <view class="card" v-for="g in data.records" :key="g.id">
      <view class="between">
        <text style="font-weight:600">{{ g.pname }}</text>
        <text class="tiny">+{{ g.my?.sh }} 碎片</text>
      </view>
      <view class="tiny">{{ g.table }} · {{ g.time }}</view>
    </view>
  </view>
</template>

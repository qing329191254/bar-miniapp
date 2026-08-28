<script setup>
import { ref } from "vue";
import { api } from "@/utils/api";

const code = ref("");
const preview = ref(null);
const msg = ref("");

async function look() {
  msg.value = "";
  try {
    preview.value = await api("/staff/verify/" + code.value);
  } catch (e) {
    msg.value = e.message;
    preview.value = null;
  }
}
async function confirm() {
  try {
    await api("/staff/verify/" + (preview.value.code || code.value) + "/confirm", { method: "POST" });
    msg.value = "核销成功";
    preview.value = null;
    code.value = "";
  } catch (e) {
    msg.value = e.message;
  }
}

function scan() {
  uni.scanCode({
    success(res) {
      code.value = res.result || "";
      look();
    },
  });
}
</script>

<template>
  <view class="pbody">
    <view class="card">
      <input class="field" v-model="code" placeholder="输入或扫描核销码" />
      <view class="row">
        <button class="btn" style="flex:1" @tap="look">识别</button>
        <button class="btn ghost" style="flex:1" @tap="scan">扫码</button>
      </view>
    </view>
    <view class="card" v-if="preview">
      <view style="font-weight:700">{{ preview.user?.nick }}</view>
      <view class="tiny">{{ preview.code }}</view>
      <view v-for="(c, i) in preview.cards" :key="i" style="padding:8px 0;border-bottom:1px solid rgba(28,27,25,.12)">
        {{ c.tpl?.name }} · {{ c.card?.no }}
        <view v-for="(rule, ri) in c.tpl?.ruleText || []" :key="ri" class="tiny gold">{{ rule }}</view>
        <view class="tiny" v-if="c.tpl?.prize">奖品（仅店员可见）：{{ c.tpl.prize }}</view>
      </view>
      <button class="btn block gold" @tap="confirm">确认核销</button>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

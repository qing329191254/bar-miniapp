<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api, savedUser } from "@/utils/api";

const kind = ref("SHARD");
const subject = ref("TEAM");
const dim = ref("WEEK");
const data = ref({ rows: [], mine: null });
const me = savedUser();

async function load() {
  data.value = await api(`/rank?kind=${kind.value}&dim=${dim.value}&subject=${subject.value}`);
}
onMounted(load);
watch([kind, subject, dim], load);

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}
function isMe(r) {
  if (subject.value === "USER") return r.user?.id === me?.id;
  return r.team?.id === me?.teamId;
}
function nameOf(r) {
  return r.team?.name || r.user?.nick;
}
function valOf(r) {
  return kind.value === "CHAMPION" ? r.v + " 冠" : fmt(r.v);
}
const color = computed(() =>
  kind.value === "SHARD" ? "#534AB7" : kind.value === "POINT" ? "#185FA5" : "#3B6D11",
);
</script>

<template>
  <view class="pbody">
    <view class="seg">
      <button class="seg-b" :class="{ on: kind === 'SHARD' }" @tap="kind = 'SHARD'">碎片榜</button>
      <button class="seg-b" :class="{ on: kind === 'POINT' }" @tap="kind = 'POINT'">积分榜</button>
      <button class="seg-b" :class="{ on: kind === 'CHAMPION' }" @tap="kind = 'CHAMPION'">冠军榜</button>
    </view>
    <view class="row" style="margin-bottom:12px">
      <text class="chip" :class="{ on: subject === 'TEAM' }" @tap="subject = 'TEAM'">战队榜</text>
      <text class="chip" :class="{ on: subject === 'USER' }" @tap="subject = 'USER'">个人榜</text>
      <text class="tiny" style="margin-left:auto">{{ dim === "WEEK" ? "当周新增" : "累计" }}</text>
    </view>
    <view class="rk-reward" v-if="kind === 'SHARD'">
      <view style="font-size:12.5px;color:#633806;font-weight:600">本周奖励 · 次周一自动发放</view>
      <view class="tiny gold" style="margin-top:3px;line-height:1.65">夺冠战队全员得战队宝箱卡 · 个人榜前三得钻石 / 黄金 / 白银宝箱卡</view>
    </view>
    <view class="rk-box">
      <view v-if="!data.rows.length" class="empty">本周还没有数据，快来玩一局</view>
      <view v-for="r in data.rows" :key="r.rank + '-' + nameOf(r)" class="rk-row" :class="{ me: isMe(r) }">
        <view class="rk-no" :class="{ top: r.rank <= 3 }">{{ r.rank }}</view>
        <view class="av">{{ (nameOf(r) || "").slice(0, 2) }}</view>
        <view style="flex:1;min-width:0">
          <view style="font-weight:500">{{ isMe(r) ? "我的" + (subject === "TEAM" ? "战队" : "") + " · " : "" }}{{ nameOf(r) }}</view>
          <view class="tiny" v-if="r.members">{{ r.members }} 名成员</view>
        </view>
        <text style="font-weight:600" :style="{ color }">{{ valOf(r) }}</text>
      </view>
    </view>
    <view class="rk-mine" v-if="data.mine">
      <text class="rk-tag">我的{{ subject === "TEAM" ? "战队" : "排名" }}</text>
      <text style="font-weight:600">第 {{ data.mine.rank }} 名</text>
      <text class="tiny" style="margin-left:auto">{{ valOf(data.mine) }}</text>
    </view>
    <view class="rk-mine" v-else>
      <text class="rk-tag">我的{{ subject === "TEAM" ? "战队" : "排名" }}</text>
      <text style="font-weight:600">暂未上榜</text>
    </view>
    <tab-bar current="rank" />
  </view>
</template>

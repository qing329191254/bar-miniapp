<script setup>
import { computed, ref, watch } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, savedUser } from "@/utils/api";

const kind = ref("SHARD");
const subject = ref("TEAM");
const dim = ref("WEEK");
const showMetric = ref(false);
const data = ref({ rows: [], mine: null });
const me = savedUser();

async function load() {
  data.value = await api(`/rank?kind=${kind.value}&dim=${dim.value}&subject=${subject.value}`);
}
onShow(load);
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
function chooseKind(value) {
  kind.value = value;
  dim.value = "WEEK";
}
function metricHint(value) {
  if (value === "WEEK") return "周一 00:00 重置";
  if (kind.value === "POINT") return "随月底清零归零";
  if (kind.value === "SHARD") return "碎片永久累计";
  return "历次冠军累计";
}
function chooseMetric(value) { dim.value = value; showMetric.value = false; }
function md(d) { return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }
const periodText = computed(() => {
  if (dim.value !== "WEEK") {
    if (kind.value === "SHARD") return "历史累计";
    if (kind.value === "CHAMPION") return "累计冠军";
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return `${md(first)} ~ ${md(last)}`;
  }
  const now = new Date();
  const day = now.getDay() || 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() - day + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return `${md(monday)} ~ ${md(sunday)}`;
});
const color = computed(() =>
  kind.value === "SHARD" ? "#534AB7" : kind.value === "POINT" ? "#185FA5" : "#3B6D11",
);
</script>

<template>
  <view class="pbody">
    <view class="seg">
      <button class="seg-b" :class="{ on: kind === 'SHARD' }" @tap="chooseKind('SHARD')">碎片榜</button>
      <button class="seg-b" :class="{ on: kind === 'POINT' }" @tap="chooseKind('POINT')">积分榜</button>
      <button class="seg-b" :class="{ on: kind === 'CHAMPION' }" @tap="chooseKind('CHAMPION')">冠军榜</button>
    </view>
    <view class="row" style="margin-bottom:12px">
      <text class="chip" :class="{ on: subject === 'TEAM' }" @tap="subject = 'TEAM'">战队榜</text>
      <text class="chip" :class="{ on: subject === 'USER' }" @tap="subject = 'USER'">个人榜</text>
      <view class="rank-period" @tap="showMetric = true">{{ periodText }} <text>▾</text></view>
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
    <view v-if="showMetric" class="metric-mask" @tap.self="showMetric = false">
      <view class="metric-sheet">
        <view class="metric-title">统计口径 <text @tap="showMetric = false">关闭</text></view>
        <view class="metric-option" :class="{ selected: dim === 'WEEK' }" @tap="chooseMetric('WEEK')"><view class="metric-name">当周新增 <text v-if="dim === 'WEEK'">✓</text></view><text>周一 00:00 重置</text></view>
        <view class="metric-option" :class="{ selected: dim !== 'WEEK' }" @tap="chooseMetric('MONTH')"><view class="metric-name">{{ kind === 'SHARD' ? '历史累计' : kind === 'CHAMPION' ? '累计冠军' : '当月累计' }} <text v-if="dim !== 'WEEK'">✓</text></view><text>{{ metricHint('MONTH') }}</text></view>
        <view class="metric-tip">统计口径由后台「榜单与奖励规则」统一配置。不同榜单的累计规则不同，榜单数据均实时读取门店业务数据。</view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.rank-period{margin-left:auto;color:#9C9A93;font-size:12px;padding:5px 0}.rank-period text{font-size:12px;font-weight:400;color:#6B6A65;margin-left:4px}.metric-mask{position:fixed;z-index:30;inset:0;background:rgba(0,0,0,.38);display:flex;align-items:flex-end}.metric-sheet{width:100%;background:#fff;border-radius:22px 22px 0 0;padding:20px 16px 28px;box-sizing:border-box}.metric-title{display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:18px;margin-bottom:14px}.metric-title text{font-size:13px;font-weight:400;color:#9C9A93}.metric-option{display:flex;justify-content:space-between;align-items:center;padding:17px 14px;border:1px solid #E2E0DA;border-bottom:0;color:#9C9A93}.metric-option:first-of-type{border-radius:14px 14px 0 0}.metric-option:nth-of-type(3){border-bottom:1px solid #E2E0DA;border-radius:0 0 14px 14px}.metric-name{color:#6B6A65;font-size:15px;font-weight:400}.metric-option.selected .metric-name{color:#1C1B19;font-weight:600}.metric-name text{margin-left:4px}.metric-option>text{font-size:12px}.metric-tip{margin-top:14px;padding:11px 12px;border-radius:10px;background:#E6F1FB;color:#185FA5;font-size:12px;line-height:1.65}
</style>

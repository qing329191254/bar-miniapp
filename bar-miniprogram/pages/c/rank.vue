<script setup>
import { computed, ref, watch } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, hideWxHomeButton, savedUser } from "@/utils/api";
import { getMemberRankCache, setMemberRankCache } from "@/utils/staff-page-cache";

const kind = ref("SHARD");
const subject = ref("TEAM");
/** PERIOD = shop current week/month; ALL = historical. Old cache used WEEK/MONTH. */
const dim = ref("PERIOD");
const showMetric = ref(false);
const cached = getMemberRankCache();
const data = ref(cached?.data || { rows: [], mine: null });
if (cached?.kind) kind.value = cached.kind;
if (cached?.subject) subject.value = cached.subject;
if (cached?.dim === "ALL" || cached?.dim === "MONTH") dim.value = "ALL";
else if (cached?.dim === "PERIOD" || cached?.dim === "WEEK") dim.value = "PERIOD";
const me = savedUser();

const shopDim = computed(() =>
  data.value?.rankDim === "MONTH" || data.value?.cfg?.rankDim === "MONTH" ? "MONTH" : "WEEK",
);
const queryDim = () => (dim.value === "ALL" ? "ALL" : "WEEK");
const keyOf = () => `${kind.value}|${dim.value}|${subject.value}`;
const byKey = new Map(cached?.data ? [[keyOf(), cached.data]] : []);
const dataKey = ref(cached?.data ? keyOf() : "");
/** Rows on screen belong to the selected board; never render another board's rows. */
const ready = computed(() => dataKey.value === keyOf());

async function load() {
  const key = keyOf();
  const hit = byKey.get(key);
  if (hit) {
    data.value = hit;
    dataKey.value = key;
  }
  try {
    const next = await api(`/rank?kind=${kind.value}&dim=${queryDim()}&subject=${subject.value}`, {
      loading: !hit,
      silent: !!hit,
    });
    byKey.set(key, next);
    if (key !== keyOf()) return;
    data.value = next;
    dataKey.value = key;
    setMemberRankCache({ kind: kind.value, subject: subject.value, dim: dim.value, data: next });
  } catch (e) {
    if (!hit) throw e;
  }
}
onShow(() => {
  hideWxHomeButton();
  load();
});
watch([kind, subject, dim], load);

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}
function isMe(r) {
  if (subject.value === "USER") return !!(r.user?.id && r.user.id === me?.id);
  return !!(r.team?.id && r.team.id === me?.teamId);
}
function nameOf(r) {
  return r.team?.name || r.user?.nick;
}
function teamLabelOf(r) {
  if (subject.value !== "USER") return "";
  return (r.user?.teamName || "").trim();
}
function valOf(r) {
  return kind.value === "CHAMPION" ? r.v + " 冠" : fmt(r.v);
}
function chooseKind(value) {
  kind.value = value;
  if (value !== "POINT") dim.value = "PERIOD";
}
function metricHint(value) {
  if (value === "PERIOD") return shopDim.value === "MONTH" ? "每月 1 日 12:00 重置" : "每周一 12:00 重置";
  if (kind.value === "SHARD") return "碎片永久累计";
  return "历次冠军累计";
}
function chooseMetric(value) {
  if (kind.value === "POINT") return;
  dim.value = value;
  showMetric.value = false;
}
function openMetric() {
  if (kind.value === "POINT") return;
  showMetric.value = true;
}
const periodText = computed(() => {
  if (kind.value === "POINT") return "当前积分";
  if (dim.value === "ALL") return kind.value === "CHAMPION" ? "累计冠军" : "历史累计";
  return data.value?.periodLabel || (shopDim.value === "MONTH" ? "当月新增" : "当周新增");
});
const color = computed(() =>
  kind.value === "SHARD" ? "#534AB7" : kind.value === "POINT" ? "#185FA5" : "#3B6D11",
);
const emptyText = computed(() => {
  if (kind.value === "POINT") return "暂无可用积分";
  if (kind.value === "CHAMPION") {
    return dim.value === "ALL"
      ? "暂无累计冠军数据"
      : shopDim.value === "MONTH" ? "本月还没有冠军记录" : "本周还没有冠军记录";
  }
  if (kind.value === "SHARD" && dim.value === "ALL") return "暂无历史碎片数据";
  return shopDim.value === "MONTH" ? "本月还没有数据，快来玩一局" : "本周还没有数据，快来玩一局";
});
/** 个人榜默认只展示前十；战队榜仍全量 */
const displayRows = computed(() => {
  if (!ready.value) return [];
  const rows = data.value?.rows || [];
  if (subject.value === "USER") return rows.slice(0, 10);
  return rows;
});
</script>

<template>
  <page-meta :page-style="`overflow:${showMetric ? 'hidden' : 'visible'}`" />
  <app-toast />
  <view class="pbody">
    <view class="seg rank-seg">
      <button class="seg-b" :class="{ on: kind === 'SHARD' }" @tap="chooseKind('SHARD')">🧩 碎片榜</button>
      <button class="seg-b" :class="{ on: kind === 'POINT' }" @tap="chooseKind('POINT')">⭐ 积分榜</button>
      <button class="seg-b" :class="{ on: kind === 'CHAMPION' }" @tap="chooseKind('CHAMPION')">🏆 冠军榜</button>
    </view>
    <view class="row" style="margin-bottom:12px">
      <text class="chip" :class="{ on: subject === 'TEAM' }" @tap="subject = 'TEAM'">战队榜</text>
      <text class="chip" :class="{ on: subject === 'USER' }" @tap="subject = 'USER'">个人榜</text>
      <view
        class="rank-period"
        :class="{ static: kind === 'POINT' }"
        @tap="openMetric"
      >{{ periodText }} <text v-if="kind !== 'POINT'">▾</text></view>
    </view>
    <view class="rk-reward" v-if="kind === 'SHARD'">
      <view style="font-size:12.5px;color:#633806;font-weight:600">{{ shopDim === "MONTH" ? "本月奖励 · 次月 1 日 12:00 自动发放" : "本周奖励 · 每周一 12:00 自动发放" }}</view>
      <view class="tiny gold" style="margin-top:3px;line-height:1.65">第一名战队全员得战队奖励卡 · 个人榜前三名得店内奖励卡（碎片为荣誉值，不可兑换）</view>
    </view>
    <view class="rk-reward point-hint" v-else-if="kind === 'POINT'">
      <view style="font-size:12.5px;color:#0C447C;font-weight:600">会员积分排行</view>
      <view class="tiny" style="margin-top:3px;line-height:1.65;color:#185FA5">按当前可用积分排序，战队榜为成员积分之和。积分仅限本店会员权益使用，不可兑换现金、不可转让。</view>
    </view>
    <view class="rk-box">
      <view v-if="!ready" class="empty"></view>
      <view v-else-if="!displayRows.length" class="empty">{{ emptyText }}</view>
      <view v-for="r in displayRows" :key="r.rank + '-' + nameOf(r)" class="rk-row" :class="{ me: isMe(r) }">
        <view class="rk-no" :class="{ top: r.rank <= 3 }">{{ r.rank }}</view>
        <view class="av">{{ (nameOf(r) || "").slice(0, 2) }}</view>
        <view style="flex:1;min-width:0">
          <view class="rk-name-line">
            <text class="rk-nick">{{ isMe(r) ? "我的" + (subject === "TEAM" ? "战队" : "") + " · " : "" }}{{ nameOf(r) }}</text>
            <text v-if="subject === 'USER' && teamLabelOf(r)" class="rk-team-tag">{{ teamLabelOf(r) }}</text>
          </view>
          <view class="tiny" v-if="r.members">{{ r.members }} 名成员</view>
        </view>
        <text style="font-weight:600" :style="{ color }">{{ valOf(r) }}</text>
      </view>
    </view>
    <view class="rk-mine" v-if="ready && data.mine">
      <text class="rk-tag">我的{{ subject === "TEAM" ? "战队" : "排名" }}</text>
      <text style="font-weight:600">第 {{ data.mine.rank }} 名</text>
      <text class="tiny" style="margin-left:auto">{{ valOf(data.mine) }}</text>
    </view>
    <view class="rk-mine" v-else-if="ready">
      <text class="rk-tag">我的{{ subject === "TEAM" ? "战队" : "排名" }}</text>
      <text style="font-weight:600">暂未上榜</text>
    </view>
    <tab-bar current="rank" />
    <view v-if="showMetric && kind !== 'POINT'" class="metric-mask" @tap.self="showMetric = false">
      <view class="metric-sheet">
        <view class="metric-title">统计方式 <text @tap="showMetric = false">关闭</text></view>
        <view class="metric-option" :class="{ selected: dim === 'PERIOD' }" @tap="chooseMetric('PERIOD')"><view class="metric-name">{{ shopDim === 'MONTH' ? '当月新增' : '当周新增' }} <text v-if="dim === 'PERIOD'">✓</text></view><text>{{ metricHint('PERIOD') }}</text></view>
        <view class="metric-option" :class="{ selected: dim === 'ALL' }" @tap="chooseMetric('ALL')"><view class="metric-name">{{ kind === 'SHARD' ? '历史累计' : '累计冠军' }} <text v-if="dim === 'ALL'">✓</text></view><text>{{ metricHint('ALL') }}</text></view>
        <view class="metric-tip">碎片榜与冠军榜可按当期或累计查看。积分榜固定为当前可用积分，不支持周/月切换。</view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.rk-name-line{display:flex;align-items:center;flex-wrap:wrap;gap:6px;min-width:0}
.rk-nick{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.rk-team-tag{flex:none;max-width:9em;padding:1px 7px;border:1px solid #E2E0DA;border-radius:99px;color:#6B6A65;font-size:10px;line-height:1.5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rank-period{margin-left:auto;color:#9C9A93;font-size:12px;padding:5px 0}.rank-period text{font-size:12px;font-weight:400;color:#6B6A65;margin-left:4px}.rank-period.static{color:#185FA5}.point-hint{background:linear-gradient(135deg,#E6F1FB,#F0F7FD);border-color:rgba(24,95,165,.28)}.metric-mask{position:fixed;z-index:30;inset:0;background:rgba(0,0,0,.38);display:flex;align-items:flex-end}.metric-sheet{width:100%;background:#fff;border-radius:22px 22px 0 0;padding:20px 16px 28px;box-sizing:border-box}.metric-title{display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:18px;margin-bottom:14px}.metric-title text{font-size:13px;font-weight:400;color:#9C9A93}.metric-option{display:flex;justify-content:space-between;align-items:center;padding:17px 14px;border:1px solid #E2E0DA;border-bottom:0;color:#9C9A93}.metric-option:first-of-type{border-radius:14px 14px 0 0}.metric-option:nth-of-type(3){border-bottom:1px solid #E2E0DA;border-radius:0 0 14px 14px}.metric-name{color:#6B6A65;font-size:15px;font-weight:400}.metric-option.selected .metric-name{color:#1C1B19;font-weight:600}.metric-name text{margin-left:4px}.metric-option>text{font-size:12px}.metric-tip{margin-top:14px;padding:11px 12px;border-radius:10px;background:#E6F1FB;color:#185FA5;font-size:12px;line-height:1.65}
</style>

<script setup>
import { computed, ref } from "vue";
import { onReachBottom, onShow } from "@dcloudio/uni-app";
import { api, isLoggedIn, toastText } from "@/utils/api";

const guest = !isLoggedIn();

const data = ref(null);
const loadingMore = ref(false);
const personalRank = ref({ rows: [], mine: null });
const teamRank = ref({ rows: [], mine: null });

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

function md(date) {
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

const weekPeriod = computed(() => {
  const now = new Date();
  const day = now.getDay() || 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() - day + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return `${md(monday)} ~ ${md(sunday)}`;
});

const personalHint = computed(() => {
  const mine = personalRank.value.mine;
  if (!mine) return "个人榜暂未上榜";
  if (mine.rank <= 3) return `个人榜第 ${mine.rank} 名 · 当前第 ${mine.rank} 名，保持住！`;
  const third = personalRank.value.rows.find((row) => row.rank === 3);
  const gap = third ? Math.max(0, Number(third.v || 0) - Number(mine.v || 0)) : 0;
  return gap > 0
    ? `个人榜第 ${mine.rank} 名 · 距前三还差 ${fmt(gap)} 碎片`
    : `个人榜第 ${mine.rank} 名`;
});

const teamHint = computed(() => {
  const mine = teamRank.value.mine;
  return mine ? `战队榜第 ${mine.rank} 名 · 第一名可得战队奖励卡` : "暂无战队";
});

onShow(async () => {
  if (guest) return;
  const [shards, personal, team] = await Promise.all([
    api("/shards"),
    api("/rank?kind=SHARD&dim=WEEK&subject=USER"),
    api("/rank?kind=SHARD&dim=WEEK&subject=TEAM"),
  ]);
  data.value = shards;
  personalRank.value = personal;
  teamRank.value = team;
});

async function loadMore() {
  const cur = data.value;
  if (!cur?.hasMore || loadingMore.value) return;
  loadingMore.value = true;
  try {
    const res = await api(`/shards/records?limit=30&before=${encodeURIComponent(cur.cursor || "")}`, { silent: true, loading: false });
    if (data.value !== cur) return;
    const seen = new Set(cur.records.map((g) => g.key || g.id));
    const more = (res?.items || []).filter((g) => !seen.has(g.key || g.id));
    data.value = { ...cur, records: [...cur.records, ...more], cursor: res?.cursor || cur.cursor, hasMore: !!res?.hasMore };
  } catch (error) {
    toastText(error.message || "加载失败");
  } finally {
    loadingMore.value = false;
  }
}
onReachBottom(() => loadMore());
</script>

<template>
  <guest-gate v-if="guest" text="登录后查看我的碎片" />
  <view class="shard-page" v-if="data">
    <view class="summary-card purple-card">
      <view class="summary-grid">
        <view class="summary-item">
          <view class="summary-label">当周碎片</view>
          <view class="summary-value number-display">{{ fmt(data.shard.w) }}</view>
        </view>
        <view class="summary-item">
          <view class="summary-label">历史累计</view>
          <view class="summary-value number-display">{{ fmt(data.shard.t) }}</view>
        </view>
      </view>
      <view class="summary-tip">碎片为荣誉值，不可兑换，仅用于周榜排名</view>
    </view>

    <view class="rank-card purple-card">
      <view class="rank-head">
        <text class="rank-title">本周排名</text>
        <text class="rank-period">{{ weekPeriod }}</text>
      </view>
      <view class="rank-line">{{ personalHint }}</view>
      <view class="rank-line">{{ teamHint }}</view>
    </view>

    <view class="records-head">
      <text class="records-title">碎片记录</text>
      <text class="records-period">按时间倒序</text>
    </view>

    <view class="records-card">
      <view v-if="!data.records.length" class="empty-records">暂无碎片记录，参与桌游对局可获得碎片</view>
      <view v-for="g in data.records" :key="g.key || g.id" class="record-row">
        <view class="record-copy">
          <view class="record-name">{{ g.title }}</view>
          <view class="record-meta">{{ g.meta }}</view>
        </view>
        <text class="record-value" :class="{ minus: g.delta < 0, void: g.void }">{{ g.delta > 0 ? "+" : "" }}{{ fmt(g.delta) }}</text>
      </view>
    </view>
    <view v-if="data.records.length" class="list-foot" @tap="loadMore">
      {{ loadingMore ? "加载中…" : data.hasMore ? "上拉或点此加载更早记录" : `已显示全部 ${data.records.length} 条` }}
    </view>
  </view>
</template>

<style scoped>
.shard-page { min-height:100vh;box-sizing:border-box;padding:14px 12px 40px;background:#f5f4f0; }
.purple-card { border:1.5px solid #534ab7;border-radius:15px;background:#eeedff;color:#534ab7;box-sizing:border-box; }
.summary-card { padding:14px 14px 13px;margin-bottom:12px; }
.summary-grid { display:flex; }
.summary-item { width:50%; }
.summary-label { font-size:12px;line-height:1.4; }
.summary-value { margin-top:3px;color:#26215c;font-size:30px;line-height:1.25; }
.summary-tip { margin-top:10px;font-size:12px;line-height:1.5; }
.rank-card { padding:13px 14px 12px;margin-bottom:14px; }
.rank-head { display:flex;align-items:center;justify-content:space-between;margin-bottom:6px; }
.rank-title { color:#26215c;font-size:14px;font-weight:700; }
.rank-period,.rank-line { color:#534ab7;font-size:12px; }
.rank-line { line-height:1.7; }
.records-head { display:flex;align-items:center;justify-content:space-between;margin-bottom:8px; }
.records-title { color:#1c1b19;font-size:15px;font-weight:700; }
.records-period { color:#9c9a93;font-size:12px; }
.records-card { padding:0 14px;border:1px solid rgba(28,27,25,.12);border-radius:14px;background:#fff;box-shadow:0 2px 5px rgba(28,27,25,.06); }
.record-row { display:flex;align-items:center;min-height:65px;border-bottom:1px solid rgba(28,27,25,.12); }
.record-row:last-child { border-bottom:none; }
.record-copy { flex:1;min-width:0;padding:11px 10px 11px 0; }
.record-name { color:#1c1b19;font-size:14px;line-height:1.45; }
.record-meta { margin-top:3px;color:#6b6a65;font-size:12px;line-height:1.45; }
.record-value { flex:none;color:#534ab7;font-size:15px; }
.record-value.minus { color:#a32d2d; }
.record-value.void { color:#9c9a93;text-decoration:line-through; }
.empty-records { padding:32px 8px;color:#9c9a93;font-size:12px;text-align:center; }
.list-foot { padding:14px 0 4px;text-align:center;color:#9c9a93;font-size:12px; }
</style>

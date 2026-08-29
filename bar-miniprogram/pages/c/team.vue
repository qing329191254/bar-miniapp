<script setup>
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { api, savedUser } from "@/utils/api";

const data = ref(null);
const me = savedUser();
function fmt(n) { return Number(n || 0).toLocaleString("en-US"); }
onLoad(async (options) => {
  const id = Number(options?.id || me?.teamId || 0);
  if (id) data.value = await api(`/teams/${id}`);
});
</script>

<template>
  <view v-if="data" class="team-page">
    <view class="team-hero">
      <view class="team-head"><view class="team-avatar">{{ data.team.name.slice(0, 1) }}</view><view><view class="team-name">{{ data.team.name }}</view><view class="team-meta">{{ data.members.length }} 名成员 · 本周战队榜第 {{ data.rank || "—" }} 名</view></view></view>
      <view class="team-stats">
        <view><text class="stat-num number-display">{{ data.champs }}</text><text>战队夺冠</text></view>
        <view><text class="stat-num number-display">{{ fmt(data.shardWeek) }}</text><text>本周碎片</text></view>
        <view><text class="stat-num number-display">{{ fmt(data.shardTotal) }}</text><text>历史碎片</text></view>
      </view>
    </view>
    <view class="section-head"><text>战队成员</text><text>{{ data.members.length }} 人 · 按本周碎片排序</text></view>
    <view class="list-card">
      <view v-for="(member, index) in data.members" :key="member.id" class="member-row">
        <text class="member-rank">{{ index + 1 }}</text><view class="member-avatar">{{ member.av }}</view>
        <view class="member-copy"><view class="member-name">{{ member.nick }} <text v-if="member.id === me?.id" class="me-tag">我</text></view><view class="member-meta">{{ member.no }} · 个人冠军 {{ member.champions }} 次</view></view>
        <view class="member-shard"><text class="number-display">{{ fmt(member.shardWeek) }}</text><text>本周碎片</text></view>
      </view>
    </view>
    <view class="section-head record-head"><text>战队夺冠记录</text><text>{{ data.champs }} 次 · 本月 {{ data.monthChamps }} 次</text></view>
    <view class="list-card">
      <view v-if="!data.records.length" class="empty">暂无战队夺冠记录</view>
      <view v-for="(item,index) in data.records" :key="item.date+'-'+index" class="champ-row"><view class="crown">冠</view><view><view class="champ-title">{{ item.event }}</view><view class="champ-meta">{{ item.date }}<text v-if="item.n"> · 参赛 {{ item.n }} 人</text> · {{ item.nick }}</view><view v-if="item.teamName && item.teamName !== data.team.name" class="champ-note">获奖时战队：{{ item.teamName }}（该成员后调入本队）</view></view></view>
    </view>
    <view class="team-note">战队冠军数为当前队员的个人冠军实时聚合，成员调队会同时改变两个战队的数字；夺冠记录保留“获奖时战队”快照，已发放的历史奖励不受调队影响。</view>
  </view>
</template>

<style scoped>
.team-page{min-height:100vh;box-sizing:border-box;padding:14px 12px 40px;background:#f5f4f0}.team-hero{padding:13px 14px;margin-bottom:14px;border-radius:15px;background:linear-gradient(135deg,#51439e,#8b82df);color:#fff;box-shadow:0 6px 14px rgba(83,74,183,.2)}.team-head{display:flex;align-items:center;gap:14px}.team-avatar{width:48px;height:48px;display:flex;align-items:center;justify-content:center;border-radius:12px;background:rgba(255,255,255,.18);font-size:20px;font-weight:700}.team-name{font-size:18px;font-weight:700}.team-meta{margin-top:3px;color:rgba(255,255,255,.78);font-size:12px}.team-stats{display:flex;margin-top:16px}.team-stats>view{flex:1;display:flex;flex-direction:column;align-items:center;color:rgba(255,255,255,.78);font-size:11px}.stat-num{color:#fff;font-size:23px;line-height:1.35}.section-head{display:flex;justify-content:space-between;align-items:center;margin:0 0 8px;font-size:15px;font-weight:700}.section-head>text:last-child{color:#9c9a93;font-size:11px;font-weight:400}.record-head{margin-top:14px}.list-card{padding:0 14px;border:1px solid rgba(28,27,25,.12);border-radius:14px;background:#fff;box-shadow:0 2px 5px rgba(28,27,25,.05)}.member-row{display:flex;align-items:center;gap:9px;padding:12px 0;border-bottom:1px solid rgba(28,27,25,.12)}.member-row:last-child,.champ-row:last-child{border-bottom:none}.member-rank{width:16px;color:#ba7517;text-align:center;font-weight:600}.member-avatar{width:32px;height:32px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:50%;background:#e2e0da;color:#9c9a93;font-size:11px}.member-copy{flex:1;min-width:0}.member-name{font-size:14px}.member-meta{color:#6b6a65;font-size:11px}.me-tag{display:inline-block;padding:1px 8px;margin-left:4px;border-radius:99px;background:#e6f1fb;color:#185fa5;font-size:10px}.member-shard{display:flex;flex-direction:column;align-items:flex-end;color:#9c9a93;font-size:10px}.member-shard text:first-child{color:#534ab7;font-size:14px}.champ-row{display:flex;align-items:center;gap:10px;padding:13px 0;border-bottom:1px solid rgba(28,27,25,.12)}.crown{width:32px;height:32px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:8px;background:#fac775;color:#633806;font-size:11px}.champ-title{font-size:14px}.champ-meta{margin-top:2px;color:#6b6a65;font-size:11px}.champ-note{margin-top:3px;color:#9c9a93;font-size:10px}.team-note{padding:12px 14px;margin-top:14px;border:1px dashed rgba(28,27,25,.15);border-radius:14px;color:#9c9a93;font-size:11px;line-height:1.8}.empty{padding:32px 0;text-align:center;color:#9c9a93;font-size:12px}
</style>

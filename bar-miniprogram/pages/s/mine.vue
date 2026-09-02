<script setup>
import { computed, onMounted, ref } from "vue";
import { api, clearSession, go, relaunch } from "@/utils/api";
import { reminderState, saveReminderPrefs, testStaffReminder } from "@/utils/staff-reminder";

const me = ref(null);
const todo = ref(null);
const roleMap = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };
const weekNames = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

const todayHint = computed(() => {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${mm}-${dd} ${weekNames[now.getDay()]}`;
});

const jobItems = computed(() => {
  if (!todo.value) return [];
  const s = todo.value.stat;
  return [
    { kind: "accept", icon: "accept", tone: "amber", title: "今日接单", sub: todayHint.value, val: `${s.orders} 单` },
    { kind: "pay", icon: "pay", tone: "blue", title: "今日收款确认", sub: `充值 ¥${s.rcAmt} + 点单 ¥${s.odAmt}`, val: `¥${s.amount}` },
    { kind: "verify", icon: "verify", tone: "purple", title: "今日核销", sub: "卡券", val: `${s.verifies} 张` },
    { kind: "game", icon: "game", tone: "teal", title: "今日对局录入", sub: `${s.heads || 0} 人次`, val: `${s.games} 局` },
    { kind: "grant", icon: "grant", tone: "green", title: "今日发分", sub: "店员当面确认后发放", val: `${s.wds} 笔`, last: true },
  ];
});

const pushItems = computed(() => {
  if (!me.value) return [];
  const p = me.value.push || {};
  return [
    { key: "voice", icon: "bell", tone: "blue", title: "前台声音提醒", sub: "新单到达时播放提示音", enabled: p.enabled !== false && p.miniVoice !== false && reminderState.prefs.voice },
    { key: "vibrate", icon: "accept", tone: "amber", title: "前台震动提醒", sub: "新单到达时同步震动", enabled: p.enabled !== false && p.miniVibrate !== false && reminderState.prefs.vibrate },
    { key: "badge", icon: "todo", tone: "purple", title: "待办角标", sub: "底部待办入口显示未处理数量", enabled: p.enabled !== false && p.miniBadge !== false && reminderState.prefs.badge },
  ];
});

onMounted(async () => {
  me.value = await api("/me");
  todo.value = await api("/staff/todo");
});

function logout() {
  clearSession();
  relaunch("/pages/login/login");
}
function openDetail(kind) {
  go(`/pages/s/job-detail?kind=${kind}`);
}
function toggleReminder(item) {
  saveReminderPrefs({ [item.key]: !reminderState.prefs[item.key] });
}
</script>

<template>
  <app-toast />
  <view class="pbody" v-if="me">
    <view class="staff-hd">
      <view class="row">
        <view class="ph-lg">{{ me.user.av }}</view>
        <view style="margin-left:12px;flex:1;min-width:0">
          <view style="font-size:16px;font-weight:600">{{ me.user.nick }}</view>
          <view class="tiny" style="color:rgba(255,255,255,.72);margin-top:2px">{{ me.user.phone }}</view>
          <view class="row" style="margin-top:6px">
            <text class="pill-w">{{ roleMap[me.user.role] || me.user.role }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="card" v-if="todo">
      <view class="sec-head">
        <view class="h2 sec-title">我的作业记录</view>
        <text class="sec-hint">今日 · 点进可查历史</text>
      </view>
      <view
        v-for="item in jobItems"
        :key="item.kind"
        class="job-stat"
        :class="{ 'job-stat-last': item.last }"
        @tap="item.kind !== 'grant' ? openDetail(item.kind) : undefined"
      >
        <app-icon :name="item.icon" :tone="item.tone" size="sm" shape="soft" />
        <view class="gr">
          <view style="font-weight:500">{{ item.title }}</view>
          <view class="li-sub">{{ item.sub }}</view>
        </view>
        <text class="li-val">{{ item.val }}<text v-if="item.kind !== 'grant'"> ›</text></text>
      </view>
    </view>

    <view class="card">
      <view class="sec-head"><view class="h2 sec-title">前台值守提醒</view><text class="sec-hint">仅小程序前台生效</text></view>
      <view v-for="(item, i) in pushItems" :key="item.title" class="job-stat reminder-item" :class="{ 'job-stat-last': i === pushItems.length - 1 }" @tap="toggleReminder(item)">
        <app-icon :name="item.icon" :tone="item.tone" size="sm" shape="soft" />
        <view class="gr">
          <view style="font-weight:500">{{ item.title }}</view>
          <view class="li-sub">{{ item.sub }}</view>
        </view>
        <view class="mini-toggle" :class="{ on: item.enabled }"><i /></view>
      </view>
      <button class="btn ghost block reminder-test" @tap="testStaffReminder">测试声音和震动</button>
    </view>

    <button class="btn ghost block foot-btn" @tap="logout">切换账号</button>
    <tab-bar current="mine" />
  </view>
</template>

<style scoped>
.sec-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 9px;
}
.sec-title {
  margin-bottom: 0;
}
.sec-hint {
  margin-left: auto;
  font-size: 11px;
  color: #9c9a93;
  flex-shrink: 0;
}
.li-sub {
  font-size: 11px;
  color: #6b6a65;
  margin-top: 2px;
  line-height: 1.45;
}
.reminder-item{cursor:pointer}.mini-toggle{position:relative;width:40px;height:22px;flex:none;border:1px solid rgba(82,59,32,.16);border-radius:99px;background:#ded4c6;box-sizing:border-box}.mini-toggle i{position:absolute;left:2px;top:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 4px rgba(74,52,28,.18);transition:transform .18s}.mini-toggle.on{background:linear-gradient(135deg,#c8862a,#e8b45a);border-color:rgba(185,120,34,.42)}.mini-toggle.on i{transform:translateX(18px)}.reminder-test{margin-top:12px}
.li-val {
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 8px;
  font-size: 13px;
}
.job-stat-last {
  border-bottom: none;
}
.job-stat:not(.job-stat-last):active {
  opacity: 0.72;
}
.pill-on {
  background: linear-gradient(135deg, #eaf3de, #d4eac0);
  color: #3b6d11;
}
.pill-off {
  background: #fcebeb;
  color: #a32d2d;
}
</style>

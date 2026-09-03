<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, clearSession, go, hideWxHomeButton, relaunch, setPortal } from "@/utils/api";
import { getStaffMineCache, setStaffMineCache } from "@/utils/staff-page-cache";
import { reminderState, saveReminderPrefs, stopStaffReminder, testStaffReminder } from "@/utils/staff-reminder";

const cache = getStaffMineCache();
const me = ref(cache.me);
const todo = ref(cache.todo);
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
    { key: "badge", icon: "todo", tone: "purple", title: "待办角标", sub: "底部待办入口显示未处理数量", enabled: p.enabled !== false && p.miniBadge !== false && reminderState.prefs.badge },
  ];
});

async function load() {
  const hasCache = me.value && todo.value;
  const [meRes, todoRes] = await Promise.all([
    api("/me", { loading: !hasCache, silent: hasCache }),
    api("/staff/todo", { loading: false, silent: true }),
  ]);
  me.value = meRes;
  todo.value = todoRes;
  setStaffMineCache(meRes, todoRes);
}

onShow(() => {
  hideWxHomeButton();
  load();
});

function logout() {
  clearSession();
  relaunch("/pages/login/login");
}
function switchToCustomer() {
  setPortal("customer");
  stopStaffReminder();
  relaunch("/pages/c/home");
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
      <view
        v-for="(item, i) in pushItems"
        :key="item.title"
        class="reminder-row"
        :class="{ 'reminder-row-last': i === pushItems.length - 1 }"
      >
        <view
          class="reminder-row-main"
          hover-class="reminder-row-main-hover"
          :hover-stay-time="0"
          @tap="toggleReminder(item)"
        >
          <app-icon :name="item.icon" :tone="item.tone" size="sm" shape="soft" />
          <view class="gr">
            <view style="font-weight:500">{{ item.title }}</view>
            <view class="li-sub">{{ item.sub }}</view>
          </view>
        </view>
        <view
          class="mini-toggle"
          :class="{ on: item.enabled }"
          hover-class="mini-toggle-press"
          :hover-stay-time="0"
          @tap="toggleReminder(item)"
        >
          <view class="mini-toggle-thumb" />
        </view>
      </view>
      <button class="btn ghost block reminder-test" @tap="testStaffReminder">测试声音提醒</button>
    </view>

    <button class="btn ghost block foot-btn" style="margin-bottom:10px" @tap="switchToCustomer">切换到会员端</button>
    <button class="btn ghost block foot-btn" @tap="logout">切换账号</button>
  </view>
  <tab-bar current="mine" />
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
.reminder-row {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 0;
  border-bottom: 1px solid rgba(28, 27, 25, 0.08);
  background: #fff;
}
.reminder-row-last {
  border-bottom: none;
}
.reminder-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 11px;
}
.reminder-row-main:active {
  opacity: 1;
  background: transparent;
}
.reminder-row-main-hover {
  opacity: 1 !important;
  background-color: transparent !important;
}
.reminder-row .mini-toggle {
  flex: none;
}
.mini-toggle-press {
  opacity: 1;
  background: linear-gradient(180deg, #ece6dc, #ded4c6);
}
.mini-toggle.on.mini-toggle-press {
  background: linear-gradient(135deg, #d8a356 0%, #b87320 55%, #965614 100%);
}
.mini-toggle {
  position: relative;
  width: 40px;
  height: 22px;
  border: 1px solid rgba(82, 59, 32, 0.16);
  border-radius: 999px;
  background: linear-gradient(180deg, #ece6dc, #ded4c6);
  box-shadow: inset 0 1px 2px rgba(74, 52, 28, 0.08);
  box-sizing: border-box;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.mini-toggle-thumb {
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(74, 52, 28, 0.16);
  transition: transform 0.18s ease;
}
.mini-toggle.on {
  border-color: rgba(185, 120, 34, 0.42);
  background: linear-gradient(135deg, #d8a356 0%, #b87320 55%, #965614 100%);
  box-shadow: inset 0 1px 2px rgba(116, 74, 20, 0.14);
}
.mini-toggle.on .mini-toggle-thumb {
  transform: translateX(18px);
}
.reminder-test {
  margin-top: 12px;
}
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

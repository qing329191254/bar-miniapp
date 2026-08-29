<script setup>
import { computed, onMounted, ref } from "vue";
import { api, clearSession, go, relaunch } from "@/utils/api";

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

onMounted(async () => {
  me.value = await api("/me");
  todo.value = await api("/staff/todo");
});

function logout() {
  clearSession();
  relaunch("/pages/login/login");
}
function on(v) {
  return v ? "已开启" : "已关闭";
}
function openDetail(kind) {
  go(`/pages/s/job-detail?kind=${kind}`);
}
</script>

<template>
  <view class="pbody" v-if="me">
    <view class="card">
      <view class="row">
        <view class="av" style="width:46px;height:46px;font-size:15px">{{ me.user.av }}</view>
        <view style="margin-left:11px">
          <view style="font-size:15px;font-weight:600">{{ me.user.nick }}</view>
          <view class="tiny">{{ me.user.phone }}</view>
          <view class="row" style="margin-top:4px">
            <text class="pill" style="background:#E6F1FB;color:#185FA5">{{ roleMap[me.user.role] || me.user.role }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="card" v-if="todo">
      <view class="sec-head">
        <view class="h2 sec-title">我的作业记录</view>
        <text class="sec-hint">今日 · 点进可查历史</text>
      </view>
      <view class="li job-li" @tap="openDetail('accept')">
        <view class="gr">
          <view style="font-weight:500">今日接单</view>
          <view class="li-sub">{{ todayHint }}</view>
        </view>
        <text class="li-val">{{ todo.stat.orders }} 单 ›</text>
      </view>
      <view class="li job-li" @tap="openDetail('pay')">
        <view class="gr">
          <view style="font-weight:500">今日收款确认</view>
          <view class="li-sub">充值 ¥{{ todo.stat.rcAmt }} + 点单 ¥{{ todo.stat.odAmt }}</view>
        </view>
        <text class="li-val">¥{{ todo.stat.amount }} ›</text>
      </view>
      <view class="li job-li" @tap="openDetail('verify')">
        <view class="gr">
          <view style="font-weight:500">今日核销</view>
          <view class="li-sub">卡券</view>
        </view>
        <text class="li-val">{{ todo.stat.verifies }} 张 ›</text>
      </view>
      <view class="li job-li" @tap="openDetail('game')">
        <view class="gr">
          <view style="font-weight:500">今日对局录入</view>
          <view class="li-sub">{{ todo.stat.heads || 0 }} 人次</view>
        </view>
        <text class="li-val">{{ todo.stat.games }} 局 ›</text>
      </view>
      <view class="li" style="border-bottom:none">
        <view class="gr">
          <view style="font-weight:500">今日发分</view>
          <view class="li-sub">店员当面确认后发放 · 可在管理后台查看提分单明细</view>
        </view>
        <text class="li-val">{{ todo.stat.wds }} 笔</text>
      </view>
    </view>

    <view class="card">
      <view class="h2">消息推送</view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">新订单提醒</view><view class="tiny">微信订阅消息推送</view></view>
        <text class="pill" :style="me.push?.enabled && me.push?.order ? 'background:#EAF3DE;color:#3B6D11' : 'background:#FCEBEB;color:#A32D2D'">{{ on(me.push?.enabled && me.push?.order) }}</text>
      </view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">待办事项提醒</view><view class="tiny">待接单 / 待收款</view></view>
        <text class="pill" :style="me.push?.enabled && me.push?.todo ? 'background:#EAF3DE;color:#3B6D11' : 'background:#FCEBEB;color:#A32D2D'">{{ on(me.push?.enabled && me.push?.todo) }}</text>
      </view>
      <view class="li" style="border-bottom:none">
        <view class="gr"><view style="font-weight:500">周结算提醒</view></view>
        <text class="pill" :style="me.push?.enabled && me.push?.settle ? 'background:#EAF3DE;color:#3B6D11' : 'background:#FCEBEB;color:#A32D2D'">{{ on(me.push?.enabled && me.push?.settle) }}</text>
      </view>
    </view>

    <button class="btn ghost block" @tap="logout">切换账号</button>
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
.li-val {
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 8px;
}
.job-li:active {
  opacity: 0.72;
}
</style>

<script setup>
import { onMounted, ref } from "vue";
import { api, clearSession, relaunch } from "@/utils/api";

const me = ref(null);
const todo = ref(null);
const roleMap = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

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
      <view class="h2">我的作业记录</view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">今日接单</view><view class="tiny">今日</view></view>
        <text style="font-weight:600">{{ todo.stat.orders }} 单</text>
      </view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">今日收款确认</view><view class="tiny">充值 ¥{{ todo.stat.rcAmt }} + 点单 ¥{{ todo.stat.odAmt }}</view></view>
        <text style="font-weight:600">¥{{ todo.stat.amount }}</text>
      </view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">今日核销</view><view class="tiny">卡券</view></view>
        <text style="font-weight:600">{{ todo.stat.verifies }} 张</text>
      </view>
      <view class="li">
        <view class="gr"><view style="font-weight:500">今日对局录入</view></view>
        <text style="font-weight:600">{{ todo.stat.games }} 局</text>
      </view>
      <view class="li" style="border-bottom:none">
        <view class="gr"><view style="font-weight:500">今日发分</view><view class="tiny">提分单确认发放</view></view>
        <text style="font-weight:600">{{ todo.stat.wds }} 笔</text>
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

    <view class="card" style="background:#FAF9F5">
      <view class="h2">只读信息</view>
      <view class="tiny">一个微信号只能一个角色，不可切换到顾客模式。退款 / 作废 / 调金币 / 补发卡券需店长以上在 Web 端操作。</view>
    </view>

    <button class="btn ghost block" @tap="logout">切换演示账号</button>
    <tab-bar current="mine" />
  </view>
</template>

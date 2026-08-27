<script setup>
import { computed, onMounted, ref } from "vue";
import { api, go, loadGameDraft } from "@/utils/api";

const data = ref(null);
const msg = ref("");
const tab = ref("accept");

async function load() {
  data.value = await api("/staff/todo");
}
onMounted(load);

const defs = computed(() => {
  if (!data.value) return [];
  return [
    { k: "accept", label: "待接单", n: data.value.accept.length },
    { k: "pay", label: "待收款", n: data.value.recharges.length + data.value.payOrders.length },
    { k: "wdr", label: "待确认提分", n: data.value.withdrawals.length },
    { k: "making", label: "制作中", n: data.value.making.length },
  ];
});
const total = computed(() => defs.value.reduce((s, d) => s + d.n, 0));
const draft = computed(() => {
  const d = loadGameDraft();
  return d && d.step >= 1 && d.step <= 4 ? d : null;
});
const cur = computed(() => {
  const d = defs.value.find((x) => x.k === tab.value) || defs.value[0];
  if (d && d.n === 0) {
    const alt = defs.value.find((x) => x.n > 0);
    return alt || d;
  }
  return d;
});

async function act(path) {
  msg.value = "";
  try {
    await api(path, { method: "POST", body: { reason: "店员操作" } });
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view class="card" style="background:#FCEBEB;border-color:#E24B4A;padding:10px 12px">
      <view class="row">
        <text style="font-size:13px;font-weight:600;color:#A32D2D">共 {{ total }} 项待办</text>
      </view>
    </view>
    <view class="card" v-if="draft" style="background:#FAEEDA;border-color:#BA7517;padding:10px 12px">
      <view class="between">
        <text style="font-size:13px;font-weight:600;color:#BA7517">有 1 局未提交</text>
        <button class="btn gold" style="padding:6px 12px;font-size:12px" @tap="go('/pages/s/game', true)">继续录入</button>
      </view>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
    <view class="stodo-tabs">
      <view
        v-for="d in defs"
        :key="d.k"
        class="stodo-tab"
        :class="{ on: cur && cur.k === d.k }"
        @tap="tab = d.k"
      >
        {{ d.label }}
        <text v-if="d.n" class="stodo-n">{{ d.n }}</text>
      </view>
    </view>

    <view v-if="cur && cur.k==='accept'">
      <view class="card" v-for="o in data.accept" :key="o.id" :style="o.lack ? 'border-color:#E9C4C4;background:#FCEBEB' : 'border-color:#BA7517;background:#FAEEDA'">
        <view class="between">
          <text style="font-weight:600">{{ o.user?.nick }} {{ o.user?.tail }}</text>
          <text class="pill">{{ o.tableName || "未指定" }}</text>
        </view>
        <view class="tiny" style="margin:6px 0">{{ (o.items||[]).map(i=>i.name+'×'+i.qty).join('、') }}</view>
        <view class="tiny" v-if="o.lack" style="color:#A32D2D">余额不足，差 {{ o.lack }} 金币</view>
        <view class="between" style="margin-top:8px">
          <text style="font-size:16px;font-weight:600">{{ o.total }} 金币</text>
          <view class="row">
            <button class="btn ghost" @tap="act('/staff/orders/'+o.id+'/reject')">拒单</button>
            <button class="btn" :disabled="!!o.lack" @tap="act('/staff/orders/'+o.id+'/accept')">接单</button>
          </view>
        </view>
      </view>
      <view class="empty" v-if="!data.accept.length">暂无待接单</view>
    </view>

    <view v-if="cur && cur.k==='pay'">
      <view class="card" v-for="r in data.recharges" :key="'r'+r.id" style="border-color:#185FA5;background:#E6F1FB">
        <view class="between">
          <text class="pill" style="background:#185FA5;color:#fff">充值单</text>
          <text class="tiny" style="color:#A32D2D">{{ r.remain }}</text>
        </view>
        <view class="between" style="margin:8px 0">
          <view><view class="tiny">应收现金</view><view style="font-size:20px;font-weight:700">¥{{ r.amount }}</view></view>
          <view style="text-align:right"><view class="tiny">单号后四位</view><view style="font-size:20px;font-weight:700;color:#A32D2D">{{ String(r.no).slice(-4) }}</view></view>
        </view>
        <view class="tiny">{{ r.user?.nick }} · 到账 {{ r.amount + r.bonus }} 金币</view>
        <view class="row" style="margin-top:8px">
          <button class="btn ghost" @tap="act('/staff/recharges/'+r.id+'/reject')">拒绝</button>
          <button class="btn" @tap="act('/staff/recharges/'+r.id+'/confirm')">确认收款</button>
        </view>
      </view>
      <view class="card" v-for="o in data.payOrders" :key="'o'+o.id">
        <view class="between"><text class="pill">点单</text><text>{{ o.user?.nick }}</text></view>
        <view class="between" style="margin-top:8px">
          <text style="font-weight:700">¥{{ o.total }}</text>
          <button class="btn" @tap="act('/staff/orders/'+o.id+'/confirm-pay')">确认收款</button>
        </view>
      </view>
      <view class="empty" v-if="!data.recharges.length && !data.payOrders.length">暂无待收款</view>
    </view>

    <view v-if="cur && cur.k==='wdr'">
      <view class="card" v-for="w in data.withdrawals" :key="w.id" style="border-color:#534AB7;background:#EEEDFE">
        <view class="between">
          <text class="pill" style="background:#534AB7;color:#fff">提分单</text>
          <text class="tiny">{{ w.remain }}</text>
        </view>
        <view style="font-size:20px;font-weight:700;margin:8px 0">{{ w.pts }} 分</view>
        <view class="tiny">{{ w.user?.nick }} · {{ String(w.no).slice(-4) }}</view>
        <view class="row" style="margin-top:8px">
          <button class="btn ghost" @tap="act('/staff/withdrawals/'+w.id+'/reject')">驳回</button>
          <button class="btn" @tap="act('/staff/withdrawals/'+w.id+'/grant')">确认发放</button>
        </view>
      </view>
      <view class="empty" v-if="!data.withdrawals.length">暂无待确认提分</view>
    </view>

    <view v-if="cur && cur.k==='making'">
      <view class="card" v-for="o in data.making" :key="o.id">
        <view class="between">
          <text style="font-weight:600">{{ o.user?.nick }}</text>
          <text class="tiny">{{ o.tableName }}</text>
        </view>
        <view class="tiny">{{ (o.items||[]).map(i=>i.name+'×'+i.qty).join('、') }}</view>
        <view class="row" style="margin-top:8px;justify-content:flex-end">
          <button class="btn" @tap="act('/staff/orders/'+o.id+'/finish')">出单</button>
        </view>
      </view>
      <view class="empty" v-if="!data.making.length">暂无制作中</view>
    </view>

    <view class="card" style="background:#FAF9F5">
      <view class="h2">我的今日</view>
      <view class="stat5">
        <view><view class="sb">¥{{ data.stat.amount }}</view><view class="tiny">我经手</view></view>
        <view><view class="sb">{{ data.stat.orders }}</view><view class="tiny">接单</view></view>
        <view><view class="sb">{{ data.stat.verifies }}</view><view class="tiny">核销</view></view>
        <view><view class="sb">{{ data.stat.games }}</view><view class="tiny">录局</view></view>
        <view><view class="sb">{{ data.stat.wds }}</view><view class="tiny">发分</view></view>
      </view>
      <view class="between" v-if="data.shopAmt!=null" style="border-top:1px solid rgba(28,27,25,.12);margin-top:10px;padding-top:9px">
        <text class="tiny">全店今日营业额</text>
        <text class="gold" style="font-weight:700">¥{{ data.shopAmt }}</text>
      </view>
    </view>
    <tab-bar current="todo" />
  </view>
</template>

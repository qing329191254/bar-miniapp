<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import WeekChart from "./WeekChart.vue";

const d = ref<any>(null);
const router = useRouter();
onMounted(async () => {
  d.value = await api("/admin/dashboard");
});

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function go(p: string) {
  router.push("/" + p);
}
const week = computed(() => {
  const rows = [...(d.value?.week || [])].reverse();
  return rows.map((x: any) => ({
    ...x,
    label: String(x.d).slice(8) + "日",
  }));
});
</script>

<template>
  <div v-if="d">
    <div class="hdr">数据看板 <em>{{ d.liability ? "老板视角 · 含资产负债总览" : "店长视角" }}</em></div>
    <div class="card" v-if="d.block" style="background:#FCEBEB;border-color:#E24B4A;padding:10px 12px">
      <b style="font-size:13px;color:#A32D2D">⚠ 门店信息未配置，小程序无法上线</b>
      <button class="btn ghost" style="margin-left:12px" @click="go('content')">去配置</button>
    </div>
    <div class="cards">
      <div class="mtr" style="cursor:pointer" @click="go('orders')">
        <div class="k">今日营业额 ›</div>
        <div class="v">¥{{ fmt(d.shopAmt) }}</div>
        <div class="tiny" style="margin-top:2px">金币 ¥{{ fmt(d.today.coin) }} + 现场 ¥{{ fmt(d.today.offline) }} · 不含充值</div>
      </div>
      <div class="mtr" style="cursor:pointer" @click="go('recharges')">
        <div class="k">今日充值 ›</div>
        <div class="v" style="color:#185FA5">¥{{ fmt(d.today.recharge) }}</div>
        <div class="tiny" style="margin-top:2px;color:#185FA5">资金流入 · 不计营业额</div>
      </div>
      <div class="mtr" style="cursor:pointer" @click="go('orders')">
        <div class="k">订单数 / 进行中 ›</div>
        <div class="v">{{ d.orderCount }} / {{ d.todo.accept + d.todo.pay + d.todo.recharge }}</div>
        <div class="tiny" style="margin-top:2px">待接单 {{ d.todo.accept }} · 待收款 {{ d.todo.pay + d.todo.recharge }}</div>
      </div>
      <div class="mtr" style="cursor:pointer" @click="go('members')">
        <div class="k">会员数 ›</div>
        <div class="v">{{ d.members }}</div>
        <div class="tiny" style="margin-top:2px">点击进入会员列表</div>
      </div>
    </div>

    <div class="dash-grid">
      <div>
        <div class="card">
          <div class="st">待处理 <em>点击跳转对应模块</em></div>
          <div class="todo4">
            <div class="todo-cell" style="background:#FCEBEB;cursor:pointer" @click="go('orders')">
              <b style="font-size:19px;color:#A32D2D">{{ d.todo.accept }}</b>
              <div class="tiny" style="color:#A32D2D">待接单</div>
            </div>
            <div class="todo-cell" style="background:#FAEEDA;cursor:pointer" @click="go('orders')">
              <b style="font-size:19px;color:#BA7517">{{ d.todo.pay }}</b>
              <div class="tiny" style="color:#BA7517">待收款</div>
            </div>
            <div class="todo-cell" style="background:#E6F1FB;cursor:pointer" @click="go('recharges')">
              <b style="font-size:19px;color:#185FA5">{{ d.todo.recharge }}</b>
              <div class="tiny" style="color:#185FA5">待确认充值</div>
            </div>
            <div class="todo-cell" style="background:#F1EFE8;cursor:pointer" @click="go('products')">
              <b style="font-size:19px">{{ d.todo.soldout }}</b>
              <div class="tiny">缺货商品</div>
            </div>
          </div>
          <div class="tiny" style="margin-top:8px">营业额 = 金币消费 + 现场收款，已剔除充值。充值只是资金进入，消费时才转为收入。</div>
        </div>
        <div class="card">
          <div class="st">近 7 日营业额</div>
          <WeekChart :rows="week" />
        </div>
      </div>
      <div>
        <div class="card" v-if="d.liability" style="background:#FCEBEB;border-color:#E24B4A">
          <div class="st" style="color:#A32D2D">资产负债总览 <em style="color:#A32D2D">仅老板可见</em></div>
          <div class="li"><div class="gr"><b>未消费金币</b><span class="tiny" style="color:#A32D2D">真实负债</span></div><b>¥{{ fmt(d.liability.coin) }}</b></div>
          <div class="li"><div class="gr"><b>未清零积分</b><span class="tiny" style="color:#A32D2D">月底清零</span></div><b>{{ fmt(d.liability.point) }}</b></div>
          <div class="li" style="border:none"><div class="gr"><b>未核销卡券</b></div><b>{{ d.liability.cards }} 张</b></div>
        </div>
        <div class="card">
          <div class="st">异常告警</div>
          <div class="li">
            <div class="gr"><b>金币手动调整 {{ d.alerts?.coinAdjust?.length || 0 }} 笔</b>
              <span class="tiny">{{ d.alerts?.coinAdjust?.length ? "待老板审批" : "暂无待审批" }}</span></div>
            <button class="btn ghost" @click="go('coinAdjusts')">{{ d.liability ? "审批" : "查看" }}</button>
          </div>
          <div class="li" style="border:none">
            <div class="gr"><b :style="d.alerts?.deact ? 'color:#A32D2D' : ''">注销申请 {{ d.alerts?.deact || 0 }} 笔</b>
              <span class="tiny">{{ d.alerts?.deact ? "需核对资产结清后执行" : "暂无待处理申请" }}</span></div>
            <button class="btn ghost" @click="go('deactivations')">{{ d.alerts?.deact ? "处理" : "查看" }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

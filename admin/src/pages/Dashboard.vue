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
function fmtDay(dt: Date) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function last7Days() {
  const days: string[] = [];
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const dt = new Date(now);
    dt.setDate(now.getDate() - i);
    days.push(fmtDay(dt));
  }
  return days;
}

const week = computed(() => {
  const map = new Map((d.value?.week || []).map((x: any) => [x.d, x]));
  return last7Days().map((day) => map.get(day) || { d: day, coin: 0, offline: 0 });
});
const coinAdjPending = computed(() => d.value?.alerts?.coinAdjust?.length || 0);
const showCoinAdjPri = computed(() => !!d.value?.liability && coinAdjPending.value > 0);
const showDeactPri = computed(() => (d.value?.alerts?.deact || 0) > 0);
const pointRatio = computed(() => d.value?.alerts?.pointRatio ?? 0);
const pointThreshold = computed(() => d.value?.alerts?.pointThreshold ?? 3);
const pointOver = computed(() => !!d.value?.alerts?.pointOver);
const clearDay = computed(() => {
  const now = new Date();
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  return `${now.getMonth() + 1}-${last} 清零`;
});
</script>

<template>
  <div v-if="d" class="dash-page">
    <div class="hdr">数据看板 <em>{{ d.liability ? "老板视角 · 含资产负债总览" : "店长视角" }}</em></div>
    <div class="card" v-if="d.block" style="background:#FCEBEB;border-color:#E24B4A;padding:10px 12px">
      <b style="font-size:13px;color:#A32D2D">⚠ 门店信息未配置，小程序无法上线</b>
      <button class="btn ghost" style="margin-left:12px" @click="go('content')">去配置</button>
    </div>
    <div class="cards">
      <div class="mtr" style="cursor:pointer" @click="go('dailyBiz')">
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
      <div class="dash-main-col">
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
        <div class="card chart-card">
          <div class="st">近 7 日营业额 <em>周五六为峰值</em></div>
          <WeekChart :rows="week" />
        </div>
      </div>
      <div>
        <div class="card" v-if="d.liability" style="background:#FCEBEB;border-color:#E24B4A">
          <div class="st" style="color:#A32D2D">资产负债总览</div>
          <div class="li li-link" @click="go('liabCoin')">
            <div class="gr"><b>未消费金币 ›</b><span class="tiny" style="color:#A32D2D">真实负债，用户随时可消费</span></div>
            <b>¥{{ fmt(d.liability.coin) }}</b>
          </div>
          <div class="li li-link" @click="go('liabPoint')">
            <div class="gr"><b>未清零积分 ›</b><span class="tiny" style="color:#A32D2D">{{ clearDay }}</span></div>
            <b>{{ fmt(d.liability.point) }}</b>
          </div>
          <div class="li li-link" style="border:none" @click="go('liabCard')">
            <div class="gr"><b>未核销卡券 ›</b><span class="tiny" style="color:#A32D2D">含 {{ d.liability.treasure || 0 }} 张宝箱卡</span></div>
            <b>{{ d.liability.cards }} 张</b>
          </div>
        </div>
        <div class="card">
          <div class="st">异常告警 <em>自动推送</em></div>
          <div class="li li-link" @click="go('alertPoint')">
            <div class="gr">
              <b :style="pointOver ? 'color:#A32D2D' : ''">店员录入积分异常 ›</b>
              <span class="tiny">今日总量为均值 {{ pointRatio }} 倍（阈值 {{ pointThreshold }} 倍）</span>
            </div>
            <button class="btn sm ghost" @click.stop="go('alertPoint')">查看</button>
          </div>
          <div class="li li-link" @click="go('coinAdjusts')">
            <div class="gr"><b>金币手动调整 {{ d.alerts?.coinAdjust?.length || 0 }} 笔 ›</b>
              <span class="tiny">{{ d.alerts?.coinAdjust?.length ? "待老板审批" : "暂无待审批" }}</span></div>
            <button class="btn sm" :class="{ ghost: !showCoinAdjPri }" @click.stop="go('coinAdjusts')">{{ showCoinAdjPri ? "审批" : "查看" }}</button>
          </div>
          <div class="li li-link" style="border:none" @click="go('deactivations')">
            <div class="gr"><b :style="d.alerts?.deact ? 'color:#A32D2D' : ''">注销申请 {{ d.alerts?.deact || 0 }} 笔 ›</b>
              <span class="tiny">{{ d.alerts?.deact ? "需核对资产结清后执行" : "暂无待处理申请" }}</span></div>
            <button class="btn sm" :class="{ ghost: !showDeactPri }" @click.stop="go('deactivations')">{{ showDeactPri ? "处理" : "查看" }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

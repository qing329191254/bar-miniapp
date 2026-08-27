<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";

const OD: Record<string, [string, string]> = {
  PENDING_ACCEPT: ["待接单", "#BA7517"],
  PENDING_PAY: ["待付款", "#185FA5"],
  MAKING: ["制作中", "#534AB7"],
  FINISHED: ["已完成", "#3B6D11"],
  CANCELLED: ["已取消", "#9C9A93"],
  CLOSED: ["已关闭", "#9C9A93"],
  REFUNDED: ["已退款", "#A32D2D"],
};
const RC: Record<string, [string, string]> = {
  PENDING_PAY: ["待付款", "#185FA5"],
  PAID: ["已到账", "#3B6D11"],
  CLOSED: ["已关闭", "#9C9A93"],
  CANCELLED: ["已取消", "#9C9A93"],
};
const WD: Record<string, [string, string]> = {
  PENDING_CONFIRM: ["待确认", "#BA7517"],
  GRANTED: ["已发放", "#3B6D11"],
  REJECTED: ["已驳回", "#A32D2D"],
  CANCELLED: ["已取消", "#9C9A93"],
  CLOSED_TIMEOUT: ["超时关闭", "#A32D2D"],
};

const route = useRoute();
const coll = computed(() => String(route.params.coll || route.path.replace("/", "")));
const rows = ref<any[]>([]);
const members = ref<any[]>([]);
const status = ref("");

const titles: Record<string, [string, string]> = {
  orders: ["订单记录", "接单扣款 · 到店付在待办确认"],
  recharges: ["充值记录", "资金流入不计营业额"],
  withdrawals: ["提分单管理", "本页只读 · 发放在商家移动端当面完成"],
  gameRecords: ["对局记录查询", "作废需店长以上"],
};

onMounted(load);
watch(() => route.fullPath, () => { status.value = ""; load(); });

async function load() {
  const c = coll.value;
  rows.value = await api("/admin/" + c);
  if (!members.value.length) members.value = await api("/admin/members");
}
function nick(uid: number) {
  return members.value.find((x) => x.id === uid)?.nick || uid;
}
function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pill(map: Record<string, [string, string]>, s: string) {
  return map[s] || [s, "#9C9A93"];
}
const shown = computed(() => {
  let list = rows.value || [];
  if (status.value) list = list.filter((r) => r.status === status.value);
  return list;
});
const pendingWdr = computed(() =>
  coll.value === "withdrawals" ? rows.value.filter((w) => w.status === "PENDING_CONFIRM") : [],
);
</script>

<template>
  <div>
    <div class="hdr">{{ titles[coll]?.[0] || coll }} <em>{{ titles[coll]?.[1] }}</em></div>
    <div class="note rd" v-if="coll==='withdrawals'">本页只读，不提供发放入口。提分兑付必须由店员在商家移动端「待办」当面完成。</div>
    <div class="card" v-if="pendingWdr.length" style="background:#FAEEDA;border-color:#BA7517">
      <div class="st" style="color:#BA7517">待确认提分单 {{ pendingWdr.length }} 张 · 发放在商家移动端完成</div>
      <div class="li" v-for="w in pendingWdr" :key="w.id">
        <div class="gr"><b>{{ w.no }} · {{ fmt(w.pts) }} 分</b><span class="tiny">{{ nick(w.uid) }} · {{ w.at || w.created }}</span></div>
        <span class="tiny">此处无操作按钮是刻意设计</span>
      </div>
    </div>
    <div class="row" style="gap:6px;margin-bottom:10px;flex-wrap:wrap" v-if="coll==='orders'">
      <span class="chip" :class="{ on: !status }" @click="status=''">全部 {{ rows.length }}</span>
      <span class="chip" v-for="(v,k) in OD" :key="k" :class="{ on: status===k }" @click="status = status===k ? '' : k">{{ v[0] }}</span>
    </div>
    <div class="card" style="padding:0;overflow-x:auto">
      <table class="tb2" v-if="coll==='orders'">
        <thead>
          <tr><th>单号</th><th>会员</th><th>桌台</th><th>金额</th><th>支付</th><th>状态</th><th>时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown.slice(0,80)" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ r.nick || nick(r.uid) }}</td>
          <td class="tiny">{{ r.tableName || "—" }}</td>
          <td><b>{{ r.total }}</b></td>
          <td class="tiny">{{ r.payType === "COIN" ? "金币" : "到店付" }}</td>
          <td><span class="pill" :style="{ color: pill(OD, r.status)[1] }">{{ pill(OD, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at }}</td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else-if="coll==='recharges'">
        <thead>
          <tr><th>单号</th><th>会员</th><th>金额</th><th>赠送</th><th>状态</th><th>时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown.slice(0,80)" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ nick(r.uid) }}</td>
          <td>¥{{ r.amount }}</td>
          <td class="tiny">{{ r.bonus }}</td>
          <td><span class="pill" :style="{ color: pill(RC, r.status)[1] }">{{ pill(RC, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at || r.created }}</td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else-if="coll==='withdrawals'">
        <thead>
          <tr><th>单号</th><th>会员</th><th>积分数</th><th>状态</th><th>提交时间</th><th>发放时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown.slice(0,80)" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ nick(r.uid) }}</td>
          <td>{{ fmt(r.pts) }}</td>
          <td><span class="pill" :style="{ color: pill(WD, r.status)[1] }">{{ pill(WD, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at || r.created }}</td>
          <td class="tiny">{{ r.grantAt || "—" }}</td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else>
        <thead>
          <tr><th>项目</th><th>桌台</th><th>时间</th><th>人数</th><th>积分</th><th>碎片</th><th>录入</th><th>状态</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown.slice(0,80)" :key="r.id">
          <td><b>{{ r.pname }}</b></td>
          <td>{{ r.table || "—" }}</td>
          <td class="tiny">{{ r.time }}</td>
          <td>{{ (r.players || []).length }}</td>
          <td>{{ fmt((r.players || []).reduce((s: number, p: any) => s + (p.pts || 0), 0)) }}</td>
          <td>{{ fmt((r.players || []).reduce((s: number, p: any) => s + (p.sh || 0), 0)) }}</td>
          <td class="tiny">{{ r.op }}</td>
          <td><span class="pill">{{ r.status === "VOID" ? "已作废" : "正常" }}</span></td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

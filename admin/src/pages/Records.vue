<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";

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
const rowTotal = ref(0);
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const pendingItems = ref<any[]>([]);
const members = ref<any[]>([]);
const status = ref("");

const titles: Record<string, [string, string]> = {
  recharges: ["充值记录", "资金流入不计营业额"],
  withdrawals: ["提分单管理", "本页只读 · 发放在商家移动端当面完成"],
  gameRecords: ["对局记录查询", "作废需店长以上"],
};

onMounted(load);
watch(() => route.fullPath, () => { status.value = ""; tablePage.value = 1; load(); });
watch([tablePage, tablePageSize], () => load());
watch(status, () => { tablePage.value = 1; load(); });

async function load() {
  const c = coll.value;
  const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value));
  if (status.value) params.set("status", status.value);
  const res = await api<any>(`/admin/${c}?${params}`);
  rows.value = res.items || [];
  rowTotal.value = res.total ?? rows.value.length;
  pendingItems.value = res.pendingItems || [];
  if (!members.value.length) members.value = await api("/admin/members?pageSize=0");
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
const shown = computed(() => rows.value || []);
const pendingWdr = computed(() =>
  coll.value === "withdrawals" ? pendingItems.value : [],
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
    <div class="card" style="padding:0;overflow-x:auto">
      <table class="tb2" v-if="coll==='recharges'" data-cols="llcccc">
        <thead>
          <tr><th>单号</th><th>会员</th><th>金额</th><th>赠送</th><th>状态</th><th>时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ nick(r.uid) }}</td>
          <td>¥{{ r.amount }}</td>
          <td class="tiny">{{ r.bonus }}</td>
          <td><span class="pill" :style="{ color: pill(RC, r.status)[1] }">{{ pill(RC, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at || r.created }}</td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else-if="coll==='withdrawals'" data-cols="llcccc">
        <thead>
          <tr><th>单号</th><th>会员</th><th>积分数</th><th>状态</th><th>提交时间</th><th>发放时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ nick(r.uid) }}</td>
          <td>{{ fmt(r.pts) }}</td>
          <td><span class="pill" :style="{ color: pill(WD, r.status)[1] }">{{ pill(WD, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at || r.created }}</td>
          <td class="tiny">{{ r.grantAt || "—" }}</td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else data-cols="lccccccl">
        <thead>
          <tr><th>项目</th><th>桌台</th><th>时间</th><th>人数</th><th>积分</th><th>碎片</th><th>录入</th><th>状态</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.pname }}</b><div v-if="r.round" class="tiny">{{ r.round }}</div></td>
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
      <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
    </div>
  </div>
</template>

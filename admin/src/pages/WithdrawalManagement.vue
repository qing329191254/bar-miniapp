<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";

const rows = ref<any[]>([]);
const rowTotal = ref(0);
const statusCounts = ref<Record<string, number>>({});
const tablePage = ref(1);
const tablePageSize = ref(50);
const members = ref<any[]>([]);
const status = ref("");
const now = ref(Date.now());
let timer: number | undefined;

const STATUS: Record<string, [string, string]> = {
  PENDING_CONFIRM: ["待确认", "#BA7517"], GRANTED: ["已发放", "#3B6D11"],
  REJECTED: ["已驳回", "#A32D2D"], CANCELLED: ["已取消", "#6B6A65"], CLOSED_TIMEOUT: ["超时关闭", "#A32D2D"],
};
function fmt(n: number) { return Number(n || 0).toLocaleString("en-US"); }
function nick(uid: number) { return members.value.find((m) => m.id === uid)?.nick || "—"; }
function stamp(row: any) { return row.at || row.created || ""; }
function elapsed(row: any) {
  const start = new Date(stamp(row).replace(/-/g, "/")).getTime();
  if (!start || row.status === "PENDING_CONFIRM") return "—";
  const end = new Date((row.grantAt || row.closedAt || stamp(row)).replace(/-/g, "/")).getTime();
  const min = Math.max(0, Math.round((end - start) / 60000));
  return min < 60 ? `${min} 分钟` : `${Math.floor(min / 60)} 小时 ${min % 60} 分`;
}
function remaining(row: any) {
  if (!row.expireAt) return "—";
  const sec = Math.max(0, Math.ceil((Number(row.expireAt) - now.value) / 1000));
  return sec ? `${Math.floor(sec / 60)} 分 ${sec % 60} 秒` : "已超时";
}
const pendingItems = ref<any[]>([]);
const filtered = computed(() => rows.value);
const pending = computed(() => pendingItems.value);
const granted = computed(() => filtered.value.filter((r) => r.status === "GRANTED"));
const closed = computed(() => filtered.value.filter((r) => r.status !== "PENDING_CONFIRM"));
const grantedPoints = computed(() => granted.value.reduce((sum, r) => sum + Number(r.pts || 0), 0));
const rejected = computed(() => statusCounts.value.REJECTED || 0);
const timedout = computed(() => statusCounts.value.CLOSED_TIMEOUT || 0);
const statusCount = (key: string) => statusCounts.value[key] || 0;

async function load() {
  const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value));
  if (status.value) params.set("status", status.value);
  const [res, users] = await Promise.all([
    api<any>(`/admin/withdrawals?${params}`),
    members.value.length ? Promise.resolve(members.value) : api<any[]>("/admin/members?pageSize=0"),
  ]);
  rows.value = (res.items || []).sort((a: any, b: any) => String(stamp(b)).localeCompare(String(stamp(a))));
  rowTotal.value = res.total ?? rows.value.length;
  statusCounts.value = res.statusCounts || {};
  pendingItems.value = res.pendingItems || [];
  members.value = users;
}

watch(status, () => { tablePage.value = 1; load(); });
watch([tablePage, tablePageSize], () => load());
onMounted(() => { load(); timer = window.setInterval(() => { now.value = Date.now(); }, 1000); });
</script>

<template>
  <div>
    <div class="hdr">提分单管理 <em>共 {{ rows.length }} 张 · 当前筛出 {{ filtered.length }} 张<span v-if="pending.length"> · 待确认 {{ pending.length }} 张</span></em></div>
    <div class="note rd"><b>本页只读，不提供发放与确认入口。</b>提分必须由店员在商家移动端当面确认，后台用于查询单据与查看处理情况。</div>

    <div class="cards withdrawal-kpis">
      <div class="mtr"><div class="k">已发放积分</div><div class="v">{{ fmt(grantedPoints) }}</div><div class="tiny">{{ granted.length }} 张已发放</div></div>
      <div class="mtr"><div class="k">驳回率</div><div class="v">{{ closed.length ? (rejected / closed.length * 100).toFixed(1) : 0 }}%</div><div class="tiny">{{ rejected }} / {{ closed.length }} 张已终结</div></div>
      <div class="mtr"><div class="k">超时关闭</div><div class="v" :style="{ color: timedout ? '#A32D2D' : '' }">{{ timedout }}</div><div class="tiny">超时后冻结积分全额退回</div></div>
      <div class="mtr"><div class="k">待确认</div><div class="v" :style="{ color: pending.length ? '#BA7517' : '' }">{{ pending.length }}</div><div class="tiny">发放在商家移动端完成</div></div>
    </div>

    <div class="card"><div class="st">状态分布 <em>点击快速筛选</em></div><div class="row" style="flex-wrap:wrap">
      <button class="chip" :class="{ on: !status }" @click="status=''">全部 {{ rows.length }}</button>
      <button v-for="([key, value]) in Object.entries(STATUS)" :key="key" class="chip" :class="{ on: status === key }" @click="status = status === key ? '' : key">{{ value[0] }} {{ statusCount(key) }}</button>
    </div></div>

    <div v-if="pending.length" class="card pending-card">
      <div class="st" style="color:#BA7517">待确认提分单 <em style="color:#BA7517">不受上方筛选影响，仅供掌握积压</em></div>
      <div v-for="row in pending" :key="row.id" class="li">
        <div class="gr"><b>{{ row.no.slice(0, -4) }}<span style="color:#A32D2D">{{ row.no.slice(-4) }}</span> · {{ fmt(row.pts) }} 分</b><span class="tiny">{{ nick(row.uid) }} · 提交 {{ stamp(row) }}</span></div>
        <span class="tiny" style="color:#A32D2D">剩 {{ remaining(row) }}</span>
      </div>
      <div class="tiny" style="color:#BA7517;margin-top:7px">顾客到吧台报单号末四位，店员在移动端待办中核对后当面发放；这里没有操作按钮是刻意设计。</div>
    </div>

    <div class="card" style="padding:0;overflow:auto"><table class="tb2" data-cols="llcccccc">
      <thead><tr><th>提分单号</th><th>会员</th><th>数量</th><th>状态</th><th>提交时间</th><th>等待时长</th><th>经手员工</th><th>备注</th></tr></thead>
      <tbody><tr v-for="row in filtered" :key="row.id" :style="row.status === 'PENDING_CONFIRM' ? 'background:#FDF8EE' : ''">
        <td><b>{{ row.no }}</b></td><td>{{ nick(row.uid) }}</td><td><b>{{ fmt(row.pts) }}</b></td>
        <td><span class="pill" :style="{ color: STATUS[row.status]?.[1] }">{{ STATUS[row.status]?.[0] || row.status }}</span></td>
        <td class="tiny">{{ stamp(row) }}</td><td class="tiny">{{ elapsed(row) }}</td>
        <td>{{ row.grantBy ? nick(row.grantBy) : row.rejectBy ? nick(row.rejectBy) : '—' }}</td>
        <td class="tiny">{{ row.rejectRemark || (row.status === 'CLOSED_TIMEOUT' ? '超时未确认，积分已退回' : '—') }}</td>
      </tr><tr v-if="!filtered.length"><td colspan="8" class="empty">当前筛选条件下无提分单</td></tr></tbody>
    </table>
    <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
    </div>
    <div class="note">状态机：待确认 → 已发放 / 已驳回 / 已取消 / 超时关闭。除已发放外，其余终态都会将冻结积分全额退回可用积分。</div>
  </div>
</template>

<style scoped>
.withdrawal-kpis { grid-template-columns:repeat(4, minmax(0, 1fr)); }
.pending-card { background:#FAEEDA; border-color:#BA7517; }
.empty { text-align:center; color:var(--ink3); padding:26px !important; }
@media (max-width:960px) { .withdrawal-kpis { grid-template-columns:1fr 1fr; } }
</style>

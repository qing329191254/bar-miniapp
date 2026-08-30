<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

const router = useRouter();
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");

const ST: Record<string, string> = {
  PENDING: "gold",
  REJECTED: "red",
  DONE: "grey",
};
const ST_LABEL: Record<string, string> = {
  PENDING: "待处理",
  REJECTED: "已驳回",
  DONE: "已注销",
};

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

function memberLabel(uid: number) {
  const m = data.value?.members?.[uid];
  return m ? `${m.nick} ${m.tail}`.trim() : "（会员已删除）";
}

function memberNo(uid: number) {
  return data.value?.members?.[uid]?.no || "—";
}

function openDetail(id: number) {
  router.push(`/deactivations/${id}`);
}

const list = computed(() => data.value?.list || []);
const summary = computed(
  () => data.value?.summary || { total: 0, pending: 0, rejected: 0, done: 0, refundTotal: 0 },
);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    data.value = await api("/admin/deactivation?pageSize=0");
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="hdr deact-hdr">
      <span class="hdr-title">注销申请处理</span>
      <em v-if="data" class="hdr-note">共 {{ summary.total }} 条 · 待处理 {{ summary.pending }} 条</em>
    </div>

    <AppAsyncPage :loading="loading" :data="data" :err="err" :skeleton="{ showHeader: false, showFilter: false, tableCols: 7 }" @retry="load">
      <div class="g4 kpi-row">
        <div class="mtr">
          <div class="k">待处理</div>
          <div class="v" :class="{ alert: summary.pending }">{{ summary.pending }}</div>
          <div class="tiny">需核对资产结清</div>
        </div>
        <div class="mtr">
          <div class="k">待退本金</div>
          <div class="v">¥{{ fmt(summary.refundTotal) }}</div>
          <div class="tiny">按实时余额合计</div>
        </div>
        <div class="mtr">
          <div class="k">已驳回</div>
          <div class="v mut">{{ summary.rejected }}</div>
          <div class="tiny">须填明原因</div>
        </div>
        <div class="mtr">
          <div class="k">已注销</div>
          <div class="v mut">{{ summary.done }}</div>
          <div class="tiny">基础账号信息将保留备查</div>
        </div>
      </div>

      <div class="card table-card">
        <table class="tb2 deact-table">
          <thead>
            <tr>
              <th style="width:14%">申请单号</th>
              <th style="width:14%">会员</th>
              <th style="width:20%">申请原因</th>
              <th style="width:13%">申请时间</th>
              <th style="width:13%">当前本金</th>
              <th style="width:11%">状态</th>
              <th style="width:15%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in list" :key="d.id" :class="{ 'row-pending': d.status === 'PENDING' }">
              <td><b>{{ d.no }}</b></td>
              <td>
                {{ memberLabel(d.uid) }}
                <div class="tiny">{{ memberNo(d.uid) }}</div>
              </td>
              <td class="mut">{{ d.reason || "—" }}</td>
              <td class="mut">{{ d.created }}</td>
              <td>
                <span v-if="d.status === 'DONE'" class="mut">已退 ¥{{ fmt(d.refunded || 0) }}</span>
                <b v-else :class="{ alert: d.live?.coinP }">¥{{ fmt(d.live?.coinP || 0) }}</b>
              </td>
              <td>
                <span class="pill" :class="ST[d.status] || 'grey'">{{ ST_LABEL[d.status] || d.status }}</span>
              </td>
              <td>
                <button class="btn sm" :class="{ pri: d.status === 'PENDING' }" @click="openDetail(d.id)">
                  {{ d.status === "PENDING" ? "核对处理" : "查看详情" }}
                </button>
              </td>
            </tr>
            <tr v-if="!list.length">
              <td colspan="7" class="table-empty">暂无注销申请</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="side-note warn multi">
        <div class="side-note-body">
          <p><b>注销操作不可撤销，请分两步处理：</b>顾客从小程序提交申请后，账号与资产仍保持原状；店长需先核对并结清金币、积分和卡券，再在本页确认注销。申请处理完成前，相关资产仍会计入门店负债。</p>
        </div>
      </div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.deact-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  text-align: right;
  pointer-events: auto;
  white-space: normal;
}
.kpi-row {
  margin-bottom: 12px;
}
.g4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.table-card {
  padding: 0;
  overflow: auto;
}
.deact-table :is(th, td):nth-child(6),
.deact-table :is(th, td):nth-child(7) {
  text-align: center;
}
.row-pending {
  background: #fdf8ee;
}
.alert {
  color: var(--red);
}
.mut {
  color: var(--ink3);
}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}
.pill.gold {
  background: var(--goldbg);
  color: var(--gold);
}
.pill.red {
  background: var(--redbg);
  color: var(--red);
}
.pill.grey {
  background: #f5f4f0;
  color: #6b6a65;
}
@media (max-width: 900px) {
  .g4 {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

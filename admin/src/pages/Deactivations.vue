<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";

const router = useRouter();
const data = ref<any>(null);
const loading = ref(true);
const tablePage = ref(1);
const tablePageSize = ref(50);
const err = ref("");

const ST: Record<string, [string, string, string]> = {
  PENDING: ["待处理", "#BA7517", "#FAEEDA"],
  REJECTED: ["已驳回", "#A32D2D", "#FCEBEB"],
  DONE: ["已注销", "#6B6A65", "#F5F4F0"],
};

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
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
const listTotal = computed(() => data.value?.listTotal ?? 0);
const summary = computed(() => data.value?.summary || { total: 0, pending: 0, rejected: 0, done: 0, refundTotal: 0 });

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const params = pageQs(tablePage.value, tablePageSize.value);
    data.value = await api(`/admin/deactivation?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

watch([tablePage, tablePageSize], () => load());

onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">注销申请处理</span>
      <em v-if="data" class="hdr-note">共 {{ summary.total }} 条 · 待处理 {{ summary.pending }} 条</em>
    </div>

    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
      <div class="cards">
        <div class="mtr">
          <div class="k">待处理</div>
          <div class="v" :style="{ color: summary.pending ? '#A32D2D' : undefined }">{{ summary.pending }}</div>
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
          <div class="tiny">账号壳保留可追溯</div>
        </div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even tb-deact" data-cols="lllclcc">
          <thead>
            <tr>
              <th>申请单号</th><th>会员</th><th>申请原因</th><th>申请时间</th><th>当前本金</th><th>状态</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in list" :key="d.id" :class="{ 'row-pending': d.status === 'PENDING' }">
              <td><b>{{ d.no }}</b></td>
              <td>{{ memberLabel(d.uid) }}<div class="tiny">{{ memberNo(d.uid) }}</div></td>
              <td class="mut">{{ d.reason || "—" }}</td>
              <td class="mut">{{ d.created }}</td>
              <td>
                <span v-if="d.status === 'DONE'" class="mut">已退 ¥{{ fmt(d.refunded || 0) }}</span>
                <b v-else :style="{ color: d.live?.coinP ? '#A32D2D' : 'var(--ink3)' }">¥{{ fmt(d.live?.coinP || 0) }}</b>
              </td>
              <td>
                <span class="pill" :style="pillStyle(ST[d.status] || [d.status, '#6B6A65', '#F5F4F0'])">{{ ST[d.status]?.[0] || d.status }}</span>
              </td>
              <td>
                <button class="btn sm" :class="{ pri: d.status === 'PENDING' }" @click="openDetail(d.id)">
                  {{ d.status === "PENDING" ? "核对处理" : "查看详情" }}
                </button>
              </td>
            </tr>
            <tr v-if="!list.length">
              <td colspan="7" class="tiny empty-row">暂无注销申请</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="listTotal" />
      </div>

      <div class="note rd">
        <b>注销为不可逆操作，故设计为两段式：</b>C 端提交只置标记（DEACTIVATE_PENDING），账号仍可正常消费、资产仍计入店里的真实负债；真正执行由店长在本页核对资产结清后完成。<b>申请一提交就把人从负债里剔除是错的</b>——钱还没退，负债不会因为顾客提了个申请就消失。
      </div>
    </template>
  </div>
</template>

<style scoped>
.table-card {
  padding: 0;
  overflow: auto;
}
.tb-deact {
  table-layout: fixed;
}
.row-pending {
  background: #fdf8ee;
}
.empty-row {
  text-align: center;
  padding: 26px;
  color: var(--ink3);
}
</style>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, DEFAULT_PAGE_SIZE } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppPagination from "../components/AppPagination.vue";
import { usePagination } from "../composables/usePagination";
import { showToast } from "../composables/useToast";
import { csvFilename, downloadXlsx } from "../exportCsv";

type LogRow = {
  t: string;
  op: string;
  role: string;
  action: string;
  detail: string;
  uid?: number | null;
};

const rows = ref<LogRow[]>([]);
const loading = ref(true);
const err = ref("");

const logsPg = usePagination(rows, DEFAULT_PAGE_SIZE);
const shown = logsPg.items;
const tablePage = logsPg.page;
const tablePageSize = logsPg.pageSize;
const rowTotal = logsPg.total;

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<LogRow[]>("/admin/logs?pageSize=0");
    rows.value = Array.isArray(data) ? data : [];
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function exportLogs() {
  if (!rows.value.length) {
    showToast("暂无可导出的日志", true);
    return;
  }
  downloadXlsx(
    csvFilename("操作日志", "全部记录", "xlsx"),
    ["时间", "操作人", "角色", "类型", "内容"],
    rows.value.map((row) => [row.t, row.op, row.role, row.action, row.detail]),
    { colWidths: [20, 14, 12, 18, 48], textCols: [0, 1, 2, 3, 4], sheetName: "操作日志" },
  );
  showToast(`已导出 ${rows.value.length} 条操作日志`);
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'table', showFilter: true, metrics: 0, tableCols: 6, showNote: false }" @retry="load">
    <div>
      <div class="hdr logs-hdr">
        <span class="hdr-title">操作日志</span>
        <em class="hdr-note">仅老板可查看 · 记录长期保留</em>
      </div>
      <div class="toolbar row">
        <button class="btn sm" @click="exportLogs">导出日志</button>
      </div>

      <div class="card tb-wrap">
        <table class="tb2">
          <thead>
            <tr>
              <th style="width: 14%">时间</th>
              <th style="width: 14%">操作人</th>
              <th style="width: 18%">类型</th>
              <th style="width: 54%">内容</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in shown" :key="`${row.t}-${row.action}-${i}`">
              <td class="tiny">{{ row.t }}</td>
              <td>
                {{ row.op }}
                <div class="tiny role">{{ row.role }}</div>
              </td>
              <td>
                <span class="pill action-pill">{{ row.action }}</span>
              </td>
              <td class="tiny">{{ row.detail }}</td>
            </tr>
            <tr v-if="!shown.length">
              <td colspan="4" class="empty-row">暂无日志</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.logs-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.tb-wrap { padding: 0; overflow: auto; }
.tiny { font-size: 11px; color: var(--ink3); }
.role { margin-top: 2px; }
.action-pill { background: #E6F1FB; color: var(--blue); }
.empty-row { text-align: center; color: var(--ink3); padding: 24px; font-size: 12px; }
</style>

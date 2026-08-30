<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

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
const msg = ref("");

const total = computed(() => rows.value.length);

function notify(text: string) {
  msg.value = text;
  window.setTimeout(() => {
    if (msg.value === text) msg.value = "";
  }, 2200);
}

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

function exportDemo() {
  notify("已导出 Excel（演示）");
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :error="err" @retry="load">
    <div>
      <div class="hdr">操作日志 <em>仅老板可见 · 永久保留不可删除</em></div>
      <p v-if="msg" class="notice">{{ msg }}</p>

      <div class="toolbar row">
        <button class="btn sm" @click="exportDemo">导出</button>
        <span class="total">共 {{ total }} 条</span>
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
            <tr v-for="(row, i) in rows" :key="`${row.t}-${row.action}-${i}`">
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
            <tr v-if="!rows.length">
              <td colspan="4" class="empty-row">暂无日志</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.notice { color: var(--green); font-size: 12px; margin-bottom: 8px; }
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.total { margin-left: auto; font-size: 11px; color: var(--ink3); }
.tb-wrap { padding: 0; overflow: auto; }
.tiny { font-size: 11px; color: var(--ink3); }
.role { margin-top: 2px; }
.action-pill { background: #E6F1FB; color: var(--blue); }
.empty-row { text-align: center; color: var(--ink3); padding: 24px; font-size: 12px; }
</style>

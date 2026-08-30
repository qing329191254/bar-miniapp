<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppDateInput from "../components/AppDateInput.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";
import { csvFilename, downloadExcelTable } from "../exportCsv";

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];

const STATUS: Record<string, [string, string, string]> = {
  PENDING_CONFIRM: ["待确认", "#BA7517", "#FAEEDA"],
  GRANTED: ["已发放", "#3B6D11", "#EAF3DE"],
  REJECTED: ["已驳回", "#A32D2D", "#FCEBEB"],
  CANCELLED: ["已取消", "#6B6A65", "#F5F4F0"],
  CLOSED_TIMEOUT: ["超时关闭", "#A32D2D", "#FCEBEB"],
};

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

const preset = ref("all");
const dateFrom = ref("");
const dateTo = ref("");
const opUid = ref(0);
const status = ref("");
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const exporting = ref(false);
const now = ref(Date.now());
let timer: number | undefined;

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function statusPill(s: string) {
  return STATUS[s] || [s, "#6B6A65", "#F5F4F0"];
}
function memberLabel(o: { nick?: string; tail?: string }) {
  const nick = o.nick || "—";
  const tail = o.tail ? ` ${o.tail}` : "";
  return `${nick}${tail}`.trim();
}
function stamp(row: any) {
  return row.at || row.created || "—";
}
function noHead(no: string) {
  return no.length > 4 ? no.slice(0, 4) : no;
}
function noTail(no: string) {
  return no.length > 4 ? no.slice(-4) : "";
}
function parseTimeMin(s: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(String(s || ""));
  if (!m) return null;
  return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]).getTime() / 60000;
}
function durTxt(mins: number | null | undefined) {
  if (mins == null || !Number.isFinite(mins)) return "—";
  const n = Math.max(0, Math.round(mins));
  if (n < 60) return `${n} 分`;
  const h = Math.floor(n / 60);
  const m = n % 60;
  return `${h} 小时${m ? ` ${m} 分` : ""}`;
}
function wdrWait(row: any) {
  const t0 = parseTimeMin(row.at || row.created || "");
  if (t0 == null) return null;
  if (row.status === "PENDING_CONFIRM") {
    return Math.max(0, now.value / 60000 - t0);
  }
  const t1 = parseTimeMin(row.grantAt || row.closedAt || "");
  if (t1 == null) return null;
  return Math.max(0, t1 - t0);
}
function remaining(row: any) {
  if (!row.expireAt) return "—";
  const sec = Math.max(0, Math.ceil((Number(row.expireAt) - now.value) / 1000));
  return sec ? `${Math.floor(sec / 60)} 分 ${sec % 60} 秒` : "已超时";
}
function noteText(row: any) {
  if (row.status === "REJECTED") return row.rejectRemark || "—";
  if (row.status === "CLOSED_TIMEOUT") return `超时 30 分钟未确认，${fmt(row.pts)} 分已全额退回`;
  if (row.status === "CANCELLED") return "顾客自行取消，已全额退回";
  return "—";
}
function exportFilename(rangeLabel: string) {
  return csvFilename("提分单", rangeLabel, "xls");
}
async function exportRows() {
  if (exporting.value) return;
  exporting.value = true;
  try {
    const params = new URLSearchParams(
      pageQs(1, 0, {
        preset: preset.value,
        opUid: opUid.value,
        status: status.value,
      }),
    );
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    const res = await api<any>(`/admin/withdrawals-page?${params}`);
    const list: any[] = res.rows || [];
    if (!list.length) {
      showToast("当前筛选条件下无数据可导出", true);
      return;
    }
    const headers = ["提分单号", "会员", "数量", "状态", "提交时间", "等待时长", "经手员工", "备注"];
    const body = list.map((row) => [
      row.no || "",
      memberLabel(row),
      Number(row.pts ?? 0),
      statusPill(row.status)[0],
      stamp(row),
      durTxt(wdrWait(row)),
      row.opName ? `${row.opName}${row.opRole ? ` · ${row.opRole}` : ""}` : "—",
      noteText(row),
    ]);
    downloadExcelTable(exportFilename(res.rangeLabel || ""), headers, body, {
      colWidths: [95, 90, 55, 60, 115, 55, 90, 220],
      textCols: [0, 4],
      numberCols: [2],
      sheetName: "提分单",
    });
    showToast(`已导出 ${list.length} 条提分单`);
  } catch (e: any) {
    showToast(e?.message || "导出失败", true);
  } finally {
    exporting.value = false;
  }
}
function setPreset(p: string) {
  if (p !== "custom" && p === preset.value) return;
  preset.value = p;
  if (p !== "custom") {
    dateFrom.value = "";
    dateTo.value = "";
    load(true);
  }
}
function onCustomDateChange() {
  if (preset.value === "custom" && dateFrom.value && dateTo.value) load(true);
}
function toggleStatus(key: string) {
  status.value = status.value === key ? "" : key;
  load(true);
}

const summary = computed(() => data.value?.summary || {});
const byStatus = computed(() => data.value?.byStatus || {});
const pending = computed(() => data.value?.pending || []);
const rows = computed(() => data.value?.rows || []);
const rowTotal = computed(() => data.value?.rowTotal ?? 0);
const hdrNote = computed(() => {
  if (!data.value) return "";
  const parts = [`共 ${data.value.totalAll} 张`, `当前筛出 ${data.value.filtered} 张`];
  if (pending.value.length) parts.push(`待确认 ${pending.value.length} 张`);
  return parts.join(" · ");
});
const tableSummary = computed(() => {
  if (!rows.value.length) return null;
  const uids = new Set(rows.value.map((r: any) => r.uid));
  const totalPts = rows.value.reduce((s: number, r: any) => s + Number(r.pts || 0), 0);
  return { members: uids.size, totalPts, grantedPts: summary.value.grantedPts || 0 };
});
const timeoutCardStyle = computed(() =>
  summary.value.timeout > 0
    ? { background: "var(--redbg)", borderColor: "#E24B4A" }
    : { background: "var(--greenbg)", borderColor: "#97C459" },
);
const timeoutTone = computed(() => (summary.value.timeout > 0 ? "var(--red)" : "var(--green)"));
const rejectTone = computed(() =>
  summary.value.closedCount && summary.value.rejected / summary.value.closedCount > 0.2 ? "var(--red)" : "var(--ink)",
);

async function load(resetPage = false) {
  if (resetPage) tablePage.value = 1;
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(
      pageQs(tablePage.value, tablePageSize.value, {
        preset: preset.value,
        opUid: opUid.value,
        status: status.value,
      }),
    );
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/withdrawals-page?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  timer = window.setInterval(() => { now.value = Date.now(); }, 1000);
});
onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
watch([tablePage, tablePageSize], () => load());
watch([opUid, status], () => load(true));
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">提分单管理</span>
      <em v-if="data" class="hdr-note">{{ hdrNote }}</em>
      <button class="btn sm hdr-export" :disabled="exporting" @click="exportRows">{{ exporting ? "导出中…" : "导出" }}</button>
    </div>

    <div class="note rd">
      <b>本页只读，不提供发放与确认入口。</b>提分兑付必须由店员在<b>商家移动端「待办」页当面完成</b>——顾客站在吧台前、店员核对单号后四位、当面把东西给出去，这三件事同时发生才算发放。Web 端若开操作入口，等于允许远程把顾客积分标记为已发放，顾客没拿到东西账上却已扣，双方都无法举证。<b>本页职责是查询与服务质量分析。</b>
    </div>

    <AppAsyncPage
      :loading="loading"
      :data="data"
      :err="err"
      :skeleton="{ showExtraCard: true, tableCols: 8, tableRows: 8 }"
      @retry="load()"
    >
      <div class="card flt-card">
        <div class="st">筛选 <em>当前范围：{{ data.rangeLabel }}</em></div>
        <div class="flt-chips">
          <span v-for="[p, label] in PRESETS" :key="p" class="chip" :class="{ on: preset === p }" @click="setPreset(p)">{{ label }}</span>
        </div>
        <div v-if="preset === 'custom'" class="flt-custom">
          <span class="tiny">起</span>
          <AppDateInput v-model="dateFrom" @change="onCustomDateChange" />
          <span class="tiny">止</span>
          <AppDateInput v-model="dateTo" @change="onCustomDateChange" />
        </div>
        <div class="flt-extra">
          <label class="flt-field">
            <span class="fld">经手员工</span>
            <select v-model.number="opUid" class="inp flt-select">
              <option :value="0">全部操作人</option>
              <option v-for="s in data.staff || []" :key="s.id" :value="s.id">{{ s.nick }} · {{ ROLE[s.role] || s.role }}</option>
            </select>
          </label>
          <label class="flt-field">
            <span class="fld">单据状态</span>
            <select v-model="status" class="inp flt-select">
              <option value="">全部状态</option>
              <option v-for="([key, value]) in Object.entries(STATUS)" :key="key" :value="key">{{ value[0] }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="cards wdr-metrics">
        <div class="mtr">
          <div class="k">已发放积分</div>
          <div class="v">{{ fmt(summary.grantedPts) }}</div>
          <div class="tiny">{{ summary.grantedCount }} 张已发放</div>
        </div>
        <div class="mtr">
          <div class="k">驳回率</div>
          <div class="v" :style="{ color: rejectTone }">{{ summary.rejectionRate ?? 0 }}%</div>
          <div class="tiny">{{ summary.rejected }} / {{ summary.closedCount }} 张已终结</div>
        </div>
        <div class="mtr">
          <div class="k">平均等待时长</div>
          <div class="v wdr-wait">{{ summary.avgWait || "—" }}</div>
          <div class="tiny">提交 → 发放</div>
        </div>
        <div class="mtr">
          <div class="k">P90 等待时长</div>
          <div class="v wdr-wait">{{ summary.p90Wait || "—" }}</div>
          <div class="tiny">90% 的单在此之内</div>
        </div>
      </div>

      <div class="card timeout-card" :style="timeoutCardStyle">
        <div class="row timeout-row">
          <div>
            <div class="tiny" :style="{ color: timeoutTone }">超时关闭率</div>
            <b class="timeout-rate" :style="{ color: timeoutTone }">{{ summary.timeoutRate ?? 0 }}%</b>
            <span class="tiny timeout-sub">{{ summary.timeout }} / {{ summary.closedCount }} 张已终结</span>
          </div>
          <div class="timeout-right">
            <div class="tiny">自动关闭时限</div>
            <b class="timeout-limit">30 分钟</b>
            <div class="tiny">超时冻结积分<b style="color:var(--green)">全额退回</b></div>
          </div>
        </div>
        <div class="tiny timeout-note">
          <b>超时关闭率高说明店员响应慢，是服务质量指标，不是系统故障指标。</b>单据超时不代表系统出错——恰恰是系统按规则正常兜底了。该率上升要查的是排班与吧台响应流程，而不是查程序。超时后<b>冻结积分全额退回可用，绝不没收</b>：提分单只是额度转移凭据，顾客提交后没人来处理是店里的问题，拿顾客积分抵账没有任何道理。
        </div>
      </div>

      <div class="card">
        <div class="st">状态分布 <em>点击可快速筛选</em></div>
        <div class="row flt-chips">
          <span class="chip" :class="{ on: !status }" @click="status = ''; load(true)">全部 {{ data?.filtered ?? 0 }}</span>
          <span
            v-for="([key, value]) in Object.entries(STATUS)"
            :key="key"
            class="chip"
            :class="{ on: status === key }"
            @click="toggleStatus(key)"
          >{{ value[0] }} {{ byStatus[key] ?? 0 }}</span>
        </div>
      </div>

      <div v-if="pending.length" class="card pending-card">
        <div class="st pending-title">待确认提分单 <em>{{ pending.length }} 张 · 不受时间筛选影响 · 仅供掌握积压</em></div>
        <div v-for="row in pending" :key="'p' + row.id" class="li pending-li">
          <div class="gr">
            <b>{{ noHead(row.no) }}<span class="no-tail">{{ noTail(row.no) }}</span> · {{ fmt(row.pts) }} 分</b>
            <span class="mut">{{ memberLabel(row) }} · 提交 {{ stamp(row) }} · 该会员冻结中 {{ fmt(row.pointFz || 0) }} 分</span>
          </div>
          <span class="tiny wait-label">已等待 <b class="wait-val">{{ durTxt(wdrWait(row)) }}</b></span>
          <span v-if="row.expireAt" class="tiny remain">剩 <b>{{ remaining(row) }}</b></span>
          <span class="tiny pending-hint">发放在商家移动端完成</span>
        </div>
        <div class="tiny pending-foot">顾客到吧台报单号末 4 位（红色部分），店员在移动端「待办 → 待确认提分」核对后当面发放。<b>此处无操作按钮是刻意设计</b>，不是功能缺失。</div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even wdr-table" data-cols="llcccccc">
          <thead>
            <tr>
              <th>提分单号</th>
              <th>会员</th>
              <th>数量</th>
              <th>状态</th>
              <th>提交时间</th>
              <th>等待时长</th>
              <th>经手员工</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" :class="{ 'row-pending': row.status === 'PENDING_CONFIRM' }">
              <td><b>{{ row.no }}</b></td>
              <td>{{ memberLabel(row) }}</td>
              <td><b>{{ fmt(row.pts) }}</b></td>
              <td>
                <span class="pill" :style="pillStyle(statusPill(row.status))">{{ statusPill(row.status)[0] }}</span>
              </td>
              <td class="tiny">{{ stamp(row) }}</td>
              <td class="tiny">{{ durTxt(wdrWait(row)) }}</td>
              <td>
                <template v-if="row.opName">
                  {{ row.opName }}
                  <div class="tiny">{{ row.opRole || "—" }}</div>
                </template>
                <span v-else class="mut">—</span>
              </td>
              <td class="tiny mut">{{ noteText(row) }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="8" class="tiny empty-row">当前筛选条件下无提分单</td>
            </tr>
            <tr v-if="tableSummary" class="summary-row">
              <td>合计</td>
              <td class="mut">{{ tableSummary.members }} 位会员</td>
              <td><b>{{ fmt(tableSummary.totalPts) }}</b></td>
              <td colspan="5" class="mut">其中已发放 {{ fmt(tableSummary.grantedPts) }} 分</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
      </div>

      <div class="note">
        <b>状态机：</b>待确认 → 已发放 / 已驳回 / 已取消 / 超时关闭。除「已发放」外<b>其余三个终态一律把冻结积分全额退回可用</b>，不存在任何没收情形。<br />
        <b>防刷规则：</b>同一用户 24 小时内超时关闭超过 3 次，暂停其提交提分单，<b>随时间自然滚动自动解禁</b>，故本页不设人工解禁入口——留人工开关就会有人来求情、就会有例外，规则也就不成规则了。<br />
        <b>等待时长口径：</b>已终结单算「提交 → 发放/关闭」，待确认单算「提交 → 当前」并每秒刷新。P90 取最近秩法不做插值（单据量少时插值出来的小数没有业务含义）。
      </div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.hdr-export { margin-left: auto; }
.hdr-export:disabled { opacity: .55; cursor: not-allowed; }
.flt-card .st em { font-weight: normal; color: var(--ink2); }
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.flt-custom { display: flex; align-items: center; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.flt-extra { display: flex; gap: 10px; margin-top: 9px; flex-wrap: wrap; }
.flt-field { display: block; }
.flt-field .fld { display: block; color: var(--ink2); font-size: 12px; margin-bottom: 4px; }
.flt-select { max-width: 170px; margin: 0; }
.wdr-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 12px; }
.wdr-wait { font-size: 17px; }
.timeout-card { margin-bottom: 12px; }
.timeout-row { align-items: flex-start; }
.timeout-rate { font-size: 26px; display: inline-block; margin-right: 7px; }
.timeout-sub { margin-left: 0; }
.timeout-right { margin-left: auto; text-align: right; }
.timeout-limit { font-size: 16px; }
.timeout-note { margin-top: 8px; line-height: 1.75; color: var(--ink2); }
.pending-card { background: #faeeda; border-color: #ba7517; margin-bottom: 12px; }
.pending-title { color: #ba7517; }
.pending-title em { color: #ba7517; }
.pending-li { border-color: rgba(186, 117, 23, 0.25); align-items: center; flex-wrap: wrap; gap: 6px; }
.no-tail { color: #a32d2d; }
.wait-label { margin-right: 9px; }
.wait-val { color: #ba7517; }
.remain { color: #a32d2d; margin-right: 9px; white-space: nowrap; }
.pending-hint { color: var(--ink3); }
.pending-foot { margin-top: 6px; color: #ba7517; line-height: 1.65; }
.table-card { padding: 0; overflow: auto; }
.row-pending { background: #fdf8ee; }
.summary-row { background: #faf9f5; font-weight: 600; }
.empty-row { text-align: center; color: var(--ink3); padding: 26px !important; }
@media (max-width: 960px) {
  .wdr-metrics { grid-template-columns: 1fr 1fr; }
}
</style>

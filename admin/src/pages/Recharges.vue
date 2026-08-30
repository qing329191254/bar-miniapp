<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppDateInput from "../components/AppDateInput.vue";
import AppSelect from "../components/AppSelect.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const router = useRouter();

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];

const RCST: Record<string, [string, string, string]> = {
  PENDING_PAY: ["待付款", "#BA7517", "#FAEEDA"],
  PAID: ["已到账", "#3B6D11", "#EAF3DE"],
  CLOSED: ["已关闭", "#6B6A65", "#F5F4F0"],
  CANCELLED: ["已取消", "#6B6A65", "#F5F4F0"],
};

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

const CLOSE_LABEL: Record<string, string> = {
  TIMEOUT: "超时未支付自动取消",
  USER_CANCEL: "用户取消",
  STAFF_REJECT: "店员拒绝",
};

const preset = ref("all");
const dateFrom = ref("");
const dateTo = ref("");
const opUid = ref(0);
const memberUid = ref(0);
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const now = ref(Date.now());
const rejectTarget = ref<any | null>(null);
const rejectReason = ref("");
const rejecting = ref(false);
const confirmTarget = ref<any | null>(null);
const actingId = ref(0);
let timer: number | undefined;

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function statusPill(s: string) {
  return RCST[s] || [s, "#6B6A65", "#F5F4F0"];
}
function memberLabel(o: { nick?: string; tail?: string }) {
  const nick = o.nick || "—";
  const tail = o.tail ? ` ${o.tail}` : "";
  return `${nick}${tail}`.trim();
}
function remarkText(r: any) {
  if (r.rejectRemark) return r.rejectRemark;
  if (r.closeReason && CLOSE_LABEL[r.closeReason]) return CLOSE_LABEL[r.closeReason];
  return r.closeReason || "";
}
function noHead(no: string) {
  return no.length > 4 ? no.slice(0, 4) : no;
}
function noTail(no: string) {
  return no.length > 4 ? no.slice(-4) : "";
}
function remain(expireAt: number | null | undefined) {
  if (!expireAt) return "—";
  const sec = Math.max(0, Math.ceil((Number(expireAt) - now.value) / 1000));
  if (!sec) return "超时";
  return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`;
}
function back() {
  router.push("/dash");
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

const summary = computed(() => data.value?.summary || { paidAmount: 0, paidCount: 0, bonusTotal: 0, avgAmount: 0, incomplete: 0 });
const byOp = computed(() => data.value?.byOp || []);
const pending = computed(() => data.value?.pending || []);
const rows = computed(() => data.value?.rows || []);
const rowTotal = computed(() => data.value?.rowTotal ?? 0);
const hdrNote = computed(() => {
  if (!data.value) return "";
  const parts = [`共 ${data.value.totalAll} 笔`, `当前筛出 ${data.value.filtered} 笔`];
  if (pending.value.length) parts.push(`待确认 ${pending.value.length} 张`);
  return parts.join(" · ");
});
const opOpts = computed(() => [
  { value: 0, label: "全部操作人" },
  ...(data.value?.staff || []).map((s: any) => ({
    value: s.id,
    label: `${s.nick} · ${ROLE[s.role] || s.role}`,
  })),
]);
const memberOpts = computed(() => [
  { value: 0, label: "全部会员" },
  ...(data.value?.members || []).map((m: any) => ({
    value: m.id,
    label: `${m.nick} ${m.tail || ""}`.trim(),
  })),
]);

async function load(resetPage = false) {
  if (resetPage) tablePage.value = 1;
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(
      pageQs(tablePage.value, tablePageSize.value, {
        preset: preset.value,
        opUid: opUid.value || undefined,
        uid: memberUid.value || undefined,
      }),
    );
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/recharges-page?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

function openConfirm(r: any) {
  confirmTarget.value = r;
}
function closeConfirm() {
  if (actingId.value) return;
  confirmTarget.value = null;
}
async function confirmOne() {
  const r = confirmTarget.value;
  if (!r) return;
  actingId.value = r.id;
  try {
    await api(`/admin/recharges/${r.id}/confirm`, { method: "POST" });
    confirmTarget.value = null;
    await load();
  } catch (e: any) {
    showToast(e?.message || "确认失败", true);
  } finally {
    actingId.value = 0;
  }
}
function openReject(r: any) {
  rejectTarget.value = r;
  rejectReason.value = "";
}
function closeReject() {
  if (rejecting.value) return;
  rejectTarget.value = null;
  rejectReason.value = "";
}
async function submitReject() {
  const r = rejectTarget.value;
  const reason = rejectReason.value.trim();
  if (!r || reason.length < 2) {
    showToast("请填写拒绝原因（至少 2 个字）", true);
    return;
  }
  rejecting.value = true;
  try {
    await api(`/admin/recharges/${r.id}/reject`, { method: "POST", body: { reason } });
    rejectTarget.value = null;
    rejectReason.value = "";
    await load();
  } catch (e: any) {
    showToast(e?.message || "拒绝失败", true);
  } finally {
    rejecting.value = false;
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
watch([opUid, memberUid], () => load(true));
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">充值记录与管理</span>
      <em v-if="data" class="hdr-note">{{ hdrNote }}</em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回看板</button>
    </div>

    <AppAsyncPage
      :loading="loading"
      :data="data"
      :err="err"
      :skeleton="{ showHeader: false, showExtraCard: true, tableCols: 9, tableRows: 8 }"
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
            <span class="fld">操作人</span>
            <AppSelect v-model="opUid" :options="opOpts" no-margin class="flt-select" />
          </label>
          <label class="flt-field">
            <span class="fld">充值人</span>
            <AppSelect v-model="memberUid" :options="memberOpts" no-margin class="flt-select" />
          </label>
        </div>
      </div>

      <div class="cards rc-metrics">
        <div class="mtr">
          <div class="k">已到账金额</div>
          <div class="v">¥{{ fmt(summary.paidAmount) }}</div>
          <div class="tiny">{{ summary.paidCount }} 笔实收</div>
        </div>
        <div class="mtr">
          <div class="k">赠送金币</div>
          <div class="v">{{ fmt(summary.bonusTotal) }}</div>
          <div class="tiny">平台负债 · 不计收入</div>
        </div>
        <div class="mtr">
          <div class="k">笔均金额</div>
          <div class="v">¥{{ fmt(summary.avgAmount) }}</div>
          <div class="tiny">已到账口径</div>
        </div>
        <div class="mtr">
          <div class="k">未完成</div>
          <div class="v">{{ summary.incomplete }}</div>
          <div class="tiny">待付款 / 已取消</div>
        </div>
      </div>

      <div v-if="byOp.length" class="card">
        <div class="st">按操作人聚合 <em>仅统计已到账</em></div>
        <div class="op-grid">
          <div v-for="op in byOp" :key="op.opUid" class="op-cell">
            <div class="tiny">{{ op.name }}</div>
            <b class="op-amt">¥{{ fmt(op.amt) }}</b>
            <div class="tiny">{{ op.n }} 笔</div>
          </div>
        </div>
      </div>

      <div v-if="pending.length" class="card pending-card">
        <div class="st pending-title">待处理充值单 <em>{{ pending.length }} 张 · 需当面确认收款</em></div>
        <div v-for="r in pending" :key="'p' + r.id" class="li pending-li">
          <div class="gr">
            <b>{{ noHead(r.no) }}<span class="no-tail">{{ noTail(r.no) }}</span></b>
            <span class="tiny">{{ memberLabel(r) }} · ¥{{ fmt(r.amount) }} + 赠 {{ fmt(r.bonus) }} · 发起 {{ r.at || r.created || "—" }}</span>
          </div>
          <span class="tiny remain">{{ remain(r.expireAt) }}</span>
          <button class="btn sm ghost" :disabled="actingId === r.id" @click="openReject(r)">拒绝</button>
          <button class="btn sm rc-confirm" :disabled="actingId === r.id" @click="openConfirm(r)">{{ actingId === r.id ? "处理中…" : "确认收款" }}</button>
        </div>
        <div class="tiny pending-foot">请顾客在吧台提供单号后 4 位（红色部分），核对无误后再确认到账。金额不可修改，系统会自动避免重复入账。</div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even rc-table" data-cols="llccccccc">
          <thead>
            <tr>
              <th>充值单号</th>
              <th>充值人</th>
              <th>实收</th>
              <th>赠送</th>
              <th>状态</th>
              <th>操作人</th>
              <th>时间</th>
              <th>备注</th>
              <th class="col-op">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id" :class="{ 'row-pending': r.status === 'PENDING_PAY' }">
              <td><b>{{ r.no }}</b></td>
              <td>{{ memberLabel(r) }}</td>
              <td><b>¥{{ fmt(r.amount) }}</b></td>
              <td class="bonus-col">{{ fmt(r.bonus) }}</td>
              <td>
                <span class="pill" :style="pillStyle(statusPill(r.status))">{{ statusPill(r.status)[0] }}</span>
              </td>
              <td class="tiny">{{ r.opName || "—" }}</td>
              <td class="tiny">{{ r.at || r.created || "—" }}</td>
              <td class="tiny">{{ remarkText(r) || "—" }}</td>
              <td class="col-op">
                <button v-if="r.status === 'PENDING_PAY'" class="btn sm rc-confirm" :disabled="actingId === r.id" @click="openConfirm(r)">确认</button>
                <span v-else class="tiny">—</span>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="9" class="tiny empty-row">当前筛选条件下无充值记录</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
      </div>

      <div class="note">
        <div class="note-body">
          <p><b>口径：</b>「实收」为顾客实际支付现金，计入营业收入统计；「赠送」为平台负债，用户消费时才核销，不计收入。待付款单超时自动取消，不占用额度。</p>
          <p><b>到账确认规则：</b>充值金额不可修改，同一会员同时只能有一张待付款订单；拒绝时需填写原因。每次确认都会记录操作人、时间、单号及余额变化，便于后续核对。</p>
        </div>
      </div>
    </AppAsyncPage>

    <Teleport to="body">
    <div v-if="confirmTarget" class="reject-mask" @click.self="closeConfirm">
      <div class="reject-dialog">
        <div class="st">确认收款 <em>{{ confirmTarget.no }}</em></div>
        <div class="reject-info">{{ memberLabel(confirmTarget) }} · ¥{{ fmt(confirmTarget.amount) }} + 赠 {{ fmt(confirmTarget.bonus) }}</div>
        <div class="tiny confirm-tip">请核对单号后 4 位与顾客付款金额，确认后将入账并记录操作人。</div>
        <div class="reject-actions">
          <button class="btn ghost" :disabled="!!actingId" @click="closeConfirm">取消</button>
          <button class="btn rc-confirm" :disabled="!!actingId" @click="confirmOne">{{ actingId ? "处理中…" : "确认收款" }}</button>
        </div>
      </div>
    </div>
    <div v-if="rejectTarget" class="reject-mask" @click.self="closeReject">
      <div class="reject-dialog">
        <div class="st">拒绝充值单 <em>{{ rejectTarget.no }}</em></div>
        <div class="reject-info">{{ memberLabel(rejectTarget) }} · ¥{{ fmt(rejectTarget.amount) }} + 赠 {{ fmt(rejectTarget.bonus) }}</div>
        <div class="tiny reject-label">拒绝原因（必填，至少 2 个字）</div>
        <textarea v-model="rejectReason" class="inp reject-reason" maxlength="100" placeholder="例如：顾客未付款离开"></textarea>
        <div class="reject-actions">
          <button class="btn ghost" :disabled="rejecting" @click="closeReject">取消</button>
          <button class="btn danger" :disabled="rejecting" @click="submitReject">{{ rejecting ? "提交中…" : "确认拒绝" }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<style scoped>
.hdr-back { margin-left: auto; }
.flt-card .st em { font-weight: normal; color: var(--ink2); }
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.flt-custom { display: flex; align-items: center; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.flt-extra { display: flex; gap: 10px; margin-top: 9px; flex-wrap: wrap; }
.flt-field { display: block; }
.flt-field .fld { display: block; color: var(--ink2); font-size: 12px; margin-bottom: 4px; }
.flt-field :deep(.flt-select) { width: 170px; max-width: 170px; }
.confirm-tip { margin-bottom: 12px; color: var(--ink2); line-height: 1.6; }
.rc-metrics { margin-bottom: 12px; }
.op-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.op-cell { background: #faf9f5; border-radius: 9px; padding: 10px 12px; }
.op-amt { font-size: 16px; }
.pending-card { background: #fdf4e3; border-color: #ba7517; }
.pending-title { color: #ba7517; }
.pending-title em { color: #ba7517; }
.pending-li { border-color: rgba(186, 117, 23, 0.25); align-items: center; flex-wrap: wrap; gap: 6px; }
.no-tail { color: #a32d2d; }
.remain { color: #a32d2d; margin-right: 4px; white-space: nowrap; }
.pending-foot { margin-top: 6px; color: #ba7517; }
.table-card { padding: 0; overflow: auto; }
.row-pending { background: #fdf8ee; }
.bonus-col { color: #ba7517; }
.rc-confirm { margin: 0; background: #ba7517; border-color: #ba7517; color: #fff; }
.empty-row { text-align: center; padding: 26px; color: var(--ink3); }
.reject-dialog { width: min(440px, 100%); padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 18px 48px rgba(28, 27, 25, 0.24); }
.reject-info { margin-bottom: 12px; padding: 10px 12px; border-radius: 9px; background: #fdf4e3; color: #6b6a65; font-size: 13px; }
.reject-label { margin-bottom: 6px; }
.reject-reason { min-height: 86px; resize: vertical; width: 100%; box-sizing: border-box; }
.reject-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.reject-actions .btn { margin: 0; }
@media (max-width: 960px) {
  .op-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>

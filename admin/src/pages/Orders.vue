<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppDateInput from "../components/AppDateInput.vue";

const router = useRouter();
const route = useRoute();

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];

const ODST: Record<string, [string, string, string]> = {
  PENDING_PAY: ["待付款", "#BA7517", "#FAEEDA"],
  PENDING_ACCEPT: ["待接单", "#185FA5", "#E6F1FB"],
  MAKING: ["制作中", "#534AB7", "#EEEDFE"],
  FINISHED: ["已完成", "#3B6D11", "#EAF3DE"],
  CANCELLED: ["已取消", "#6B6A65", "#F5F4F0"],
  CLOSED: ["已关闭", "#6B6A65", "#F5F4F0"],
  REFUNDED: ["已退款", "#A32D2D", "#FCEBEB"],
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
const msg = ref("");
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const refundTarget = ref<any | null>(null);
const refundReason = ref("");
const refunding = ref(false);

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function statusPill(s: string) {
  return ODST[s] || [s, "#6B6A65", "#F5F4F0"];
}
function memberLabel(o: { nick?: string; tail?: string; uid?: number }) {
  const nick = o.nick || "—";
  const tail = o.tail ? ` ${o.tail}` : "";
  return `${nick}${tail}`.trim();
}
function itemsText(items: any[]) {
  return (items || [])
    .map((i) => `${i.name || "—"}${Number(i.qty || 1) > 1 ? "×" + i.qty : ""}`)
    .join("、") || "—";
}
function canRefund(order: any) {
  if (["CLOSED", "CANCELLED", "REFUNDED"].includes(order.status)) return false;
  if (order.payType === "COIN") return ["MAKING", "FINISHED"].includes(order.status);
  return ["PENDING_ACCEPT", "MAKING", "FINISHED", "PENDING_PAY"].includes(order.status);
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
function toggleStatus(k: string) {
  status.value = status.value === k ? "" : k;
}

const summary = computed(() => data.value?.summary || { paidAmount: 0, paidCount: 0, avgAmount: 0, cancelled: 0, active: 0 });
const byStatus = computed(() => data.value?.byStatus || {});
const byOp = computed(() => data.value?.byOp || []);
const pending = computed(() => data.value?.pending || []);
const rows = computed(() => data.value?.rows || []);
const rowTotal = computed(() => data.value?.rowTotal ?? 0);
const hdrNote = computed(() => {
  if (!data.value) return "";
  const parts = [`共 ${data.value.totalAll} 单`, `当前筛出 ${data.value.filtered} 单`];
  if (pending.value.length) parts.push(`待处理 ${pending.value.length} 单`);
  return parts.join(" · ");
});

async function load(resetPage = false) {
  if (resetPage) tablePage.value = 1;
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(
      pageQs(tablePage.value, tablePageSize.value, {
        preset: preset.value,
        opUid: opUid.value || undefined,
        status: status.value || undefined,
      }),
    );
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/orders-page?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

function openRefund(order: any) {
  refundTarget.value = order;
  refundReason.value = "";
  msg.value = "";
}
function closeRefund() {
  if (refunding.value) return;
  refundTarget.value = null;
  refundReason.value = "";
}
async function submitRefund() {
  const order = refundTarget.value;
  const reason = refundReason.value.trim();
  if (!order || reason.length < 2) {
    msg.value = "请填写退款原因";
    return;
  }
  if (!window.confirm(`确认退款订单 ${order.no}？该操作不可撤销。`)) return;
  refunding.value = true;
  msg.value = "";
  try {
    await api(`/admin/orders/${order.id}/refund`, { method: "POST", body: { reason } });
    refundTarget.value = null;
    refundReason.value = "";
    await load();
  } catch (error: any) {
    msg.value = error.message || "退款失败";
  } finally {
    refunding.value = false;
  }
}

onMounted(() => {
  const qStatus = String(route.query.status || "");
  if (qStatus && ODST[qStatus]) status.value = qStatus;
  load();
});
watch(() => route.query.status, (q) => {
  const s = String(q || "");
  status.value = s && ODST[s] ? s : "";
  load(true);
});
watch([tablePage, tablePageSize], () => load());
watch([opUid], () => load(true));
watch(status, () => load(true));
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">订单记录与管理</span>
      <em v-if="data" class="hdr-note">{{ hdrNote }}</em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回看板</button>
    </div>

    <div v-if="loading && !data" class="card"><p class="tiny loading-hint">加载中…</p></div>
    <div v-else-if="err" class="card err-card">
      <p>{{ err }}</p>
      <button class="btn sm ghost" @click="load()">重试</button>
    </div>

    <template v-else-if="data">
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
            <select v-model.number="opUid" class="inp flt-select">
              <option :value="0">全部操作人</option>
              <option v-for="s in data.staff || []" :key="s.id" :value="s.id">{{ s.nick }} · {{ ROLE[s.role] || s.role }}</option>
            </select>
          </label>
          <label class="flt-field">
            <span class="fld">订单状态</span>
            <select v-model="status" class="inp flt-select">
              <option value="">全部状态</option>
              <option v-for="(v, k) in ODST" :key="k" :value="k">{{ v[0] }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="cards od-metrics">
        <div class="mtr">
          <div class="k">有效订单额</div>
          <div class="v">¥{{ fmt(summary.paidAmount) }}</div>
          <div class="tiny">{{ summary.paidCount }} 单已收款</div>
        </div>
        <div class="mtr">
          <div class="k">笔均金额</div>
          <div class="v">¥{{ fmt(summary.avgAmount) }}</div>
          <div class="tiny">已收款口径</div>
        </div>
        <div class="mtr">
          <div class="k">退款 / 取消</div>
          <div class="v">{{ summary.cancelled }}</div>
          <div class="tiny">不计入营业额</div>
        </div>
        <div class="mtr">
          <div class="k">进行中</div>
          <div class="v">{{ summary.active }}</div>
          <div class="tiny">待付款 / 待接单 / 制作中</div>
        </div>
      </div>

      <div class="card">
        <div class="st">状态分布 <em>点击可快速筛选</em></div>
        <div class="flt-chips">
          <span
            v-for="(v, k) in ODST"
            :key="k"
            class="chip"
            :class="{ on: status === k }"
            @click="toggleStatus(k)"
          >{{ v[0] }} {{ byStatus[k] || 0 }}</span>
        </div>
      </div>

      <div v-if="byOp.length" class="card">
        <div class="st">按操作人聚合 <em>仅统计已收款</em></div>
        <div class="op-grid">
          <div v-for="op in byOp" :key="op.opUid" class="op-cell">
            <div class="tiny">{{ op.name }}</div>
            <b class="op-amt">¥{{ fmt(op.amt) }}</b>
            <div class="tiny">{{ op.n }} 单</div>
          </div>
        </div>
      </div>

      <div v-if="pending.length" class="card pending-card">
        <div class="st pending-title">待处理订单 <em>{{ pending.length }} 单 · 不受时间筛选影响</em></div>
        <div v-for="o in pending" :key="'p' + o.id" class="li pending-li">
          <div class="gr">
            <b>{{ o.no }}</b>
            <span class="tiny">{{ memberLabel(o) }} · {{ o.tableName || "未指定桌台" }} · ¥{{ fmt(o.total) }} · {{ o.payType === "COIN" ? "金币" : "现场付" }}</span>
          </div>
          <span class="pill" :style="pillStyle(statusPill(o.status))">{{ statusPill(o.status)[0] }}</span>
          <span class="tiny pending-hint">日常接单在商家移动端完成</span>
        </div>
        <div class="tiny pending-foot">接单 / 出单为桌边作业，请在商家移动端「待办」页处理；此处仅供后台掌握积压情况。</div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even od-table" data-cols="llllcccccc">
          <thead>
            <tr>
              <th>单号</th>
              <th>用户</th>
              <th>桌台</th>
              <th>商品</th>
              <th>金额</th>
              <th>支付</th>
              <th>状态</th>
              <th>操作人</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td><b>{{ r.no }}</b></td>
              <td>{{ memberLabel(r) }}</td>
              <td class="tiny">{{ r.tableName || "—" }}</td>
              <td class="tiny items-col">{{ itemsText(r.items) }}</td>
              <td><b>¥{{ fmt(r.total) }}</b></td>
              <td class="tiny">{{ r.payType === "COIN" ? "金币" : "现场" }}</td>
              <td>
                <span class="pill" :style="pillStyle(statusPill(r.status))">{{ statusPill(r.status)[0] }}</span>
                <div v-if="r.refundReason" class="tiny refund-reason">{{ r.refundReason }}</div>
              </td>
              <td class="tiny">{{ r.opName || "—" }}</td>
              <td class="tiny">{{ r.at || "—" }}</td>
              <td>
                <button v-if="canRefund(r)" class="btn sm od-refund" @click="openRefund(r)">退款</button>
                <span v-else class="tiny">—</span>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="10" class="tiny empty-row">当前筛选条件下无订单记录</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
      </div>

      <div class="note">
        <b>口径：</b>有效订单额只计「制作中 / 已完成」，退款与取消单不计入营业额。<b>操作人</b>为接单或确认收款的店员，待接单状态尚无经手人故显示「—」。<br />
        <b>退款需店长以上：</b>按原扣款构成退回本金与赠送金币，必填原因并记入操作日志；同时回收该订单发放的未使用套餐赠卡。
      </div>
    </template>

    <div v-if="refundTarget" class="refund-mask" @click.self="closeRefund">
      <div class="refund-dialog">
        <div class="st">
          订单退款
          <em v-if="refundTarget.status === 'FINISHED'"> · 已出单</em>
          <em>{{ refundTarget.no }}</em>
        </div>
        <div v-if="refundTarget.status === 'FINISHED'" class="refund-warn">该订单已出单（商品已交付），退款将产生实物损失，请确认已与顾客达成一致。</div>
        <div class="refund-amount">
          <template v-if="refundTarget.payType === 'COIN'">
            退回 <b>{{ fmt((refundTarget.paidPrincipal || 0) + (refundTarget.paidBonus || 0)) }}</b> 金币
            <span>本金 {{ fmt(refundTarget.paidPrincipal || 0) }} / 赠送 {{ fmt(refundTarget.paidBonus || 0) }}</span>
          </template>
          <template v-else>
            需线下原路退款 <b>¥{{ fmt(refundTarget.total) }}</b>
            <span>本操作不写入会员金币余额</span>
          </template>
        </div>
        <div class="tiny refund-label">退款原因（必填，至少 2 个字）</div>
        <textarea v-model="refundReason" class="inp refund-reason" maxlength="100" placeholder="例如：商品缺货，已与顾客协商退款"></textarea>
        <div v-if="msg" class="err">{{ msg }}</div>
        <div class="refund-actions">
          <button class="btn ghost" :disabled="refunding" @click="closeRefund">取消</button>
          <button class="btn danger" :disabled="refunding" @click="submitRefund">{{ refunding ? "退款处理中…" : "确认退款" }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hdr-back { margin-left: auto; }
.loading-hint { padding: 24px; text-align: center; }
.err-card { background: #fcebeb; border-color: #e24b4a; }
.err-card p { color: #a32d2d; padding: 16px; }
.flt-card .st em { font-weight: normal; color: var(--ink2); }
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.flt-custom { display: flex; align-items: center; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.flt-date { width: auto; max-width: 150px; margin: 0; }
.flt-extra { display: flex; gap: 10px; margin-top: 9px; flex-wrap: wrap; }
.flt-field { display: block; }
.flt-field .fld { display: block; color: var(--ink2); font-size: 12px; margin-bottom: 4px; }
.flt-select { max-width: 170px; margin: 0; }
.od-metrics { margin-bottom: 12px; }
.op-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.op-cell { background: #faf9f5; border-radius: 9px; padding: 10px 12px; }
.op-amt { font-size: 16px; }
.pending-card { background: #e6f1fb; border-color: #185fa5; }
.pending-title { color: #185fa5; }
.pending-title em { color: #185fa5; }
.pending-li { border-color: rgba(24, 95, 165, 0.2); align-items: center; }
.pending-hint { color: var(--ink3); margin-left: 8px; white-space: nowrap; }
.pending-foot { margin-top: 6px; color: #185fa5; }
.table-card { padding: 0; overflow: auto; }
.items-col { max-width: 220px; }
.refund-reason { color: #a32d2d; margin-top: 2px; }
.od-refund { color: #a32d2d; border-color: #e9c4c4; margin: 0; }
.empty-row { text-align: center; padding: 26px; color: var(--ink3); }
.refund-mask { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(28, 27, 25, 0.42); }
.refund-dialog { width: min(440px, 100%); padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 18px 48px rgba(28, 27, 25, 0.24); }
.refund-warn { color: #a32d2d; font-size: 12px; margin-bottom: 8px; }
.refund-amount { margin-bottom: 13px; padding: 11px 12px; border-radius: 9px; background: #fcebeb; color: #a32d2d; }
.refund-amount b { font-size: 17px; }
.refund-amount span { display: block; margin-top: 2px; font-size: 12px; color: #6b6a65; }
.refund-label { margin-bottom: 6px; }
.refund-reason { min-height: 86px; resize: vertical; width: 100%; box-sizing: border-box; }
.refund-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.refund-actions .btn { margin: 0; }
@media (max-width: 960px) {
  .op-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>

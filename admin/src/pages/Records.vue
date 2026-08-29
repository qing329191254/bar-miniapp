<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";

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
const rowTotal = ref(0);
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const pendingItems = ref<any[]>([]);
const members = ref<any[]>([]);
const status = ref("");
const msg = ref("");
const refundTarget = ref<any | null>(null);
const refundReason = ref("");
const refunding = ref(false);

const titles: Record<string, [string, string]> = {
  orders: ["订单记录", "接单扣款 · 到店付在待办确认"],
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
function canRefund(order: any) {
  if (order.payType === "COIN") return ["MAKING", "FINISHED"].includes(order.status);
  return ["PENDING_ACCEPT", "MAKING", "FINISHED"].includes(order.status);
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
    <div class="note rd" v-if="coll==='orders'">订单退款仅限店长或老板操作：金币订单按原本金、赠送构成退回；到吧台付款需线下原路退款，系统留痕并更新订单状态。</div>
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
      <table class="tb2" v-if="coll==='orders'" data-cols="llcccccc">
        <thead>
          <tr><th>单号</th><th>会员</th><th>桌台</th><th>金额</th><th>支付</th><th>状态</th><th>时间</th><th>操作</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ r.nick || nick(r.uid) }}</td>
          <td class="tiny">{{ r.tableName || "—" }}</td>
          <td><b>{{ r.total }}</b></td>
          <td class="tiny">{{ r.payType === "COIN" ? "金币" : "到店付" }}</td>
          <td><span class="pill" :style="{ color: pill(OD, r.status)[1] }">{{ pill(OD, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at }}</td>
          <td><button v-if="canRefund(r)" class="btn danger small-btn" @click="openRefund(r)">退款</button><span v-else class="tiny">—</span></td>
        </tr>
        </tbody>
      </table>
      <table class="tb2" v-else-if="coll==='recharges'" data-cols="llcccc">
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

    <div v-if="refundTarget" class="refund-mask" @click.self="closeRefund">
      <div class="refund-dialog">
        <div class="st">订单退款 <em>{{ refundTarget.no }}</em></div>
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
        <div class="tiny" style="margin-bottom:6px">退款原因（必填，至少 2 个字）</div>
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
.small-btn { padding: 5px 9px; font-size: 12px; }
.refund-mask { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(28, 27, 25, .42); }
.refund-dialog { width: min(440px, 100%); padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 18px 48px rgba(28, 27, 25, .24); }
.refund-amount { margin-bottom: 13px; padding: 11px 12px; border-radius: 9px; background: #fcebeb; color: #a32d2d; }
.refund-amount b { font-size: 17px; }
.refund-amount span { display: block; margin-top: 2px; font-size: 12px; color: #6b6a65; }
.refund-reason { min-height: 86px; resize: vertical; }
.refund-actions { display: flex; justify-content: flex-end; gap: 8px; }
.refund-actions .btn { margin: 0; }
</style>

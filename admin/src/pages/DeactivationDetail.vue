<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const route = useRoute();
const router = useRouter();
const id = computed(() => Number(route.params.id));
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const refundOk = ref(false);
const dlg = ref<null | "exec" | "reject">(null);
const reason = ref("");
const acting = ref(false);

const ST: Record<string, [string, string, string]> = {
  PENDING: ["待处理", "#BA7517", "#FAEEDA"],
  REJECTED: ["已驳回", "#A32D2D", "#FCEBEB"],
  DONE: ["已注销", "#6B6A65", "#F5F4F0"],
};
const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

type AssetRow = [string, number, number, string, string, string];

const ASSETS: Omit<AssetRow, 1 | 2>[] = [
  ["金币 · 本金", "¥", "#A32D2D", "顾客真实资金，注销前必须线下退还"],
  ["金币 · 赠送", "¥", "#BA7517", "不可退不可提现，注销时直接清零"],
  ["积分 · 可用", "", "#185FA5", "注销时清零，不折现"],
  ["积分 · 冻结", "", "#BA7517", "有冻结说明尚有提分单未终结，须先处理"],
  ["碎片 · 本周", "", "#534AB7", "荣誉值，清零不影响任何资金"],
  ["未核销卡券", "", "#534AB7", "注销时全部作废，须当面告知顾客"],
];

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function back() {
  router.push("/deactivations");
}
function snapKey(i: number) {
  return ["coinP", "coinB", "point", "pointFz", "shardW", "cards"][i];
}
function liveKey(i: number) {
  return snapKey(i);
}

const isPending = computed(() => data.value?.status === "PENDING");
const hasFz = computed(() => (data.value?.live?.pointFz || 0) > 0);
const canExec = computed(() => isPending.value && refundOk.value && !hasFz.value);

const memberStatus = computed(() => {
  const m = data.value?.member;
  if (!m) return "账号已删除";
  if (m.status === "DEACTIVATED") return "已注销";
  if (m.deact === "DEACTIVATE_PENDING") return "正常 · 已提交注销申请（标记中，仍可消费）";
  return "正常";
});

const auditText = computed(() => {
  const d = data.value;
  if (!d?.auditAt) return "";
  const s = d.staff?.[d.auditBy];
  const name = s?.nick || "—";
  const role = s?.role ? ROLE[s.role] || s.role : "—";
  let t = `${name}（${role}） · ${d.auditAt}`;
  if (d.auditRemark) t += ` · ${d.auditRemark}`;
  if (d.status === "DONE") {
    t += ` · 已退本金 ¥${fmt(d.refunded || 0)}`;
    if (d.voidCards) t += ` · 作废卡券 ${d.voidCards} 张`;
  }
  return t;
});

const assetRows = computed<AssetRow[]>(() => {
  if (!data.value) return [];
  const snap = data.value.snap || {};
  const live = data.value.live || {};
  return ASSETS.map((meta, i) => {
    const k = snapKey(i);
    return [meta[0], Number(snap[k] || 0), Number(live[k] || 0), meta[1], meta[2], meta[3]];
  });
});

const changed = computed(() => assetRows.value.filter((r) => r[1] !== r[2]));

async function load() {
  loading.value = true;
  err.value = "";
  refundOk.value = false;
  try {
    data.value = await api(`/admin/deactivation/${id.value}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

function openExec() {
  if (!refundOk.value) {
    showToast("请先勾选「本金已退还」", true);
    return;
  }
  if (hasFz.value) {
    showToast("该会员仍有冻结积分，请先处理其提分单", true);
    return;
  }
  dlg.value = "exec";
}
function openReject() {
  dlg.value = "reject";
  reason.value = "";
}
function closeDlg() {
  dlg.value = null;
  reason.value = "";
}

async function submitDlg() {
  if (!dlg.value || !data.value) return;
  if (dlg.value === "reject" && reason.value.trim().length < 2) {
    showToast("驳回原因至少 2 个字", true);
    return;
  }
  acting.value = true;
  try {
    const action = dlg.value === "exec" ? "exec" : "reject";
    await api(`/admin/deactivations/${data.value.id}/${action}`, {
      method: "POST",
      body: dlg.value === "reject" ? { reason: reason.value.trim() } : {},
    });
    closeDlg();
    showToast(action === "exec" ? "已注销" : "已驳回");
    await load();
  } catch (e: any) {
    showToast(e?.message || "操作失败", true);
  } finally {
    acting.value = false;
  }
}

onMounted(load);
watch(id, load);
</script>

<template>
  <div>
    <div class="hdr deact-detail-hdr">
      <span class="hdr-title">注销申请详情 · {{ data?.no || "…" }}</span>
      <div v-if="data?.member" class="hdr-meta">
        <em class="hdr-note">{{ data.member.nick }} · {{ data.member.no }} · {{ data.created }}</em>
        <span v-if="data" class="pill hdr-pill" :style="pillStyle(ST[data.status] || ['', '#6B6A65', '#F5F4F0'])">{{ ST[data.status]?.[0] }}</span>
      </div>
      <button class="btn sm hdr-back" @click="back">‹ 返回列表</button>
    </div>

    <AppAsyncPage
      :loading="loading"
      :data="data"
      :err="err"
      :skeleton="{ variant: 'detail', showHeader: false, showFilter: false, tableRows: 6 }"
      retry-label="重试"
      @retry="load"
    >
      <div class="card">
        <div class="st">申请信息</div>
        <div class="li"><div class="gr"><b>申请原因</b><span class="mut">{{ data.reason || "（未填写）" }}</span></div></div>
        <div class="li"><div class="gr"><b>会员状态</b><span class="mut">{{ memberStatus }}</span></div></div>
        <div v-if="auditText" class="li" style="border-bottom:none">
          <div class="gr"><b>处理记录</b><span class="mut">{{ auditText }}</span></div>
        </div>
      </div>

      <div v-if="changed.length" class="card warn-card">
        <div class="row">
          <b class="warn-title">⚠ 申请后资产有变动（{{ changed.length }} 项不一致）</b>
          <span class="tiny warn-items">{{ changed.map((r) => r[0]).join("、") }}</span>
        </div>
        <div class="tiny warn-note">
          顾客提交申请后仍发生了充值、对局、兑券或消费。<b>请以「当前实时」数据为准进行结算</b>，避免退款金额出现偏差。
        </div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even tb-asset" data-cols="lcccl">
          <thead>
            <tr><th>资产项</th><th>申请时快照</th><th>当前实时</th><th>差异</th><th>处置说明</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in assetRows" :key="i" :class="{ 'row-diff': row[1] !== row[2] }">
              <td><b>{{ row[0] }}</b></td>
              <td class="mut">{{ row[3] }}{{ fmt(row[1]) }}</td>
              <td><b :style="{ color: row[4] }">{{ row[3] }}{{ fmt(row[2]) }}</b></td>
              <td>
                <b v-if="row[2] !== row[1]" style="color:#A32D2D">{{ row[2] > row[1] ? "+" : "−" }}{{ row[3] }}{{ fmt(Math.abs(row[2] - row[1])) }}</b>
                <span v-else class="mut">一致</span>
              </td>
              <td class="tiny mut">{{ row[5] }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="isPending" class="card exec-card">
        <div class="st exec-title">执行注销 <em>不可逆 · 须先完成线下退款</em></div>
        <div v-if="hasFz" class="note rd" style="margin-bottom:9px">
          <b>该会员尚有 {{ fmt(data.live?.pointFz || 0) }} 分冻结中</b>（提分单待确认）。请先在商家移动端处理完该提分单，再执行注销——带着未终结单据注销，那张单既发不出去也退不回来。
        </div>
        <label class="refund-check">
          <input v-model="refundOk" type="checkbox" />
          <span>
            <b class="refund-label">我已确认：本金 ¥{{ fmt(data.live?.coinP || 0) }} 已线下退还给顾客</b>
            <span class="tiny refund-note">
              金币本金属于顾客的实际资产。注销后账户余额将清零，请务必在线下退款完成并保留凭证后再勾选确认，避免后续产生退款争议。
            </span>
          </span>
        </label>
        <div class="exec-actions">
          <button class="btn reject-btn" @click="openReject">驳回申请</button>
          <button class="btn dan exec-btn" :disabled="!canExec" @click="openExec">
            {{ hasFz ? "请先处理冻结积分" : refundOk ? "确认执行注销" : "请先勾选「本金已退还」" }}
          </button>
        </div>
        <div class="tiny exec-foot">
          执行后：会员状态将变为「已注销」，金币、积分与碎片清零，未核销卡券全部作废，并记录完整操作日志。历史订单与协议同意记录仍会保留，便于后续查询。
        </div>
      </div>
      <div v-else class="note">该申请已处理完成（{{ ST[data.status]?.[0] }}），无法再次操作。如仍需注销，请让顾客从小程序重新提交申请。</div>
    </AppAsyncPage>

    <Teleport to="body">
    <div v-if="dlg" class="deact-mask" @click.self="closeDlg">
      <div class="deact-dialog">
        <div class="st">{{ dlg === "exec" ? "确认执行注销" : "驳回注销申请" }}</div>
        <template v-if="dlg === 'exec' && data">
          <p class="deact-body">
            将注销会员 <b>{{ data.member?.nick }} {{ data.member?.no }}</b>，执行后不可恢复：<br />
            · 金币清零：本金 <b>¥{{ fmt(data.live?.coinP || 0) }}</b>（已确认线下退还）+ 赠送 <b>¥{{ fmt(data.live?.coinB || 0) }}</b>（不可退）<br />
            · 积分清零 <b>{{ fmt(data.live?.point || 0) }}</b> 分 · 碎片清零 <b>{{ fmt(data.live?.shardW || 0) }}</b><br />
            · 作废未核销卡券 <b>{{ data.live?.cards || 0 }}</b> 张<br />
            · 账号状态置「已注销」，退出所有战队与榜单<br />
            <span class="tiny deact-warn">基础账号信息、历史订单与协议同意记录仍会保留，便于后续追溯。</span>
          </p>
        </template>
        <template v-else-if="data">
          <p class="deact-body tiny">
            驳回 <b>{{ data.member?.nick }} {{ data.member?.tail }}</b> 的注销申请（{{ data.no }}）。<br />
            注销是协议已承诺的权利，驳回原因会同步给顾客，须写成能当面解释的话（如「资产尚未结清，请到店办理」）。驳回后顾客可重新提交。
          </p>
          <div class="tiny" style="margin:10px 0 6px">驳回原因（必填，至少 2 个字）</div>
          <textarea v-model="reason" class="inp deact-reason" maxlength="100" placeholder="例如：资产尚未结清，请到店办理"></textarea>
        </template>
        <div class="deact-actions">
          <button class="btn ghost" :disabled="acting" @click="closeDlg">取消</button>
          <button class="btn dan" :disabled="acting" @click="submitDlg">{{ acting ? "处理中…" : dlg === "exec" ? "确认执行" : "确认驳回" }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<style scoped>
.deact-detail-hdr .hdr-meta {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: calc(100% - 320px);
}
.deact-detail-hdr .hdr-note {
  position: static;
  transform: none;
  pointer-events: auto;
  white-space: nowrap;
}
.deact-detail-hdr .hdr-back {
  margin-left: auto;
}
.hdr-pill {
  flex: none;
}
.table-card {
  padding: 0;
  overflow: auto;
}
.tb-asset {
  table-layout: fixed;
}
.row-diff {
  background: #fdf3f3;
}
.warn-card {
  background: var(--redbg);
  border-color: #e24b4a;
  padding: 10px 12px;
}
.warn-title {
  font-size: 13px;
  color: var(--red);
}
.warn-items {
  margin-left: 9px;
  color: var(--red);
}
.warn-note {
  margin-top: 6px;
  color: var(--red);
  line-height: 1.7;
}
.exec-card {
  border-color: var(--red);
}
.exec-title {
  color: var(--red);
}
.exec-title em {
  color: var(--red);
  font-style: normal;
  font-size: 11px;
  font-weight: 400;
  margin-left: auto;
}
.refund-check {
  display: flex;
  gap: 8px;
  cursor: pointer;
  background: var(--redbg);
  border-radius: 9px;
  padding: 11px 12px;
  margin-bottom: 10px;
  align-items: flex-start;
}
.refund-label {
  color: var(--red);
  font-size: 12.5px;
}
.refund-note {
  display: block;
  color: var(--ink2);
  margin-top: 3px;
  line-height: 1.7;
}
.exec-actions {
  display: flex;
  gap: 8px;
}
.reject-btn {
  flex: 1;
}
.exec-btn {
  flex: 1.6;
}
.exec-foot {
  margin-top: 7px;
  color: var(--ink3);
  line-height: 1.7;
}
.deact-dialog {
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  width: min(460px, 100%);
  box-shadow: 0 8px 32px rgba(28, 27, 25, 0.12);
}
.deact-body {
  font-size: 13px;
  line-height: 1.65;
  margin: 8px 0 4px;
}
.deact-warn {
  color: var(--red);
}
.deact-reason {
  width: 100%;
  min-height: 72px;
  resize: vertical;
  box-sizing: border-box;
}
.deact-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
</style>

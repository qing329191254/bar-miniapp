<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, savedUser } from "../api";

const router = useRouter();
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const msg = ref("");
const dlg = ref<null | { mode: "approve" | "reject"; row: any }>(null);
const reason = ref("");
const acting = ref(false);
const dlgErr = ref("");

const isBoss = computed(() => savedUser()?.role === "BOSS");

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };
const ST: Record<string, [string, string, string]> = {
  PENDING: ["待审批", "#BA7517", "#FAEEDA"],
  APPROVED: ["已通过", "#3B6D11", "#EAF3DE"],
  REJECTED: ["已驳回", "#A32D2D", "#FCEBEB"],
};

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function memberLabel(uid: number) {
  const m = data.value?.members?.[uid];
  return m ? `${m.nick} ${m.tail}`.trim() : "—";
}
function staffName(id: number) {
  return data.value?.staff?.[id]?.nick || "—";
}
function staffRole(id: number) {
  const r = data.value?.staff?.[id]?.role;
  return r ? ROLE[r] || r : "—";
}
function typeLabel(t: string) {
  return t === "PRINCIPAL" ? "本金" : t === "BONUS" ? "赠送" : t || "—";
}
function deltaColor(d: number) {
  return d > 0 ? "#3B6D11" : "#A32D2D";
}
function back() {
  router.push("/dash");
}

const pending = computed(() => (data.value?.list || []).filter((a: any) => a.status === "PENDING"));
const list = computed(() => data.value?.list || []);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    data.value = await api("/admin/coin-adjust");
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

function openApprove(row: any) {
  dlg.value = { mode: "approve", row };
  reason.value = "";
  dlgErr.value = "";
}
function openReject(row: any) {
  dlg.value = { mode: "reject", row };
  reason.value = "";
  dlgErr.value = "";
}
function closeDlg() {
  dlg.value = null;
  reason.value = "";
  dlgErr.value = "";
}

async function submitDlg() {
  if (!dlg.value) return;
  const { mode, row } = dlg.value;
  if (mode === "reject" && reason.value.trim().length < 2) {
    dlgErr.value = "驳回原因至少 2 个字";
    return;
  }
  acting.value = true;
  dlgErr.value = "";
  msg.value = "";
  try {
    await api(`/admin/coin-adjust/${row.id}/${mode}`, {
      method: "POST",
      body: mode === "reject" ? { reason: reason.value.trim() } : {},
    });
    closeDlg();
    msg.value = mode === "approve" ? "已通过，金币已调整" : "已驳回";
    await load();
  } catch (e: any) {
    dlgErr.value = e?.message || "操作失败";
  } finally {
    acting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">金币手动调整审批</span>
      <em v-if="data" class="hdr-note">{{ data.pending || 0 }} 笔待审批 · {{ isBoss ? "老板可审批" : "店长只读" }}</em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回看板</button>
    </div>

    <div v-if="!isBoss" class="note rd">
      <b>权限不足：</b>手动调整金币直接改动真实负债，审批权仅归老板。店长可发起申请与查看进度，不可自行通过——否则「有权改数据的人同时能批准自己的改动」，风控形同虚设。
    </div>

    <p v-if="msg" class="tiny" style="color:#3B6D11;margin-bottom:10px">{{ msg }}</p>

    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
      <div v-if="pending.length" class="card pending-card">
        <div class="st" style="color:var(--gold)">待审批申请</div>
        <div v-for="a in pending" :key="a.id" class="li pending-li">
          <div class="gr">
            <b>{{ memberLabel(a.uid) }} · {{ a.delta > 0 ? "+" : "" }}{{ fmt(a.delta) }} {{ typeLabel(a.type) }}金币</b>
            <span class="mut">申请人 {{ staffName(a.by) }}（{{ staffRole(a.by) }}） · {{ a.at }}</span>
            <span class="tiny pending-reason">原因：{{ a.reason || "—" }} · 调整后余额 ¥{{ fmt(a.projected ?? a.balance) }}</span>
          </div>
          <template v-if="isBoss">
            <button class="btn sm reject-btn" @click="openReject(a)">驳回</button>
            <button class="btn sm pri" @click="openApprove(a)">通过</button>
          </template>
          <span v-else class="tiny" style="color:var(--ink3)">仅老板可审批</span>
        </div>
      </div>
      <div v-else class="card"><p class="mut empty-pending">暂无待审批的金币调整申请</p></div>

      <div class="card table-card">
        <table class="tb2 tb-even tb-coin-adj" data-cols="lclclcc">
          <thead>
            <tr>
              <th>会员</th><th>调整额</th><th>类型</th><th>原因</th><th>申请人</th><th>时间</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in list" :key="a.id">
              <td>{{ memberLabel(a.uid) }}</td>
              <td><b :style="{ color: deltaColor(a.delta) }">{{ a.delta > 0 ? "+" : "" }}{{ fmt(a.delta) }}</b></td>
              <td class="mut">{{ typeLabel(a.type) }}</td>
              <td class="mut">{{ a.reason || "—" }}</td>
              <td>{{ staffName(a.by) }}<div class="tiny">{{ staffRole(a.by) }}</div></td>
              <td class="mut">{{ a.at }}</td>
              <td>
                <span class="pill" :style="pillStyle(ST[a.status] || [a.status, '#6B6A65', '#F5F4F0'])">{{ ST[a.status]?.[0] || a.status }}</span>
                <div v-if="a.auditRemark" class="tiny">{{ a.auditRemark }}</div>
              </td>
            </tr>
            <tr v-if="!list.length">
              <td colspan="7" class="tiny empty-row">暂无调整记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="note">
        <b>为何要审批：</b>金币是真实负债且无第三方支付流水兜底，手动加币等于凭空创造负债。审批制把「谁申请」与「谁批准」分离，两人留痕后才生效。<b>店员一律无权发起</b>，店长可发起、老板批准。全部操作进入仅老板可见的操作日志。
      </div>
    </template>

    <div v-if="dlg" class="adj-mask" @click.self="closeDlg">
      <div class="adj-dialog">
        <div class="st">{{ dlg.mode === "approve" ? "通过金币调整" : "驳回金币调整" }}</div>
        <template v-if="dlg.mode === 'approve'">
          <p class="adj-body">
            会员 <b>{{ memberLabel(dlg.row.uid) }}</b><br />
            调整 <b :style="{ color: deltaColor(dlg.row.delta), fontSize: '17px' }">{{ dlg.row.delta > 0 ? "+" : "" }}{{ fmt(dlg.row.delta) }}</b> {{ typeLabel(dlg.row.type) }}金币<br />
            余额 <b>¥{{ fmt(dlg.row.balance) }} → ¥{{ fmt(dlg.row.projected ?? dlg.row.balance) }}</b><br />
            <span class="tiny">申请人 {{ staffName(dlg.row.by) }} · 原因：{{ dlg.row.reason || "—" }}</span><br />
            <span class="tiny adj-warn">通过后立即生效，改动真实负债，不可撤销。</span>
          </p>
        </template>
        <template v-else>
          <p class="adj-body tiny">会员 <b>{{ memberLabel(dlg.row.uid) }}</b> · {{ dlg.row.delta > 0 ? "+" : "" }}{{ fmt(dlg.row.delta) }} {{ typeLabel(dlg.row.type) }}金币</p>
          <div class="tiny" style="margin:10px 0 6px">驳回原因（必填，至少 2 个字）</div>
          <textarea v-model="reason" class="inp adj-reason" maxlength="100" placeholder="例如：凭证不完整"></textarea>
        </template>
        <div v-if="dlgErr" class="adj-err">{{ dlgErr }}</div>
        <div class="adj-actions">
          <button class="btn ghost" :disabled="acting" @click="closeDlg">取消</button>
          <button
            class="btn"
            :class="dlg.mode === 'reject' ? 'adj-submit-reject' : 'pri'"
            :disabled="acting"
            @click="submitDlg"
          >{{ acting ? "处理中…" : dlg.mode === "approve" ? "确认通过" : "确认驳回" }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pending-card {
  background: var(--goldbg);
  border-color: var(--gold);
}
.pending-li {
  border-color: rgba(186, 117, 23, 0.25);
}
.pending-reason {
  display: block;
  margin-top: 2px;
}
.empty-pending {
  padding: 26px;
  text-align: center;
}
.table-card {
  padding: 0;
  overflow: auto;
}
.tb-coin-adj {
  table-layout: fixed;
}
.empty-row {
  text-align: center;
  padding: 26px;
  color: var(--ink3);
}
.reject-btn {
  color: var(--red);
  border-color: #e9c4c4;
}
.adj-mask {
  position: fixed;
  inset: 0;
  background: rgba(28, 27, 25, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 16px;
}
.adj-dialog {
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  width: min(420px, 100%);
  box-shadow: 0 8px 32px rgba(28, 27, 25, 0.12);
}
.adj-body {
  font-size: 13px;
  line-height: 1.65;
  margin: 8px 0 4px;
}
.adj-warn {
  color: var(--red);
}
.adj-reason {
  width: 100%;
  min-height: 72px;
  resize: vertical;
  box-sizing: border-box;
}
.adj-err {
  color: var(--red);
  font-size: 12px;
  margin-top: 8px;
}
.adj-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
.adj-submit-reject {
  background: var(--red);
  color: #fff;
  border-color: var(--red);
}
</style>

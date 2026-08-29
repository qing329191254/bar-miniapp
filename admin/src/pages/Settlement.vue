<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, DEFAULT_PAGE_SIZE, pageQs, savedUser } from "../api";
import AppPagination from "../components/AppPagination.vue";

const data = ref<any>({ rows: [], summary: {} });
const preview = ref<any>({ rows: [] });
const members = ref<any[]>([]), templates = ref<any[]>([]);
const page = ref(1), pageSize = ref(DEFAULT_PAGE_SIZE);
const msg = ref(""), busy = ref(false), snapshot = ref<any>(null);
const revokeRow = ref<any>(null), revokeReason = ref("");
const manualOpen = ref(false), manual = ref({ uid: "", tplId: "", reason: "" });
const boss = savedUser()?.role === "BOSS";
const labels: Record<string, string> = { TEAM_CHAMPION: "战队夺冠", PERSONAL_RANK1: "个人第 1", PERSONAL_RANK2: "个人第 2", PERSONAL_RANK3: "个人第 3", MANUAL: "手动补发" };
const displayWeek = computed(() => (data.value.week || preview.value.week || "暂无结算周期").replace("~", " ~ "));
const ruleText = computed(() => `名次占位制 · ${data.value.cfg?.stack === false ? "不可叠加" : "可叠加"}`);
const executeDate = computed(() => {
  const m = String(data.value.week || "").split("~")[1]?.match(/^(\d{2})-(\d{2})$/);
  if (!m) return "已执行";
  const d = new Date(2026, Number(m[1]) - 1, Number(m[2]) + 1);
  return `已执行 · ${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} 04:00`;
});

async function load() { data.value = await api(`/admin/settlement/current?${pageQs(page.value, pageSize.value)}`); }
async function loadPreview() { preview.value = await api("/admin/settlement/preview"); }
async function loadOptions() {
  const [memberData, config] = await Promise.all([api<any>("/admin/members?pageSize=0"), api<any>("/admin/settlement-config")]);
  members.value = Array.isArray(memberData) ? memberData : memberData.items || [];
  templates.value = config.templates || [];
}
async function refreshAll() { try { await Promise.all([load(), loadPreview()]); } catch (e: any) { msg.value = e.message; } }
async function rerun() {
  if (!confirm(data.value.executed ? "确认重新跑本周期结算？已发放记录会幂等跳过，不会重复发券。" : "确认按预览结果执行本周期结算？")) return;
  busy.value = true; msg.value = "";
  try { const res = await api<any>("/admin/settlement/rerun", { method: "POST" }); msg.value = res.message || "结算已处理"; await refreshAll(); }
  catch (e: any) { msg.value = e.message; } finally { busy.value = false; }
}
async function openSnapshot() { try { snapshot.value = await api(`/admin/settlement/current?${pageQs(1, 50)}`); } catch (e: any) { msg.value = e.message; } }
function openRevoke(row: any) { revokeRow.value = row; revokeReason.value = ""; msg.value = ""; }
async function revoke() {
  if (revokeReason.value.trim().length < 2) { msg.value = "撤销原因至少 2 个字"; return; }
  busy.value = true; msg.value = "";
  try { await api(`/admin/settlement/${revokeRow.value.id}/revoke`, { method: "POST", body: { data: { reason: revokeReason.value.trim() } } }); revokeRow.value = null; msg.value = "奖励已撤销"; await refreshAll(); }
  catch (e: any) { msg.value = e.message; } finally { busy.value = false; }
}
async function grantManual() {
  if (!manual.value.uid || !manual.value.tplId) { msg.value = "请选择会员和补发奖励"; return; }
  if (manual.value.reason.trim().length < 2) { msg.value = "补发原因至少 2 个字"; return; }
  busy.value = true; msg.value = "";
  try { await api("/admin/settlement/manual", { method: "POST", body: { data: { ...manual.value, reason: manual.value.reason.trim() } } }); manualOpen.value = false; manual.value = { uid: "", tplId: "", reason: "" }; msg.value = "手动补发成功，奖励已进入会员卡包"; await refreshAll(); }
  catch (e: any) { msg.value = e.message; } finally { busy.value = false; }
}
function statusText(s: string) { return s === "GRANTED" ? "已发放" : s === "REVOKED" ? "已撤销" : s === "SKIPPED" ? "未发放" : s; }
function typeClass(r: any) { return r.type === "TEAM_CHAMPION" ? "type-team" : r.type === "PERSONAL_RANK1" ? "type-rank1" : r.type === "PERSONAL_RANK2" ? "type-rank2" : "type-rank3"; }
watch([page, pageSize], load);
onMounted(async () => { await Promise.all([refreshAll(), loadOptions()]); });
</script>

<template>
  <div class="settlement-page">
    <div class="hdr settlement-hdr"><span>榜单与周结算</span><em>{{ displayWeek }} · {{ ruleText }}</em></div>
    <div v-if="msg" class="notice" :class="{ err: msg.includes('原因') || msg.includes('超过') || msg.includes('失败') }">{{ msg }}</div>
    <section class="card settlement-card">
      <div class="settle-head">
        <div class="settle-summary"><span class="pill executed">{{ data.executed ? executeDate : "待执行" }}</span><span class="summary-copy" v-if="data.executed">快照已冻结 · 发放 {{ data.summary?.granted || 0 }} 张宝箱卡（战队 {{ data.summary?.team || 0 }} + 个人 {{ data.summary?.personal || 0 }}）</span><span class="summary-copy" v-else>尚未生成结算快照，请先查看下方预览</span></div>
        <div class="ops"><button class="btn ghost" :disabled="busy" @click="rerun">{{ data.executed ? "重新跑" : "执行结算" }}</button><button class="btn ghost" :disabled="!data.executed" @click="openSnapshot">查看快照</button></div>
      </div>
      <div class="table-wrap"><table class="tb2 settlement-table"><thead><tr><th>获奖对象</th><th>类型</th><th>奖励</th><th>碎片校验</th><th>状态</th><th class="col-op">操作</th></tr></thead><tbody>
        <tr v-for="r in data.rows" :key="r.id"><td><b>{{ r.target }}</b><div class="tiny">{{ r.nick }}</div></td><td><span class="pill type-pill" :class="typeClass(r)">{{ labels[r.type] || r.type }}</span></td><td>{{ r.desc }}</td><td class="shard">{{ Number(r.sh || 0).toLocaleString("en-US") }}</td><td><span class="pill status-pill" :class="`status-${String(r.status).toLowerCase()}`">{{ statusText(r.status) }}</span></td><td class="col-op"><button v-if="boss && r.status === 'GRANTED'" class="btn ghost revoke-btn" @click="openRevoke(r)">撤销</button><span v-else class="tiny">—</span></td></tr>
        <tr v-if="!data.rows?.length"><td colspan="6" class="table-empty">当前周期暂无结算记录</td></tr>
      </tbody></table></div>
      <AppPagination v-model:page="page" v-model:page-size="pageSize" :total="data.total || 0" />
      <div class="settle-bottom"><button class="btn ghost" @click="manualOpen=true">手动补发</button><span class="tiny">撤销将同时作废对应未核销卡券；补发需填原因，手动补发不受单次上限约束</span></div>
    </section>
    <section class="card preview-card"><div class="st">按当前规则预览发放 <em>只计算，不会发放真实奖励</em></div><div class="preview-meta"><span>预计发放 <b>{{ preview.count || 0 }}</b> 张</span><span>单次上限 {{ preview.cap || data.cfg?.settleCap || 20 }} 张</span><span class="pill" :class="preview.blocked ? 'preview-blocked' : 'preview-ok'">{{ preview.blocked ? "超过上限" : "校验通过" }}</span></div><div class="preview-list" v-if="preview.rows?.length"><span v-for="(r,i) in preview.rows.slice(0,8)" :key="i" class="chip">{{ r.nick }} · {{ r.desc }}</span><span v-if="preview.rows.length>8" class="tiny">另 {{preview.rows.length-8}} 项</span></div><div v-else class="list-empty">当前规则下暂无可发放对象</div><div class="preview-help">这里替代原型中的“演示、可重复发放”：运营人员可先核对人数和奖励，但反复查看不会产生卡券。</div></section>

    <Teleport to="body"><div v-if="revokeRow" class="settle-modal-mask" @click.self="revokeRow=null"><section class="settle-modal settle-revoke-modal"><div class="settle-modal-title">撤销奖励<button class="settle-modal-close" @click="revokeRow=null">×</button></div><div class="settle-target-summary"><b>{{ revokeRow.nick }}</b><span>{{ revokeRow.target }} · {{ revokeRow.desc }}</span></div><label class="settle-field-label">撤销原因 <i>*必填</i></label><textarea v-model="revokeReason" class="inp settle-reason-input" maxlength="100" placeholder="请输入撤销原因，例如：奖励对象录入错误"></textarea><div class="settle-danger-tip">确认后将同步作废对应的未核销卡券；已经核销的卡券不会追回。</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="revokeRow=null">取消</button><button class="btn dan" :disabled="busy || revokeReason.trim().length<2" @click="revoke">{{ busy ? "处理中…" : "确认撤销" }}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="manualOpen" class="settle-modal-mask" @click.self="manualOpen=false"><section class="settle-modal settle-manual-modal"><div class="settle-modal-title">手动补发<button class="settle-modal-close" @click="manualOpen=false">×</button></div><div class="settle-manual-grid"><label><span class="settle-field-label">会员 <i>*必填</i></span><select v-model="manual.uid" class="inp"><option value="">请选择会员</option><option v-for="m in members" :key="m.id" :value="m.id">{{m.nick}} · {{m.no}}</option></select></label><label><span class="settle-field-label">奖励 <i>*必填</i></span><select v-model="manual.tplId" class="inp"><option value="">请选择奖励</option><option v-for="t in templates" :key="t.id" :value="t.id">{{t.name}}</option></select></label></div><label class="settle-field-label">补发原因 <i>*必填</i></label><textarea v-model="manual.reason" class="inp settle-reason-input" maxlength="100" placeholder="例如：结算漏发补偿"></textarea><div class="settle-info-tip">手动补发不受单次自动结算上限约束，操作人和原因会写入日志。</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="manualOpen=false">取消</button><button class="btn pri" :disabled="busy" @click="grantManual">{{busy?'处理中…':'确认补发'}}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="snapshot" class="settle-modal-mask" @click.self="snapshot=null"><section class="settle-modal settle-snapshot-modal"><div class="settle-modal-title">结算快照<button class="settle-modal-close" @click="snapshot=null">×</button></div><div class="tiny settle-snapshot-sub">{{ snapshot.week?.replace('~',' ~ ') }} · 共 {{snapshot.total}} 条记录 · 规则修改不会回溯本快照</div><div class="settle-snapshot-list"><div v-for="r in snapshot.rows" :key="r.id" class="settle-snapshot-row"><span><b>{{r.nick}}</b><small>{{r.target}}</small></span><span>{{r.desc}}</span><span class="pill status-pill" :class="`status-${String(r.status).toLowerCase()}`">{{statusText(r.status)}}</span></div></div><div class="settle-modal-actions"><button class="btn ghost" @click="snapshot=null">关闭</button></div></section></div></Teleport>
  </div>
</template>

<style scoped>
.settlement-hdr em{margin-left:auto;text-align:right}.notice{margin-bottom:10px;padding:8px 10px;border-radius:7px;background:var(--greenbg);color:var(--green);font-size:12px}.notice.err{background:var(--redbg);color:var(--red)}.settlement-card{padding:0;overflow:hidden}.settle-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 20px 12px}.settle-summary{display:flex;align-items:center;gap:14px;min-width:0}.summary-copy{color:var(--ink3);font-size:12px}.executed{background:var(--greenbg);color:var(--green);white-space:nowrap}.table-wrap{overflow-x:auto;padding:0 20px}.settlement-table{border-radius:0}.settlement-table th,.settlement-table td{padding:12px 10px}.settlement-table td{height:64px}.settlement-table :is(th,td):nth-child(-n+3){text-align:left}.settlement-table :is(th,td):nth-child(n+4){text-align:center}.type-pill{font-size:12px}.type-team{background:var(--greenbg);color:var(--green)}.type-rank1{background:#EEEDFE;color:#534AB7}.type-rank2{background:var(--goldbg);color:var(--gold)}.type-rank3{background:#F1EFE9;color:var(--ink2)}.status-granted{background:var(--greenbg);color:var(--green)}.status-revoked{background:var(--redbg);color:var(--red)}.status-skipped{background:#F1EFE9;color:var(--ink3)}.revoke-btn{padding:5px 12px}.settle-bottom{display:flex;align-items:center;gap:12px;padding:12px 20px;border-top:1px solid var(--line);background:#fff}.preview-card{padding:16px 20px}.preview-meta{display:flex;align-items:center;gap:18px;color:var(--ink2);font-size:13px}.preview-meta b{font-size:18px;color:var(--ink)}.preview-ok{background:var(--greenbg);color:var(--green)}.preview-blocked{background:var(--redbg);color:var(--red)}.preview-list{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.preview-list .chip{cursor:default}.preview-help{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);color:var(--ink3);font-size:12px}
@media(max-width:760px){.settle-head,.settle-summary,.settle-bottom{align-items:flex-start;flex-direction:column}.settle-head .ops{width:100%}}
</style>

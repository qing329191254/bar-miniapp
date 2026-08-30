<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs, savedUser } from "../api";
import AppPagination from "../components/AppPagination.vue";
import { settleRewardText, settleSkipOpText, settleStatusText } from "../settlementDisplay";

const data = ref<any>({ rows: [], summary: {} });
const preview = ref<any>({ rows: [] });
const members = ref<any[]>([]), templates = ref<any[]>([]);
const page = ref(1), pageSize = ref(DEFAULT_PAGE_SIZE);
const msg = ref(""), busy = ref(false), snapshot = ref<any>(null);
const revokeRow = ref<any>(null), revokeReason = ref("");
const manualOpen = ref(false), manual = ref({ uid: "", tplId: "", reason: "" });
const rerunOpen = ref(false), rerunError = ref("");
const forceOpen = ref(false), forceReason = ref(""), forceError = ref("");
const router = useRouter();
const boss = savedUser()?.role === "BOSS";
const labels: Record<string, string> = { TEAM_CHAMPION: "战队夺冠", PERSONAL_RANK1: "个人第 1", PERSONAL_RANK2: "个人第 2", PERSONAL_RANK3: "个人第 3", MANUAL: "手动补发" };
const displayWeek = computed(() => (data.value.week || preview.value.week || "暂无结算周期").replace("~", " ~ "));
const ruleText = computed(() => `名次占位制 · ${data.value.cfg?.stack === false ? "不可叠加" : "可叠加"}`);
const blockedCount = computed(() => Number(data.value.summary?.blocked || 0));
const previewPersonal = computed(() => (preview.value.rows || []).filter((r: any) => r.eligible && String(r.type).startsWith("PERSONAL")).sort((a: any,b: any) => Number(a.rank||0)-Number(b.rank||0)));
const previewTeam = computed(() => (preview.value.rows || []).filter((r: any) => r.eligible && r.type === "TEAM_CHAMPION"));
const personalPreviewText = computed(() => previewPersonal.value.map((r: any) => `第 ${r.rank} 名「${r.nick}」→ ${r.desc}`).join("、") || "—");
const teamPreviewText = computed(() => {
  if (!preview.value.cfg?.teamReward) return "关闭";
  if (!previewTeam.value.length) return "暂无符合条件的获奖成员";
  const first = previewTeam.value[0];
  return `夺冠战队「${first.target}」${previewTeam.value.length} 名符合条件成员 → ${first.desc}${preview.value.cfg?.reqShard ? "（需本人有碎片）" : ""}`;
});
const executeDate = computed(() => {
  if (!data.value.executed) return "待执行";
  const at = data.value.executedAt;
  if (!at) return "已执行";
  const tag = data.value.trigger === "auto" ? " · 自动" : data.value.trigger === "manual" ? " · 手动" : "";
  return `已执行 · ${at}${tag}`;
});
const canExecute = computed(() => !data.value.executed && !preview.value.blocked && !busy.value);

async function load() { data.value = await api(`/admin/settlement/current?${pageQs(page.value, pageSize.value)}`); }
async function loadPreview() { preview.value = await api("/admin/settlement/preview"); }
async function loadOptions() {
  const [memberData, config] = await Promise.all([api<any>("/admin/members?pageSize=0"), api<any>("/admin/settlement-config")]);
  members.value = Array.isArray(memberData) ? memberData : memberData.items || [];
  templates.value = config.templates || [];
}
async function refreshAll() { try { await Promise.all([load(), loadPreview()]); } catch (e: any) { msg.value = e.message; } }
function openRerun() { rerunError.value = ""; msg.value = ""; rerunOpen.value = true; }
async function rerun() {
  busy.value = true; rerunError.value = "";
  try { const res = await api<any>("/admin/settlement/rerun", { method: "POST" }); msg.value = res.message || "结算已处理"; rerunOpen.value = false; await refreshAll(); }
  catch (e: any) { rerunError.value = e.message || "结算处理失败"; } finally { busy.value = false; }
}
function openForce() { forceReason.value = ""; forceError.value = ""; forceOpen.value = true; }
async function forceGrant() {
  if (forceReason.value.trim().length < 2) { forceError.value = "强制发放原因至少 2 个字"; return; }
  busy.value = true; forceError.value = "";
  try { const res = await api<any>("/admin/settlement/force", { method: "POST", body: { data: { reason: forceReason.value.trim() } } }); msg.value = res.message || "强制发放完成"; forceOpen.value = false; await refreshAll(); }
  catch (e: any) { forceError.value = e.message || "强制发放失败"; } finally { busy.value = false; }
}
async function openSnapshot() { try { snapshot.value = await api(`/admin/settlement/snapshot?week=${encodeURIComponent(data.value.week || "")}`); } catch (e: any) { msg.value = e.message; } }
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
function statusText(s: string) { return settleStatusText(s); }
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
        <div class="settle-summary"><span class="pill executed">{{ data.executed ? executeDate : "待执行" }}</span><span class="summary-copy" v-if="blockedCount">快照已冻结 · {{ blockedCount }} 张奖励被整批拦截，一张未发</span><span class="summary-copy" v-else-if="data.executed">快照已冻结 · 发放 {{ data.summary?.granted || 0 }} 张宝箱卡（战队 {{ data.summary?.team || 0 }} + 个人 {{ data.summary?.personal || 0 }}）</span><span class="summary-copy" v-else>尚未结算 · 请先查看下方预览，确认无误后点击「执行结算」</span></div>
        <div class="ops"><button class="btn ghost" :disabled="busy" @click="openRerun">{{ data.executed ? "重新跑" : "执行结算" }}</button><button class="btn ghost" :disabled="!data.executed" @click="openSnapshot">查看快照</button></div>
      </div>
      <div class="table-wrap"><table class="tb2 settlement-table"><thead><tr><th>获奖对象</th><th>类型</th><th>奖励</th><th>碎片校验</th><th>状态</th><th class="col-op">操作</th></tr></thead><tbody>
        <tr v-for="r in data.rows" :key="r.id" :class="{blocked:r.status==='BLOCKED'}"><td><b>{{ r.target }}</b><div class="tiny">{{ r.nick }}</div></td><td><span class="pill type-pill" :class="typeClass(r)">{{ labels[r.type] || r.type }}</span></td><td>{{ settleRewardText(r) }}<div v-if="r.forceReason" class="tiny force-reason">强制发放：{{ r.forceReason }}</div></td><td class="shard">{{ Number(r.sh || 0).toLocaleString("en-US") }}</td><td><span class="pill status-pill" :class="`status-${String(r.status).toLowerCase()}`">{{ statusText(r.status) }}</span></td><td class="col-op"><button v-if="['GRANTED','BLOCKED'].includes(r.status)" class="btn ghost revoke-btn" @click="openRevoke(r)">撤销</button><span v-else-if="r.status==='SKIPPED'" class="tiny skip-reason">{{ settleSkipOpText(r) }}</span><span v-else class="tiny">—</span></td></tr>
        <tr v-if="!data.rows?.length"><td colspan="6" class="table-empty">当前周期暂无结算记录</td></tr>
      </tbody></table></div>
      <AppPagination v-model:page="page" v-model:page-size="pageSize" :total="data.total || 0" />
      <div class="settle-bottom"><button class="btn ghost" @click="manualOpen=true">手动补发</button><span class="tiny">撤销将同时作废对应未核销卡券；补发需填原因，手动补发不受单次上限约束</span></div>
    </section>
    <div class="note settlement-rule-note"><b>名次占位制：</b>同一名次并列时，每位获奖者都会获得该名次对应的奖励；后续名次按实际占位顺延，超出配置范围不发奖。极端并列人数不设上限，实际发放总量以下方预览为准。<b>发奖以冻结快照为准</b>，结算后调整战队不会影响已发放奖励。<br><b>发放张数上限：</b>单次自动结算发放卡券总数超过 <b>{{ preview.cap||data.cfg?.settleCap||20 }} 张</b>时，整批标记为「被拦截」、一张不发。它与「名次范围」是两个独立约束：并列和战队奖叠加可能使实际张数远高于名次范围。</div>

    <section v-if="blockedCount" class="card blocked-card"><div class="st">本周期发放被拦截 <em>{{ blockedCount }} 张 · 超过单次上限 {{ preview.cap||data.cfg?.settleCap||20 }} 张</em></div><p>本批奖励已整批拦截，一张都没有发放。请先检查名次范围、战队奖励和并列情况；确认属于正常的大型活动后，可由老板强制发放。</p><button v-if="boss" class="btn dan" @click="openForce">强制发放 {{ blockedCount }} 张</button><span v-else class="tiny">仅老板可强制发放，请联系老板处理。</span></section>

    <section class="card preview-card">
      <div class="st preview-st">
        <span>结算前预览 <em class="preview-st-note">只读演算 · 不会发卡</em></span>
        <button class="preview-rule-link" @click="router.push('/settlecfg')">修改规则 ›</button>
      </div>
      <div class="preview-meta">
        <span>若现在执行结算，将发放 <b :class="{ red: preview.blocked }">{{ preview.count || 0 }}</b> 张</span>
        <span>单次上限 {{ preview.cap || data.cfg?.settleCap || 20 }} 张</span>
        <span class="pill" :class="preview.blocked ? 'preview-blocked' : 'preview-ok'">{{ preview.blocked ? "超过上限 · 执行后将整批拦截" : "未超限" }}</span>
      </div>
      <div class="preview-detail">
        <p><b>规则摘要</b> · {{ preview.cfg?.rankDim === "MONTH" ? "月维度" : "周维度（周一 00:00 重置）" }} · 个人前 {{ preview.cfg?.rankRange || data.cfg?.rankRange || 3 }} 名 · 战队奖 {{ preview.cfg?.teamReward ? "开" : "关" }} · {{ preview.cfg?.stack ? "可叠加" : "不可叠加" }}</p>
        <p><b>个人榜</b>（碎片{{ preview.cfg?.rankDim === "MONTH" ? "月" : "周" }}榜）{{ personalPreviewText }}</p>
        <p><b>战队奖</b> {{ teamPreviewText }}</p>
        <p v-if="preview.missingRanks?.length" class="preview-missing">第 {{ preview.missingRanks.join("、") }} 名未配置卡型，结算时将跳过。</p>
      </div>
      <div v-if="!data.executed" class="preview-action">
        <template v-if="preview.blocked">
          <p class="preview-action-tip warn">预计发放超过单次上限，请先前往「榜单与奖励规则」调整，或联系老板处理。</p>
          <button class="btn ghost" @click="router.push('/settlecfg')">去调整规则</button>
        </template>
        <template v-else>
          <p class="preview-action-tip">下方为<b>实时榜单演算</b>，仅供核对人数与奖励。确认无误后，点击右侧按钮正式结算并冻结快照。</p>
          <button class="btn pri preview-go" :disabled="!canExecute" @click="openRerun">执行结算（预计 {{ preview.count || 0 }} 张）</button>
        </template>
      </div>
      <div v-else class="preview-action done">
        <p class="preview-action-tip">本周期已于上方表格冻结快照。此处仍按<b>当前实时榜单</b>演算，仅供对照参考，再次点「重新跑」不会重复发卡。</p>
        <button class="btn ghost preview-go" :disabled="busy" @click="openSnapshot">查看已冻结快照</button>
      </div>
    </section>

    <Teleport to="body"><div v-if="rerunOpen" class="settle-modal-mask" @click.self="!busy&&(rerunOpen=false)"><section class="settle-modal settle-rerun-modal"><div class="settle-modal-title">{{ data.executed?'确认重新跑结算':'确认执行结算' }}<button class="settle-modal-close" :disabled="busy" @click="rerunOpen=false">×</button></div><div class="rerun-summary"><div class="rerun-icon">!</div><div><b>{{ displayWeek }}</b><span v-if="data.executed">该周期已有结算记录，系统将执行幂等校验并跳过重复发放，不会新增卡券。</span><span v-else>将按当前规则发放 {{ preview.count||0 }} 张奖励卡券，确认后不可直接修改结算快照。</span></div></div><div class="rerun-metrics"><span>预计奖励 <b>{{ preview.count||0 }} 张</b></span><span>单次上限 <b>{{ preview.cap||data.cfg?.settleCap||20 }} 张</b></span></div><div v-if="preview.blocked" class="settle-danger-tip">预计发放数量已超过单次上限，请先调整榜单与奖励规则后再执行。</div><div v-else class="settle-info-tip">{{ data.executed?'重新跑不会撤销、补发或重复生成已有奖励。':'系统将依据当前榜单数据生成并冻结本周期结算快照。' }}</div><div v-if="rerunError" class="rerun-error">{{ rerunError }}</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="rerunOpen=false">取消</button><button class="btn pri" :disabled="busy||preview.blocked" @click="rerun">{{ busy?'处理中…':data.executed?'确认重新跑':'确认执行结算' }}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="forceOpen" class="settle-modal-mask" @click.self="!busy&&(forceOpen=false)"><section class="settle-modal settle-force-modal"><div class="settle-modal-title">强制发放超限奖励<button class="settle-modal-close" :disabled="busy" @click="forceOpen=false">×</button></div><div class="settle-danger-tip">本周期 {{ blockedCount }} 张奖励因超过上限被整批拦截。强制发放会一次性全部发出，请确认当前规则配置符合业务预期。</div><label class="settle-field-label force-label">强制发放原因 <i>*必填</i></label><textarea v-model="forceReason" class="inp settle-reason-input" maxlength="100" placeholder="例如：大型赛事周，确认全员并列奖励"></textarea><div v-if="forceError" class="rerun-error">{{ forceError }}</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="forceOpen=false">取消</button><button class="btn dan" :disabled="busy||forceReason.trim().length<2" @click="forceGrant">{{ busy?'处理中…':`确认强制发放 ${blockedCount} 张` }}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="revokeRow" class="settle-modal-mask" @click.self="revokeRow=null"><section class="settle-modal settle-revoke-modal"><div class="settle-modal-title">撤销奖励<button class="settle-modal-close" @click="revokeRow=null">×</button></div><div class="settle-target-summary"><b>{{ revokeRow.nick }}</b><span>{{ revokeRow.target }} · {{ settleRewardText(revokeRow) }}</span></div><label class="settle-field-label">撤销原因 <i>*必填</i></label><textarea v-model="revokeReason" class="inp settle-reason-input" maxlength="100" placeholder="请输入撤销原因，例如：奖励对象录入错误"></textarea><div class="settle-danger-tip">确认后将同步作废对应的未核销卡券；已经核销的卡券不会追回。</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="revokeRow=null">取消</button><button class="btn dan" :disabled="busy || revokeReason.trim().length<2" @click="revoke">{{ busy ? "处理中…" : "确认撤销" }}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="manualOpen" class="settle-modal-mask" @click.self="manualOpen=false"><section class="settle-modal settle-manual-modal"><div class="settle-modal-title">手动补发<button class="settle-modal-close" @click="manualOpen=false">×</button></div><div class="settle-manual-grid"><label><span class="settle-field-label">会员 <i>*必填</i></span><select v-model="manual.uid" class="inp"><option value="">请选择会员</option><option v-for="m in members" :key="m.id" :value="m.id">{{m.nick}} · {{m.no}}</option></select></label><label><span class="settle-field-label">奖励 <i>*必填</i></span><select v-model="manual.tplId" class="inp"><option value="">请选择奖励</option><option v-for="t in templates" :key="t.id" :value="t.id">{{t.name}}</option></select></label></div><label class="settle-field-label">补发原因 <i>*必填</i></label><textarea v-model="manual.reason" class="inp settle-reason-input" maxlength="100" placeholder="例如：结算漏发补偿"></textarea><div class="settle-info-tip">手动补发不受单次自动结算上限约束，操作人和原因会写入日志。</div><div class="settle-modal-actions"><button class="btn ghost" :disabled="busy" @click="manualOpen=false">取消</button><button class="btn pri" :disabled="busy" @click="grantManual">{{busy?'处理中…':'确认补发'}}</button></div></section></div></Teleport>
    <Teleport to="body"><div v-if="snapshot" class="settle-modal-mask" @click.self="snapshot=null"><section class="settle-modal settle-snapshot-modal"><div class="settle-modal-title">结算快照<button class="settle-modal-close" @click="snapshot=null">×</button></div><div class="tiny settle-snapshot-sub">{{ snapshot.week?.replace('~',' ~ ') }} · 共 {{snapshot.total}} 条记录<span v-if="snapshot.executedAt"> · 执行于 {{ snapshot.executedAt }}<template v-if="snapshot.trigger==='auto'">（自动）</template><template v-else-if="snapshot.trigger==='manual'">（手动）</template></span> · 规则修改不会回溯本快照</div><div class="settle-snapshot-list"><div v-for="r in snapshot.rows" :key="r.id" class="settle-snapshot-row"><span><b>{{r.nick}}</b><small>{{r.target}}</small></span><span>{{ settleRewardText(r) }}</span><span class="shard-tag">{{ Number(r.sh||0).toLocaleString('en-US') }} 碎片</span><span class="pill status-pill" :class="`status-${String(r.status).toLowerCase()}`">{{statusText(r.status)}}</span></div></div><div class="settle-modal-actions"><button class="btn ghost" @click="snapshot=null">关闭</button></div></section></div></Teleport>
  </div>
</template>

<style scoped>
.settlement-hdr em{margin-left:auto;text-align:right}.notice{margin-bottom:10px;padding:8px 10px;border-radius:7px;background:var(--greenbg);color:var(--green);font-size:12px}.notice.err{background:var(--redbg);color:var(--red)}.settlement-card{padding:0;overflow:hidden}.settle-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 20px 12px}.settle-summary{display:flex;align-items:center;gap:14px;min-width:0}.summary-copy{color:var(--ink3);font-size:12px}.executed{background:var(--greenbg);color:var(--green);white-space:nowrap}.table-wrap{overflow-x:auto;padding:0 20px}.settlement-table{border-radius:0}.settlement-table th,.settlement-table td{padding:12px 10px}.settlement-table td{height:64px}.settlement-table :is(th,td):nth-child(-n+3){text-align:left}.settlement-table :is(th,td):nth-child(n+4){text-align:center}.settlement-table tr.blocked{background:#FDF3F3}.type-pill{font-size:12px}.type-team{background:var(--greenbg);color:var(--green)}.type-rank1{background:#EEEDFE;color:#534AB7}.type-rank2{background:var(--goldbg);color:var(--gold)}.type-rank3{background:#F1EFE9;color:var(--ink2)}.status-granted{background:var(--greenbg);color:var(--green)}.status-revoked{background:var(--redbg);color:var(--red)}.status-skipped{background:#F1EFE9;color:var(--ink3)}.status-blocked{background:var(--redbg);color:var(--red)}.force-reason{margin-top:2px;color:var(--red)}.revoke-btn{padding:5px 12px}.settle-bottom{display:flex;align-items:center;gap:12px;padding:12px 20px;border-top:1px solid var(--line);background:#fff}.settlement-rule-note{font-size:12px}.blocked-card{background:var(--redbg);border-color:#E24B4A}.blocked-card .st,.blocked-card .st em,.blocked-card p{color:var(--red)}.blocked-card p{margin-bottom:10px;font-size:12px;line-height:1.7}.blocked-card .tiny{margin-left:8px;color:var(--red)}.preview-card{padding:16px 20px;border-color:#534AB7}.preview-card .st{color:#26215C}.preview-rule-link{margin-left:auto;border:0;background:transparent;color:#534AB7;font-size:11px;cursor:pointer}.preview-meta{display:flex;align-items:center;gap:18px;flex-wrap:wrap;color:var(--ink2);font-size:13px}.preview-meta b{font-size:18px;color:#534AB7}.preview-meta b.red{color:var(--red)}.preview-ok{background:var(--greenbg);color:var(--green)}.preview-blocked{background:var(--redbg);color:var(--red)}.preview-detail{margin-top:12px;color:#534AB7;font-size:12px;line-height:1.9}.preview-detail b{color:#26215C}.preview-missing{color:var(--red)}.preview-st{display:flex;align-items:center;gap:8px}.preview-st-note{font-size:11px;font-weight:400;color:var(--ink3)}.preview-action{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line);flex-wrap:wrap}.preview-action.done{background:#FAF9F5;margin:14px -20px -16px;padding:14px 20px 16px;border-top:1px solid var(--line);border-radius:0 0 14px 14px}.preview-action-tip{margin:0;flex:1;min-width:200px;color:var(--ink2);font-size:12px;line-height:1.7}.preview-action-tip.warn{color:var(--red)}.preview-action-tip b{color:var(--ink);font-weight:600}.preview-go{flex:none;white-space:nowrap}.settle-rerun-modal,.settle-force-modal{width:min(520px,100%)}.rerun-summary{display:flex;align-items:flex-start;gap:12px;margin-bottom:15px}.rerun-icon{display:flex;align-items:center;justify-content:center;flex:none;width:32px;height:32px;border-radius:50%;background:var(--goldbg);color:var(--gold);font-size:18px;font-weight:700}.rerun-summary b,.rerun-summary span{display:block}.rerun-summary b{font-size:14px}.rerun-summary span{margin-top:4px;color:var(--ink2);font-size:12px;line-height:1.65}.rerun-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.rerun-metrics span{padding:10px 12px;border-radius:9px;background:#FAF9F5;color:var(--ink2);font-size:12px}.rerun-metrics b{display:block;margin-top:2px;color:var(--ink);font-size:15px}.rerun-error{margin-top:10px;padding:8px 10px;border-radius:7px;background:var(--redbg);color:var(--red);font-size:12px}.force-label{margin-top:14px}
@media(max-width:760px){.settle-head,.settle-summary,.settle-bottom{align-items:flex-start;flex-direction:column}.settle-head .ops{width:100%}}
</style>

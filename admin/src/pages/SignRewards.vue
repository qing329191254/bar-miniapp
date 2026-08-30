<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppSelect from "../components/AppSelect.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const dailyPoints = ref(0), rules = ref<any[]>([]), members = ref<any[]>([]), memberTotal = ref(0);
const membersPage = ref(1);
const membersPageSize = ref(10);
const tpls = ref<any[]>([]);
const selectedId = ref<number | null>(null), showCreate = ref(false), saving = ref(false);
const deleteTarget = ref<any>(null), deleting = ref(false);
const loading = ref(true), loaded = ref(false), err = ref("");
const createForm = ref({ days: null as number | null, pts: 0 });
const blank = () => ({ days: 7, pts: 0, cards: [] as any[], enabled: true });
const form = ref<any>(blank());
const selected = computed(() => selectedId.value === null ? null : rules.value.find((r) => r.id === selectedId.value));
const sortedRules = computed(() => [...rules.value].sort((a, b) => a.days - b.days));
const tplOpts = computed(() => tpls.value.map((t) => ({ value: t.id, label: t.name })));

function tplName(id: number) { return tpls.value.find((t) => t.id === id)?.name || "（卡券已删除）"; }
function rewardText(rule: any) { const p = rule.pts ? `+${Number(rule.pts).toLocaleString("en-US")} 分` : ""; const c = (rule.cards || []).map((x: any) => `${tplName(x.tpl)} ×${x.qty}`).join("、"); return [p, c].filter(Boolean).join(" + ") || "—"; }
function nextRule(member: any) { return sortedRules.value.find((r) => r.enabled !== false && r.days > member.streak); }
function openNew() { createForm.value = { days: null, pts: 0 }; showCreate.value = true; }
function openEdit(rule: any) { selectedId.value = rule.id; form.value = { ...rule, cards: (rule.cards || []).map((x: any) => ({ ...x })) }; }
function closeEdit() { selectedId.value = null; form.value = blank(); }
function addCard() { if (!tpls.value.length) { showToast("请先创建卡券模板", true); return; } form.value.cards.push({ tpl: tpls.value[0].id, qty: 1 }); }
function removeCard(i: number) { form.value.cards.splice(i, 1); }
async function load() {
  loading.value = true;
  err.value = "";
  try {
    const params = pageQs(membersPage.value, membersPageSize.value);
    const [o, t] = await Promise.all([api<any>(`/admin/signin-overview?${params}`), api<any[]>("/admin/cardTpls?pageSize=0")]);
    dailyPoints.value = o.signPoints;
    rules.value = o.rules || [];
    members.value = o.members || [];
    memberTotal.value = o.memberTotal ?? members.value.length;
    tpls.value = t || [];
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "签到奖励加载失败";
    if (loaded.value) showToast(err.value, true);
  } finally {
    loading.value = false;
  }
}

watch([membersPage, membersPageSize], () => load());
async function saveDaily() { try { await api("/admin/signin-config", { method: "PUT", body: { data: { signPoints: Math.max(0, Number(dailyPoints.value || 0)) } } }); showToast("每日签到积分已保存"); } catch (e: any) { showToast(e.message || "保存失败", true); } }
async function createRule() { saving.value = true; try { const saved = await api<any>("/admin/sign-rules", { method: "POST", body: { data: { days: Number(createForm.value.days || 0), pts: Number(createForm.value.pts || 0), cards: [], enabled: true } } }); showCreate.value = false; await load(); openEdit(rules.value.find((r) => r.id === saved.id) || saved); showToast("档位已创建，请继续配置卡券奖励"); } catch (e: any) { showToast(e.message || "创建失败", true); } finally { saving.value = false; } }
async function saveRule() { if (!selected.value) return; saving.value = true; try { const data = { ...form.value, days: Number(form.value.days || 0), pts: Number(form.value.pts || 0), cards: form.value.cards.map((x: any) => ({ tpl: Number(x.tpl), qty: Number(x.qty || 1) })) }; await api(`/admin/sign-rules/${selected.value.id}`, { method: "PUT", body: { data } }); await load(); openEdit(rules.value.find((r) => r.id === selected.value?.id) || selected.value); showToast("连续签到奖励已保存"); } catch (e: any) { showToast(e.message || "保存失败", true); } finally { saving.value = false; } }
async function toggle(rule: any) { try { await api(`/admin/sign-rules/${rule.id}/toggle`, { method: "POST" }); await load(); } catch (e: any) { showToast(e.message || "操作失败", true); } }
function remove(rule: any) { deleteTarget.value = rule; }
async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await api(`/admin/sign-rules/${deleteTarget.value.id}`, { method: "DELETE" });
    if (selectedId.value === deleteTarget.value.id) closeEdit();
    deleteTarget.value = null;
    await load();
    showToast("已删除");
  } catch (e: any) {
    showToast(e.message || "删除失败", true);
  } finally {
    deleting.value = false;
  }
}
onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 0, showNote: true }" @retry="load">
  <div>
    <div class="hdr">签到奖励配置 <em>每日基础奖励 + 连续签到奖励</em></div>
    <div class="sign-layout"><div>
      <section class="card daily-card">
        <div class="st">每日签到</div>
        <div class="daily-field">
          <label class="daily-label">每日签到奖励积分</label>
          <div class="daily-input-wrap">
            <input
              v-model.number="dailyPoints"
              type="number"
              min="0"
              class="inp daily-inp"
              @change="saveDaily"
            />
            <span class="daily-unit">分</span>
          </div>
        </div>
        <div class="tiny daily-hint">签到积分同样受月底清零约束，与对局积分同池。</div>
      </section>
      <section class="card"><div class="list-title"><b>连续签到奖励</b><span class="tiny">达标当天在每日积分之外额外发放</span><button class="btn" @click="openNew">＋ 新增档位</button></div><div class="tb-wrap sign-rules-wrap"><table class="tb2"><thead><tr><th>门槛</th><th>额外积分</th><th>额外卡券</th><th>当前达标</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="rule in sortedRules" :key="rule.id" :style="rule.enabled === false ? 'opacity:.55' : ''"><td><b>连续 {{ rule.days }} 天</b></td><td><b class="blue">{{ rule.pts ? `+${rule.pts} 分` : "—" }}</b></td><td class="tiny">{{ (rule.cards || []).map((x:any) => `${tplName(x.tpl)} ×${x.qty}`).join("、") || "—" }}</td><td>{{ rule.qualified ?? 0 }} 人已达标</td><td><span class="pill" :class="rule.enabled !== false ? 'on' : ''">{{ rule.enabled !== false ? "启用中" : "已停用" }}</span></td><td class="ops"><button class="btn ghost mini" @click="openEdit(rule)">编辑</button><button class="btn ghost mini" @click="toggle(rule)">{{ rule.enabled !== false ? "停用" : "启用" }}</button><button class="btn danger mini" @click="remove(rule)">删除</button></td></tr><tr v-if="!sortedRules.length"><td colspan="6" class="table-empty">暂无连续签到档位，可点击右上角新增</td></tr></tbody></table></div><div class="tiny rule-note">门槛不可重复；奖励可以只给积分、只给卡券，或两者兼有。天数与奖励内容均可自定义，不限于 7 / 30 天。</div></section>
      <section class="side-note multi sign-tips">
        <div class="side-note-body">
          <p><b>发放规则</b></p>
          <p>· 连签奖励与每日积分叠加，达标当天一次性发放</p>
          <p>· 连签天数等于档位值时命中，同一天最多命中一档</p>
          <p>· 断签即归零，从 1 重新累计，不做补签</p>
          <p>· 卡券奖励按模板配置的有效期计算，来源标注「连续签到 N 天」</p>
        </div>
      </section>
    </div><aside>
      <section v-if="selected" class="card edit-card"><div class="st">编辑 · 连续 {{ selected.days }} 天<button class="close" @click="closeEdit">×</button></div><label>连续天数门槛 *<input v-model.number="form.days" type="number" min="1" class="inp" /></label><label>额外奖励积分<input v-model.number="form.pts" type="number" min="0" class="inp" /></label><div class="field-label">额外奖励卡券</div><div v-for="(card, i) in form.cards" :key="i" class="reward-row"><AppSelect v-model="card.tpl" :options="tplOpts" no-margin class="reward-select" /><input v-model.number="card.qty" type="number" min="1" class="inp qty" /><button class="btn ghost mini" @click="removeCard(i)">删</button></div><div v-if="!form.cards.length" class="tiny">未配置卡券奖励，仅发积分</div><button class="btn ghost add-card" @click="addCard">＋ 添加卡券</button><button class="btn submit" :disabled="saving" @click="saveRule">保存规则</button></section>
      <section class="card"><div class="st">连签天数</div><table class="tb2"><thead><tr><th>会员</th><th>已连续</th><th>下一档</th></tr></thead><tbody><tr v-for="member in members" :key="member.id"><td><b>{{ member.nick }}</b></td><td><b :class="member.streak >= 7 ? 'green' : ''">{{ member.streak }} 天</b></td><td class="tiny">{{ nextRule(member) ? `还差 ${nextRule(member).days - member.streak} 天得 ${rewardText(nextRule(member))}` : "已达最高档" }}</td></tr><tr v-if="!members.length"><td colspan="3" class="table-empty">暂无会员连签数据</td></tr></tbody></table><AppPagination v-model:page="membersPage" v-model:page-size="membersPageSize" :total="memberTotal" :sizes="[10, 15, 30]" compact /></section>
    </aside></div>
    <Teleport to="body">
    <div v-if="showCreate" class="create-mask" @click.self="showCreate = false"><section class="create-dialog"><div class="st">新增连续签到档位</div><div class="create-grid"><label>连续天数 *<input v-model.number="createForm.days" type="number" min="1" placeholder="如 14" class="inp" /></label><label>额外奖励积分<input v-model.number="createForm.pts" type="number" min="0" class="inp" /></label></div><div class="tiny">创建后可在右侧继续配置卡券奖励。</div><div class="create-actions"><button class="btn ghost" @click="showCreate = false">取消</button><button class="btn" :disabled="saving" @click="createRule">创建档位</button></div></section></div>
    <div v-if="deleteTarget" class="dlg-mask" @click.self="deleteTarget = null">
      <section class="dlg dlg-confirm">
        <div class="st">删除连续签到档位</div>
        <p class="dlg-body">确认删除连续 <b>{{ deleteTarget.days }}</b> 天奖励？</p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="deleteTarget = null">取消</button>
          <button class="btn dan" :disabled="deleting" @click="confirmDelete">确认删除</button>
        </div>
      </section>
    </div>
    </Teleport>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.sign-layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(360px,1fr);gap:16px;align-items:start}.daily-card{width:100%;box-sizing:border-box}.daily-field{margin-top:4px}.daily-label{display:block;color:var(--ink2);font-size:12px;margin-bottom:6px}.daily-input-wrap{display:inline-flex;align-items:center;gap:8px}.daily-inp{width:88px;margin:0;text-align:center;font-variant-numeric:tabular-nums}.daily-unit{color:var(--ink3);font-size:12px;white-space:nowrap}.daily-hint{margin-top:10px;line-height:1.6}.edit-card label,.create-grid label{display:block;color:var(--ink2);font-size:12px}.edit-card .inp,.create-grid .inp{margin:5px 0 8px}.list-title{display:flex;align-items:center;gap:9px;margin-bottom:12px}.list-title .tiny{flex:1}.mini{padding:5px 9px;font-size:12px}.ops{white-space:nowrap}.ops .btn+.btn{margin-left:4px}.rule-note{margin-top:8px}.field-label{color:var(--ink2);font-size:12px;margin-bottom:5px}.reward-row{display:flex;gap:6px;align-items:center}.reward-row .inp{margin-bottom:6px}.reward-row :deep(.reward-select){flex:1;min-width:0}.reward-row .qty{width:58px}.add-card{margin:1px 0 9px}.submit{width:100%}.sign-tips{background:var(--goldbg);border-color:var(--gold);color:#633806}
.sign-tips::before{background:var(--gold);color:#fff;box-shadow:0 2px 5px rgba(185,120,34,.18)}
.sign-tips b{color:#633806}.close{float:right;border:0;background:transparent;font-size:20px;color:var(--ink2);cursor:pointer}.blue{color:#185FA5}.green{color:#3B6D11}.pill.on{color:#3B6D11}.create-dialog{width:min(720px,100%);background:#fff;border-radius:16px;padding:24px;box-shadow:0 18px 45px rgba(0,0,0,.2)}.create-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.create-actions{display:grid;grid-template-columns:1fr 1.6fr;gap:10px;margin-top:20px}.create-actions .btn{width:100%}.dlg{width:min(400px,100%);background:#fff;border-radius:16px;padding:24px;box-shadow:0 18px 45px rgba(0,0,0,.2)}.dlg .st{margin-bottom:12px}.dlg-body{font-size:13px;line-height:1.65;margin:0;color:var(--ink2)}.dlg-actions{display:grid;grid-template-columns:1fr 1.6fr;gap:10px;margin-top:18px}.dlg-actions .btn{width:100%}.tb-wrap{overflow-x:auto}.sign-rules-wrap .tb2 :is(th,td):nth-child(5),.sign-rules-wrap .tb2 :is(th,td):nth-child(6){text-align:center}.sign-rules-wrap .tb2 td.ops{display:flex;justify-content:center;flex-wrap:wrap;gap:4px}@media(max-width:960px){.sign-layout{grid-template-columns:1fr}}
</style>

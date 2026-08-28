<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, savedUser } from "../api";

const isBoss = savedUser()?.role === "BOSS";
const dailyPoints = ref(0);
const rules = ref<any[]>([]);
const members = ref<any[]>([]);
const tpls = ref<any[]>([]);
const selectedId = ref<number | null>(null);
const msg = ref("");
const saving = ref(false);
const blank = () => ({ days: 7, pts: 0, cards: [] as any[], enabled: true });
const form = ref<any>(blank());
const selected = computed(() => selectedId.value === null ? null : rules.value.find((r) => r.id === selectedId.value));
const sortedRules = computed(() => [...rules.value].sort((a, b) => a.days - b.days));

function tplName(id: number) { return tpls.value.find((t) => t.id === id)?.name || "（卡券已删除）"; }
function rewardText(rule: any) {
  const pts = Number(rule.pts || 0) ? `+${Number(rule.pts).toLocaleString("en-US")} 分` : "";
  const cards = (rule.cards || []).map((c: any) => `${tplName(c.tpl)} ×${c.qty}`).join("、");
  return [pts, cards].filter(Boolean).join(" + ") || "—";
}
function nextRule(member: any) { return sortedRules.value.find((r) => r.enabled !== false && r.days > member.streak); }
function openNew() { selectedId.value = null; form.value = blank(); msg.value = ""; }
function openEdit(rule: any) { selectedId.value = rule.id; form.value = { ...rule, cards: (rule.cards || []).map((c: any) => ({ ...c })) }; msg.value = ""; }
function addCard() { if (!tpls.value.length) { msg.value = "请先创建卡券模板"; return; } form.value.cards.push({ tpl: tpls.value[0].id, qty: 1 }); }
function removeCard(index: number) { form.value.cards.splice(index, 1); }
async function load() {
  const [overview, templates] = await Promise.all([api<any>("/admin/signin-overview"), api<any[]>("/admin/cardTpls")]);
  dailyPoints.value = overview.signPoints;
  rules.value = overview.rules || [];
  members.value = overview.members || [];
  tpls.value = templates || [];
}
async function saveDaily() {
  saving.value = true; msg.value = "";
  try { await api("/admin/config", { method: "PUT", body: { data: { signPoints: Math.max(0, Number(dailyPoints.value || 0)) } } }); msg.value = "每日签到积分已保存"; }
  catch (e: any) { msg.value = e.message || "保存失败"; }
  finally { saving.value = false; }
}
async function saveRule() {
  saving.value = true; msg.value = "";
  try {
    const data = { ...form.value, days: Number(form.value.days || 0), pts: Number(form.value.pts || 0), cards: form.value.cards.map((c: any) => ({ tpl: Number(c.tpl), qty: Number(c.qty || 1) })) };
    const saved = selected.value ? await api<any>(`/admin/sign-rules/${selected.value.id}`, { method: "PUT", body: { data } }) : await api<any>("/admin/sign-rules", { method: "POST", body: { data } });
    await load(); openEdit(rules.value.find((r) => r.id === saved.id) || saved); msg.value = "连续签到奖励已保存";
  } catch (e: any) { msg.value = e.message || "保存失败"; }
  finally { saving.value = false; }
}
async function toggle(rule: any) { try { await api(`/admin/sign-rules/${rule.id}/toggle`, { method: "POST" }); await load(); } catch (e: any) { msg.value = e.message || "操作失败"; } }
async function remove(rule: any) { if (!window.confirm(`确认删除连续 ${rule.days} 天奖励？`)) return; try { await api(`/admin/sign-rules/${rule.id}`, { method: "DELETE" }); if (selectedId.value === rule.id) openNew(); await load(); } catch (e: any) { msg.value = e.message || "删除失败"; } }
onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">签到奖励配置 <em>每日基础奖励 + 连续签到奖励</em></div>
    <div v-if="msg" class="notice">{{ msg }}</div>
    <div class="sign-layout">
      <div>
        <section class="card daily-card"><div class="st">每日签到</div><label>每日签到奖励积分<input v-model.number="dailyPoints" :disabled="!isBoss" type="number" min="0" class="inp" /></label><button v-if="isBoss" class="btn" :disabled="saving" @click="saveDaily">保存</button><div class="tiny">签到积分同样受月底清零约束，与对局积分同池。</div></section>
        <section class="card"><div class="list-title"><b>连续签到奖励</b><span class="tiny">达标当天在每日积分之外额外发放</span><button v-if="isBoss" class="btn" @click="openNew">＋ 新增档位</button></div>
          <div class="tb-wrap"><table class="tb2"><thead><tr><th>门槛</th><th>额外积分</th><th>额外卡券</th><th>当前达标</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="rule in sortedRules" :key="rule.id" :style="rule.enabled === false ? 'opacity:.55' : ''"><td><b>连续 {{ rule.days }} 天</b></td><td><b style="color:#185FA5">{{ rule.pts ? `+${rule.pts} 分` : "—" }}</b></td><td class="tiny">{{ (rule.cards || []).map((c:any) => `${tplName(c.tpl)} ×${c.qty}`).join("、") || "—" }}</td><td>{{ members.filter((m) => m.streak >= rule.days).length }} 人已达标</td><td><span class="pill" :style="{ color: rule.enabled !== false ? '#3B6D11' : '#9C9A93' }">{{ rule.enabled !== false ? "启用中" : "已停用" }}</span></td><td class="ops"><button class="btn ghost mini" @click="openEdit(rule)">编辑</button><button class="btn ghost mini" @click="toggle(rule)">{{ rule.enabled !== false ? "停用" : "启用" }}</button><button v-if="isBoss" class="btn danger mini" @click="remove(rule)">删除</button></td></tr></tbody></table></div>
          <div class="tiny rule-note">门槛不可重复；奖励可以只给积分、只给卡券，或两者兼有。天数与奖励内容均可自定义，不限于 7 / 30 天。</div>
        </section>
      </div>
      <aside>
        <section class="card edit-card"><div class="st">{{ selected ? `编辑 · 连续 ${selected.days} 天` : "新增档位" }}</div><label>连续天数门槛 *<input v-model.number="form.days" :disabled="!isBoss" type="number" min="1" class="inp" /></label><label>额外奖励积分<input v-model.number="form.pts" :disabled="!isBoss" type="number" min="0" class="inp" /></label><div class="field-label">额外奖励卡券</div><div v-for="(card, index) in form.cards" :key="index" class="reward-row"><select v-model.number="card.tpl" :disabled="!isBoss" class="inp"><option v-for="tpl in tpls" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option></select><input v-model.number="card.qty" :disabled="!isBoss" type="number" min="1" class="inp qty" /><button v-if="isBoss" class="btn ghost mini" @click="removeCard(index)">删</button></div><div v-if="!form.cards.length" class="tiny">未配置卡券奖励，仅发积分</div><button v-if="isBoss" class="btn ghost add-card" @click="addCard">＋ 添加卡券</button><button v-if="isBoss" class="btn submit" :disabled="saving" @click="saveRule">{{ selected ? "保存规则" : "创建档位" }}</button></section>
        <section class="card"><div class="st">连签天数</div><table class="tb2"><thead><tr><th>会员</th><th>已连续</th><th>下一档</th></tr></thead><tbody><tr v-for="member in members" :key="member.id"><td><b>{{ member.nick }}</b></td><td><b :style="{ color: member.streak >= 7 ? '#3B6D11' : '' }">{{ member.streak }} 天</b></td><td class="tiny">{{ nextRule(member) ? `还差 ${nextRule(member).days - member.streak} 天得 ${rewardText(nextRule(member))}` : "已达最高档" }}</td></tr></tbody></table></section>
        <section class="note sign-tips"><b>发放规则</b><br>· 连签奖励与每日积分叠加，达标当天一次性发放<br>· 连签天数等于档位值时命中，同一天最多命中一档<br>· 断签即归零，从 1 重新累计，不做补签<br>· 卡券奖励按模板配置的有效期计算，来源标注“连续签到 N 天”</section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.sign-layout { display:grid; grid-template-columns:minmax(0,1fr) 360px; gap:12px; align-items:start; }
.daily-card { max-width:700px; }.daily-card label,.edit-card label { display:block; color:var(--ink2); font-size:12px; }.daily-card .inp,.edit-card .inp { margin:5px 0 8px; }.daily-card .btn { margin:0 0 8px; }
.list-title { display:flex; align-items:center; gap:9px; margin-bottom:12px; }.list-title .tiny { flex:1; }.mini { padding:5px 9px; font-size:12px; }.ops { white-space:nowrap; }.ops .btn + .btn { margin-left:4px; }.rule-note { margin-top:8px; }.field-label { color:var(--ink2); font-size:12px; margin-bottom:5px; }.reward-row { display:flex; gap:6px; align-items:center; }.reward-row .inp { margin-bottom:6px; }.reward-row select { flex:1; }.reward-row .qty { width:58px; }.add-card { margin:1px 0 9px; }.submit { width:100%; }.notice { color:var(--green); font-size:12px; margin-bottom:8px; }.sign-tips { background:var(--goldbg); border:1px solid var(--gold); color:#633806; padding:12px; }
@media(max-width:960px) { .sign-layout { grid-template-columns:1fr; } }
</style>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";

const teams = ref<any[]>([]), unassigned = ref<any[]>([]), msg = ref("");
const showNew = ref(false), teamName = ref(""), editing = ref<any>(null), editName = ref("");
async function load() { const data = await api<any>("/admin/team-management"); teams.value = data.teams || []; unassigned.value = data.unassigned || []; }
function notify(text: string) { msg.value = text; window.setTimeout(() => { if (msg.value === text) msg.value = ""; }, 2200); }
async function createTeam() { try { await api("/admin/teams", { method: "POST", body: { data: { name: teamName.value } } }); teamName.value = ""; showNew.value = false; await load(); notify("战队已新增"); } catch (e: any) { notify(e.message || "新增失败"); } }
function startEdit(team: any) { editing.value = team; editName.value = team.name; }
async function saveName() { try { await api(`/admin/teams/${editing.value.id}`, { method: "PUT", body: { data: { name: editName.value } } }); editing.value = null; await load(); notify("战队名称已更新"); } catch (e: any) { notify(e.message || "保存失败"); } }
async function move(member: any, team: any, event: Event) { const value = Number((event.target as HTMLSelectElement).value || 0) || null; if (value === team.id) return; const target = teams.value.find((x) => x.id === value); const label = target ? target.name : "未分配"; if (!window.confirm(`确认将 ${member.nick} 调整至「${label}」？`)) return; try { await api("/admin/team-members/move", { method: "POST", body: { data: { uid: member.id, teamId: value } } }); await load(); notify("成员已调整"); } catch (e: any) { notify(e.message || "调整失败"); } }
async function remove(member: any) { if (!window.confirm(`确认将 ${member.nick} 移出当前战队？`)) return; try { await api("/admin/team-members/move", { method: "POST", body: { data: { uid: member.id, teamId: null } } }); await load(); notify("成员已移出"); } catch (e: any) { notify(e.message || "移出失败"); } }
onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">战队管理 <em>支持新增、编辑、调队二次确认</em></div>
    <div v-if="msg" class="notice">{{ msg }}</div>
    <div class="toolbar"><button class="btn" @click="showNew = true">＋ 新增战队</button><span class="tiny">新增后成员可通过「调至」下拉选择加入</span></div>
    <section v-for="team in teams" :key="team.id" class="card team-card">
      <div class="team-head"><b>{{ team.name }}</b><span class="tiny">{{ team.members.length }} 名成员 · 战队冠军 {{ team.champions }}（实时聚合）</span><button class="btn ghost mini" @click="startEdit(team)">编辑</button></div>
      <div class="tb-wrap"><table class="tb2" data-cols="lcccc"><thead><tr><th>成员</th><th>个人冠军</th><th>本周碎片</th><th>调至</th><th>操作</th></tr></thead><tbody><tr v-for="member in team.members" :key="member.id"><td><b>{{ member.nick }}</b><div class="tiny">{{ member.no }}</div></td><td>{{ member.champions }}</td><td>{{ member.shard.toLocaleString("en-US") }}</td><td><select class="select" :value="team.id" @change="move(member, team, $event)"><option :value="team.id">当前战队</option><option v-for="item in teams.filter(x => x.id !== team.id)" :key="item.id" :value="item.id">{{ item.name }}</option><option value="">未分配</option></select></td><td><button class="btn ghost mini" @click="remove(member)">移出</button></td></tr><tr v-if="!team.members.length"><td colspan="5" class="empty-row">暂无成员</td></tr></tbody></table></div>
    </section>
    <section v-if="!teams.length" class="card list-empty">暂无战队，可使用上方按钮创建</section>
    <section v-if="unassigned.length" class="card unassigned"><div class="st">未分配战队成员</div><div class="member-tags"><span v-for="u in unassigned" :key="u.id">{{ u.nick }} · {{ u.no }}</span></div></section>
    <div class="note">调队后，冠军数与周碎片会按成员当前战队实时聚合；已发放的历史奖励不受影响。</div>
    <div v-if="showNew" class="mask" @click.self="showNew = false"><section class="dialog"><div class="st">新增战队</div><label>战队名称<input v-model.trim="teamName" class="inp" placeholder="如 周末桌游组" @keyup.enter="createTeam" /></label><div class="actions"><button class="btn ghost" @click="showNew = false">取消</button><button class="btn" @click="createTeam">创建战队</button></div></section></div>
    <div v-if="editing" class="mask" @click.self="editing = null"><section class="dialog"><div class="st">编辑战队</div><label>战队名称<input v-model.trim="editName" class="inp" @keyup.enter="saveName" /></label><div class="actions"><button class="btn ghost" @click="editing = null">取消</button><button class="btn" @click="saveName">保存</button></div></section></div>
  </div>
</template>

<style scoped>
.toolbar,.team-head{display:flex;align-items:center;gap:10px;margin-bottom:12px}.team-head .tiny{margin-left:auto}.team-card{margin-bottom:12px}.mini{padding:5px 10px;font-size:12px}.select{width:220px;max-width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}.notice{color:var(--green);font-size:12px;margin-bottom:8px}.empty-row{text-align:center;color:var(--ink2);padding:18px}.unassigned{margin-top:12px}.member-tags{display:flex;flex-wrap:wrap;gap:8px}.member-tags span{padding:6px 9px;background:var(--paper);border-radius:8px;color:var(--ink2);font-size:12px}.mask{position:fixed;z-index:30;inset:0;display:grid;place-items:center;padding:20px;background:rgba(0,0,0,.38)}.dialog{width:min(460px,100%);padding:22px;background:#fff;border-radius:16px;box-shadow:0 18px 45px rgba(0,0,0,.2)}.dialog label{display:block;color:var(--ink2);font-size:12px}.dialog .inp{margin-top:6px}.actions{display:grid;grid-template-columns:1fr 1.5fr;gap:10px;margin-top:18px}.actions .btn{width:100%}@media(max-width:720px){.select{width:150px}.team-head{align-items:flex-start}.team-head .tiny{margin-left:0;flex:1}.tb-wrap{overflow-x:auto}}
</style>

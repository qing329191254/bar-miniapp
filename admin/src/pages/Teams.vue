<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppSelect from "../components/AppSelect.vue";
import { showToast } from "../composables/useToast";

type Member = { id: number; nick: string; no: string; champions: number; shard: number };
type Team = {
  id: number;
  name: string;
  logo?: string;
  status?: string;
  members: Member[];
  champions: number;
  shard: number;
};

const teams = ref<Team[]>([]);
const loading = ref(true);
const err = ref("");
const acting = ref(false);

const showNew = ref(false);
const newForm = ref({ name: "", logo: "" });

const editing = ref<Team | null>(null);
const editForm = ref({ name: "", status: "ACTIVE" });

const moveDlg = ref<{ member: Member; from: Team; to: Team } | null>(null);
const removeDlg = ref<Member | null>(null);

const activeTeams = computed(() => teams.value.filter((t) => t.status !== "DISABLED"));

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<{ teams: Team[] }>("/admin/team-management");
    teams.value = data.teams || [];
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    teams.value = [];
  } finally {
    loading.value = false;
  }
}

function openNew() {
  newForm.value = { name: "", logo: "" };
  showNew.value = true;
}

async function createTeam() {
  const name = newForm.value.name.trim();
  if (!name) {
    showToast("请填写战队名称", true);
    return;
  }
  acting.value = true;
  try {
    await api("/admin/teams", {
      method: "POST",
      body: { data: { name, logo: (newForm.value.logo.trim() || name[0] || "队")[0] } },
    });
    showNew.value = false;
    await load();
    showToast("已新增");
  } catch (e: any) {
    showToast(e?.message || "新增失败", true);
  } finally {
    acting.value = false;
  }
}

function openEdit(team: Team) {
  editing.value = team;
  editForm.value = { name: team.name, status: team.status || "ACTIVE" };
}

async function saveTeam() {
  if (!editing.value) return;
  const name = editForm.value.name.trim();
  if (!name) {
    showToast("请填写战队名称", true);
    return;
  }
  acting.value = true;
  try {
    await api(`/admin/teams/${editing.value.id}`, {
      method: "PUT",
      body: { data: { name, status: editForm.value.status } },
    });
    editing.value = null;
    await load();
    showToast("已保存");
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    acting.value = false;
  }
}

function moveTeamOptions(from: Team) {
  return activeTeams.value.filter((x) => x.id !== from.id).map((t) => ({ value: t.id, label: t.name }));
}

function onMoveSelect(member: Member, from: Team, teamId: number) {
  const value = Number(teamId || 0);
  if (!value) return;
  const to = teams.value.find((t) => t.id === value);
  if (!to || to.id === from.id) return;
  moveDlg.value = { member, from, to };
}

function movePreview() {
  if (!moveDlg.value) return null;
  const { member, from, to } = moveDlg.value;
  return {
    fromBefore: from.champions,
    fromAfter: from.champions - member.champions,
    toBefore: to.champions,
    toAfter: to.champions + member.champions,
  };
}

async function confirmMove() {
  if (!moveDlg.value) return;
  acting.value = true;
  try {
    await api("/admin/team-members/move", {
      method: "POST",
      body: { data: { uid: moveDlg.value.member.id, teamId: moveDlg.value.to.id } },
    });
    moveDlg.value = null;
    await load();
    showToast("已调队");
  } catch (e: any) {
    showToast(e?.message || "调队失败", true);
  } finally {
    acting.value = false;
  }
}

async function confirmRemove() {
  if (!removeDlg.value) return;
  acting.value = true;
  try {
    await api("/admin/team-members/move", {
      method: "POST",
      body: { data: { uid: removeDlg.value.id, teamId: null } },
    });
    removeDlg.value = null;
    await load();
    showToast("已移出");
  } catch (e: any) {
    showToast(e?.message || "移出失败", true);
  } finally {
    acting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'detail', showFilter: false, metrics: 0, tableCols: 5, showNote: true }" @retry="load">
    <div>
      <div class="hdr teams-hdr">
        <span class="hdr-title">战队管理</span>
        <em class="hdr-note">支持新增 / 编辑 · 调队二次确认</em>
      </div>
      <div class="toolbar row">
        <button class="btn sm pri" @click="openNew">＋ 新增战队</button>
        <span class="tiny">新增后成员可通过「调至」下拉选择加入</span>
      </div>

      <section v-for="team in teams" :key="team.id" class="card team-card">
        <div class="team-head">
          <div class="team-head-main">
            <span class="team-name">
              {{ team.name }}
              <span v-if="team.status === 'DISABLED'" class="disabled-tag">（已停用）</span>
            </span>
            <em class="team-stats">{{ team.members.length }} 名成员 · 战队冠军 {{ team.champions }}（实时聚合）</em>
          </div>
          <button class="btn sm ghost edit-btn" @click="openEdit(team)">编辑</button>
        </div>
        <div class="tb-wrap">
          <table class="tb2 team-member-table">
            <thead>
              <tr>
                <th style="width:30%">成员</th>
                <th style="width:16%">个人冠军</th>
                <th style="width:16%">本周碎片</th>
                <th style="width:20%">调至</th>
                <th style="width:18%">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="member in team.members" :key="member.id">
                <td><b>{{ member.nick }}</b><div class="tiny">{{ member.no }}</div></td>
                <td>{{ member.champions }}</td>
                <td>{{ fmt(member.shard) }}</td>
                <td>
                  <AppSelect
                    class="move-sel"
                    :model-value="0"
                    :options="moveTeamOptions(team)"
                    placeholder="选择战队"
                    compact
                    no-margin
                    action
                    @change="onMoveSelect(member, team, $event)"
                  />
                </td>
                <td><button class="btn sm" @click="removeDlg = member">移出</button></td>
              </tr>
              <tr v-if="!team.members.length">
                <td colspan="5" class="empty-row">暂无成员</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="!teams.length" class="card list-empty">暂无战队，可使用上方按钮创建</section>

      <div class="side-note">
        <div class="side-note-body">
          <b>调队后果：</b>冠军数归属新战队且实时聚合，拖一个人会同时改变两个战队的排名。已发放的历史奖励不受影响（依据快照）。停用的战队不再出现在调队目标中。
        </div>
      </div>
    </div>

    <Teleport to="body">
    <div v-if="showNew" class="dlg-mask" @click.self="showNew = false">
      <section class="dlg">
        <div class="st">新增战队</div>
        <div class="fld">战队名称 *</div>
        <input v-model="newForm.name" class="inp" placeholder="如 冠军收割机" />
        <div class="fld">队标（文字，用于榜单展示）</div>
        <input v-model="newForm.logo" class="inp" placeholder="如 冠" maxlength="1" />
        <div class="dlg-actions">
          <button class="btn ghost" @click="showNew = false">取消</button>
          <button class="btn pri" :disabled="acting" @click="createTeam">创建战队</button>
        </div>
      </section>
    </div>

    <div v-if="editing" class="dlg-mask" @click.self="editing = null">
      <section class="dlg">
        <div class="st">编辑战队</div>
        <div class="fld">战队名称</div>
        <input v-model="editForm.name" class="inp" />
        <div class="status-row">
          <span class="tiny">状态</span>
          <span class="chip" :class="{ on: editForm.status !== 'DISABLED' }" @click="editForm.status = 'ACTIVE'">启用</span>
          <span class="chip" :class="{ on: editForm.status === 'DISABLED' }" @click="editForm.status = 'DISABLED'">停用</span>
        </div>
        <div class="dlg-actions">
          <button class="btn ghost" @click="editing = null">取消</button>
          <button class="btn" :disabled="acting" @click="saveTeam">保存</button>
        </div>
      </section>
    </div>

    <div v-if="moveDlg" class="dlg-mask" @click.self="moveDlg = null">
      <section class="dlg">
        <div class="st">调队二次确认</div>
        <p class="dlg-body">
          将「<b>{{ moveDlg.member.nick }}</b>」从【{{ moveDlg.from.name }}】调至【{{ moveDlg.to.name }}】：<br />
          · {{ moveDlg.from.name }}冠军数 <b class="down">{{ movePreview()?.fromBefore }} → {{ movePreview()?.fromAfter }}</b><br />
          · {{ moveDlg.to.name }}冠军数 <b class="up">{{ movePreview()?.toBefore }} → {{ movePreview()?.toAfter }}</b><br />
          · 将影响后续战队榜排名<br />
          · <b>已发放的历史奖励不受影响</b>（依据快照）
        </p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="moveDlg = null">取消</button>
          <button class="btn pri" :disabled="acting" @click="confirmMove">确认调队</button>
        </div>
      </section>
    </div>

    <div v-if="removeDlg" class="dlg-mask" @click.self="removeDlg = null">
      <section class="dlg">
        <div class="st">移出战队</div>
        <p class="dlg-body">确认将 <b>{{ removeDlg.nick }}</b> 移出当前战队？</p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="removeDlg = null">取消</button>
          <button class="btn dan" :disabled="acting" @click="confirmRemove">确认移出</button>
        </div>
      </section>
    </div>
    </Teleport>
  </AppAsyncPage>
</template>

<style scoped>
.teams-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  text-align: right;
  pointer-events: auto;
  white-space: normal;
}
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.team-card { margin-bottom: 12px; padding-bottom: 0; overflow: hidden; }
.team-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.team-head-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}
.team-name {
  font-size: 14px;
  font-weight: 650;
  color: #352d24;
}
.team-stats {
  margin: 0;
  font-style: normal;
  font-size: 11px;
  color: var(--ink3);
  font-weight: 400;
}
.edit-btn { flex: none; margin: 0; }
.team-member-table :is(th, td):nth-child(5) { text-align: center; }
.disabled-tag { color: var(--red); font-size: 12px; font-weight: 400; }
.tb-wrap { overflow-x: auto; }
.move-sel { max-width: 180px; }
.empty-row { text-align: center; color: var(--ink3); padding: 18px; font-size: 12px; }
.list-empty { text-align: center; color: var(--ink2); padding: 24px; }
.dlg {
  width: min(520px, 100%); background: #fff; border-radius: 16px; padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.fld { color: var(--ink2); font-size: 12px; margin: 8px 0 4px; }
.dlg .inp { width: 100%; margin-bottom: 4px; }
.status-row { display: flex; align-items: center; gap: 8px; margin: 12px 0 4px; }
.dlg-body { font-size: 13px; line-height: 1.65; margin: 8px 0 4px; }
.down { color: var(--red); }
.up { color: var(--green); }
.dlg-actions { display: grid; grid-template-columns: 1fr 1.6fr; gap: 10px; margin-top: 18px; }
.dlg-actions .btn { width: 100%; }
@media (max-width: 720px) {
  .team-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
  .team-head-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>

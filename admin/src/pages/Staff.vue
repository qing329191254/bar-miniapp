<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppSelect from "../components/AppSelect.vue";
import { showToast } from "../composables/useToast";

type StaffRow = {
  id: number;
  no: string;
  nick: string;
  phone: string;
  role: string;
  status: string;
  orders: number;
  amount: number;
  verifies: number;
};

const rows = ref<StaffRow[]>([]);
const loading = ref(true);
const err = ref("");
const acting = ref(false);

const addForm = ref({ phone: "", nick: "", role: "STAFF" });
const showAdd = ref(false);

const roleDlg = ref<{ row: StaffRow; role: string; reason: string } | null>(null);
const disableDlg = ref<StaffRow | null>(null);

const ROLE_OPTS = [
  { value: "STAFF", label: "店员" },
  { value: "MANAGER", label: "店长" },
];
const ROLE_NAME: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<{ rows: StaffRow[] }>("/admin/staff-page");
    rows.value = data.rows || [];
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

async function addStaff() {
  const phone = addForm.value.phone.trim();
  if (!phone) {
    showToast("请填写手机号", true);
    return;
  }
  acting.value = true;
  try {
    await api("/admin/staff", {
      method: "POST",
      body: { data: { phone, nick: addForm.value.nick.trim(), role: addForm.value.role } },
    });
    addForm.value = { phone: "", nick: "", role: "STAFF" };
    showAdd.value = false;
    await load();
    showToast("已添加，该手机号登录后自动识别为员工");
  } catch (e: any) {
    showToast(e?.message || "添加失败", true);
  } finally {
    acting.value = false;
  }
}

function openAdd() {
  addForm.value = { phone: "", nick: "", role: "STAFF" };
  showAdd.value = true;
}

function onRoleChange(row: StaffRow, role: string) {
  if (role === "BOSS" || row.role === "BOSS") {
    showToast("老板角色不可在此变更", true);
    return;
  }
  if (role === row.role) return;
  roleDlg.value = { row, role, reason: "" };
}

function roleDlgBody() {
  if (!roleDlg.value) return "";
  const { row, role } = roleDlg.value;
  const from = ROLE_NAME[row.role] || row.role;
  const to = ROLE_NAME[role] || role;
  const hint =
    role === "MANAGER"
      ? "店长可见订单/充值/对局/结算等管理页，但资金规则仍归老板"
      : "店员仅保留移动端待办、核销与录对局权限";
  return `将「${row.nick}」的角色由【${from}】变更为【${to}】。\n· ${hint}\n· 变更即时生效，并记入操作日志`;
}

async function confirmRole() {
  if (!roleDlg.value) return;
  const reason = roleDlg.value.reason.trim();
  if (reason.length < 2) {
    showToast("请填写原因", true);
    return;
  }
  acting.value = true;
  try {
    await api(`/admin/staff/${roleDlg.value.row.id}/role`, {
      method: "PUT",
      body: { data: { role: roleDlg.value.role, reason } },
    });
    roleDlg.value = null;
    await load();
    showToast("角色已变更，已记入日志");
  } catch (e: any) {
    showToast(e?.message || "变更失败", true);
  } finally {
    acting.value = false;
  }
}

async function confirmDisable() {
  if (!disableDlg.value) return;
  acting.value = true;
  try {
    await api(`/admin/staff/${disableDlg.value.id}/disable`, { method: "POST" });
    disableDlg.value = null;
    await load();
    showToast("已停用，立即失效，历史记录保留");
  } catch (e: any) {
    showToast(e?.message || "停用失败", true);
  } finally {
    acting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'table', showFilter: false, metrics: 0, tableCols: 7, showNote: false }" @retry="load">
    <div>
      <div class="hdr staff-hdr">
        <span class="hdr-title">员工与权限</span>
        <em class="hdr-note">员工账号由老板统一添加与管理</em>
      </div>
      <div class="toolbar row">
        <button class="btn sm pri" @click="openAdd">＋ 新增员工</button>
        <span class="tiny">该手机号登录后自动识别为员工</span>
      </div>
      <div class="card tb-wrap">
        <table class="tb2 staff-table" data-cols="llccccc">
          <thead>
            <tr>
              <th>姓名</th>
              <th>手机号</th>
              <th>角色</th>
              <th>接单</th>
              <th>收款额</th>
              <th>核销</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>
                <b class="name">{{ row.nick }}</b>
                <span v-if="row.status === 'DISABLED'" class="disabled-tag">已停用</span>
              </td>
              <td>{{ row.phone }}</td>
              <td>
                <span v-if="row.role === 'BOSS'" class="pill boss-pill">老板</span>
                <AppSelect
                  v-else
                  class="role-sel"
                  :model-value="row.role"
                  :options="ROLE_OPTS"
                  compact
                  no-margin
                  action
                  :disabled="row.status === 'DISABLED'"
                  @change="onRoleChange(row, $event)"
                />
              </td>
              <td>{{ row.orders }}</td>
              <td>¥{{ fmt(row.amount) }}</td>
              <td>{{ row.verifies }}</td>
              <td>
                <button
                  v-if="row.status !== 'DISABLED' && row.role !== 'BOSS'"
                  class="btn sm"
                  :disabled="acting"
                  @click="disableDlg = row"
                >
                  停用
                </button>
                <span v-else-if="row.status === 'DISABLED'" class="mut">—</span>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="7" class="empty-row">暂无员工，可点击上方按钮添加</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showAdd" class="dlg-mask" @click.self="showAdd = false">
        <section class="dlg">
          <div class="st">新增员工</div>
          <div class="fld">手机号 *</div>
          <input v-model="addForm.phone" class="inp" placeholder="11 位手机号" />
          <div class="fld">姓名</div>
          <input v-model="addForm.nick" class="inp" placeholder="如 小玲" />
          <div class="fld">角色</div>
          <AppSelect v-model="addForm.role" :options="ROLE_OPTS" no-margin />
          <div class="dlg-actions">
            <button class="btn ghost" @click="showAdd = false">取消</button>
            <button class="btn pri" :disabled="acting" @click="addStaff">添加员工</button>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="roleDlg" class="dlg-mask" @click.self="roleDlg = null">
        <section class="dlg">
          <div class="st">变更员工角色</div>
          <p class="dlg-body">{{ roleDlgBody() }}</p>
          <div class="fld">变更原因（必填）</div>
          <input v-model="roleDlg.reason" class="inp" placeholder="请填写原因" />
          <div class="dlg-actions">
            <button class="btn ghost" @click="roleDlg = null">取消</button>
            <button class="btn dan" :disabled="acting" @click="confirmRole">确认变更</button>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="disableDlg" class="dlg-mask" @click.self="disableDlg = null">
        <section class="dlg dlg-confirm">
          <div class="st">停用员工</div>
          <p class="dlg-body">确认停用「<b>{{ disableDlg.nick }}</b>」？停用后立即无法登录，历史记录保留。</p>
          <div class="dlg-actions">
            <button class="btn ghost" @click="disableDlg = null">取消</button>
            <button class="btn dan" :disabled="acting" @click="confirmDisable">确认停用</button>
          </div>
        </section>
      </div>
    </Teleport>
  </AppAsyncPage>
</template>

<style scoped>
.staff-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.staff-table { table-layout: fixed; min-width: 720px; }
.staff-table :is(th,td):nth-child(1){width:14%}
.staff-table :is(th,td):nth-child(2){width:16%}
.staff-table :is(th,td):nth-child(3){width:14%}
.staff-table :is(th,td):nth-child(4){width:10%}
.staff-table :is(th,td):nth-child(5){width:12%}
.staff-table :is(th,td):nth-child(6){width:10%}
.staff-table :is(th,td):nth-child(7){width:12%}
.staff-table td.col-op { white-space: nowrap; }
.tb-wrap { padding: 0; overflow: auto; }
.name { font-weight: 500; }
.disabled-tag { margin-left: 6px; color: var(--red); font-size: 11px; font-weight: 400; }
.boss-pill { background: var(--goldbg); color: var(--gold); }
.role-sel { max-width: 72px; margin: 0 auto; }
.empty-row { text-align: center; color: var(--ink3); padding: 24px; font-size: 12px; }
.mut { color: var(--ink3); font-size: 12px; }
.dlg {
  width: min(480px, 100%); background: #fff; border-radius: 14px; padding: 20px 22px;
  border: 1px solid var(--line); box-shadow: 0 20px 60px rgba(28, 27, 25, 0.24);
}
.dlg-confirm { width: min(400px, 100%); }
.dlg .st { margin-bottom: 12px; }
.fld { color: var(--ink2); font-size: 12px; margin: 8px 0 4px; }
.dlg .inp { width: 100%; margin-bottom: 4px; }
.dlg-body { font-size: 13px; line-height: 1.65; margin: 0 0 4px; color: var(--ink2); white-space: pre-line; }
.dlg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}
.dlg-actions .btn { min-width: 96px; margin: 0; }
@media (max-width: 640px) {
  .dlg-actions { flex-direction: column-reverse; }
  .dlg-actions .btn { width: 100%; min-width: 0; }
}
</style>

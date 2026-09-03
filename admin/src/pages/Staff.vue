<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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

const addForm = ref({ phone: "", nick: "", role: "STAFF", password: "", password2: "" });
const showAdd = ref(false);
const addNeedsPwd = computed(() => addForm.value.role === "MANAGER");

const roleDlg = ref<{
  row: StaffRow;
  role: string;
  reason: string;
  password: string;
  password2: string;
} | null>(null);
const revokeDlg = ref<StaffRow | null>(null);
const pwdDlg = ref<{ row: StaffRow; password: string; password2: string } | null>(null);

const ROLE_OPTS = [
  { value: "STAFF", label: "店员" },
  { value: "MANAGER", label: "店长" },
];
const ROLE_NAME: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

function canResetPwd(row: StaffRow) {
  return row.status !== "DISABLED" && (row.role === "MANAGER" || row.role === "BOSS");
}

function canRestore(row: StaffRow) {
  return row.status === "DISABLED" && row.role !== "BOSS";
}

function canRevoke(row: StaffRow) {
  return row.role !== "BOSS";
}

/** Active: 撤销员工；旧版已停用：转为会员（同一动作，账号变为会员） */
function revokeLabel(row: StaffRow) {
  return row.status === "DISABLED" ? "转为会员" : "撤销员工";
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
  const role = addForm.value.role;
  const password = addForm.value.password;
  const password2 = addForm.value.password2;
  if (!phone) {
    showToast("请填写手机号", true);
    return;
  }
  if (role === "MANAGER") {
    if (password.length < 6 || password.length > 32) {
      showToast("店长需设置 6-32 位后台登录密码", true);
      return;
    }
    if (password !== password2) {
      showToast("两次输入的密码不一致", true);
      return;
    }
  }
  acting.value = true;
  try {
    const data: Record<string, string> = {
      phone,
      nick: addForm.value.nick.trim(),
      role,
    };
    if (role === "MANAGER") data.password = password;
    await api("/admin/staff", { method: "POST", body: { data } });
    addForm.value = { phone: "", nick: "", role: "STAFF", password: "", password2: "" };
    showAdd.value = false;
    await load();
    showToast(
      role === "MANAGER"
        ? "已保存；店长可用手机号+密码登录 Web 后台"
        : "已保存；店员仅用小程序手机号登录，无需后台密码",
    );
  } catch (e: any) {
    showToast(e?.message || "添加失败", true);
  } finally {
    acting.value = false;
  }
}

function openAdd() {
  addForm.value = { phone: "", nick: "", role: "STAFF", password: "", password2: "" };
  showAdd.value = true;
}

function onRoleChange(row: StaffRow, role: string) {
  if (role === "BOSS" || row.role === "BOSS") {
    showToast("老板角色不可在此变更", true);
    return;
  }
  if (role === row.role) return;
  roleDlg.value = { row, role, reason: "", password: "", password2: "" };
}

function roleDlgBody() {
  if (!roleDlg.value) return "";
  const { row, role } = roleDlg.value;
  const from = ROLE_NAME[row.role] || row.role;
  const to = ROLE_NAME[role] || role;
  const hint =
    role === "MANAGER"
      ? "店长可进 Web 后台；请在下方设置后台登录密码"
      : "店员仅保留小程序待办、核销与录对局，不进 Web 后台";
  return `将「${row.nick}」的角色由【${from}】变更为【${to}】。\n· ${hint}\n· 变更即时生效，并记入操作日志`;
}

async function confirmRole() {
  if (!roleDlg.value) return;
  const { row, role, reason, password, password2 } = roleDlg.value;
  const reasonTrim = reason.trim();
  if (reasonTrim.length < 2) {
    showToast("请填写原因", true);
    return;
  }
  if (role === "MANAGER") {
    if (password.length < 6 || password.length > 32) {
      showToast("升为店长需设置 6-32 位后台登录密码", true);
      return;
    }
    if (password !== password2) {
      showToast("两次输入的密码不一致", true);
      return;
    }
  }
  acting.value = true;
  try {
    const data: Record<string, string> = { role, reason: reasonTrim };
    if (role === "MANAGER") data.password = password;
    await api(`/admin/staff/${row.id}/role`, { method: "PUT", body: { data } });
    roleDlg.value = null;
    await load();
    showToast(role === "MANAGER" ? "已升为店长并设置后台密码" : "角色已变更，已记入日志");
  } catch (e: any) {
    showToast(e?.message || "变更失败", true);
  } finally {
    acting.value = false;
  }
}

async function confirmRevoke() {
  if (!revokeDlg.value) return;
  acting.value = true;
  try {
    await api(`/admin/staff/${revokeDlg.value.id}/disable`, { method: "POST" });
    revokeDlg.value = null;
    await load();
    showToast("已撤销员工权限；对方可继续用小程序会员端，也可再次添加为员工");
  } catch (e: any) {
    showToast(e?.message || "操作失败", true);
  } finally {
    acting.value = false;
  }
}

async function enableStaff(row: StaffRow) {
  acting.value = true;
  try {
    await api(`/admin/staff/${row.id}/enable`, { method: "POST" });
    await load();
    showToast("已恢复员工权限");
  } catch (e: any) {
    showToast(e?.message || "恢复失败", true);
  } finally {
    acting.value = false;
  }
}

function openResetPwd(row: StaffRow) {
  if (!canResetPwd(row)) {
    showToast("仅店长/老板需要后台密码", true);
    return;
  }
  pwdDlg.value = { row, password: "", password2: "" };
}

async function confirmResetPwd() {
  if (!pwdDlg.value) return;
  const { row, password, password2 } = pwdDlg.value;
  if (password.length < 6 || password.length > 32) {
    showToast("后台登录密码需 6-32 位", true);
    return;
  }
  if (password !== password2) {
    showToast("两次输入的密码不一致", true);
    return;
  }
  acting.value = true;
  try {
    await api(`/admin/staff/${row.id}/password`, {
      method: "PUT",
      body: { data: { password } },
    });
    pwdDlg.value = null;
    showToast("密码已重置，请用新密码登录后台");
  } catch (e: any) {
    showToast(e?.message || "重置失败", true);
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
        <span class="tiny">店员只用小程序；店长才设后台密码。撤销员工会自动变成会员，手机号可再添加</span>
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
              <td class="col-op">
                <div class="op-grid">
                  <div class="op-slot">
                    <button
                      v-if="canResetPwd(row)"
                      class="btn sm"
                      :disabled="acting"
                      @click="openResetPwd(row)"
                    >
                      重置密码
                    </button>
                  </div>
                  <div class="op-slot">
                    <button
                      v-if="canRestore(row)"
                      class="btn sm"
                      :disabled="acting"
                      @click="enableStaff(row)"
                    >
                      恢复
                    </button>
                  </div>
                  <div class="op-slot">
                    <button
                      v-if="canRevoke(row)"
                      class="btn sm"
                      :disabled="acting"
                      @click="revokeDlg = row"
                    >
                      {{ revokeLabel(row) }}
                    </button>
                  </div>
                </div>
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
          <template v-if="addNeedsPwd">
            <div class="fld">后台登录密码 *</div>
            <input v-model="addForm.password" class="inp" type="password" placeholder="6-32 位，手机号+密码进 Web 后台" autocomplete="new-password" />
            <div class="fld">确认密码 *</div>
            <input v-model="addForm.password2" class="inp" type="password" placeholder="再次输入密码" autocomplete="new-password" />
            <p class="tiny add-pwd-hint">仅店长需要；用于管理后台登录。小程序仍用手机号登录。</p>
          </template>
          <p v-else class="tiny add-pwd-hint">店员只走小程序（手机号登录），不进 Web 后台，无需设密码。</p>
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
          <template v-if="roleDlg.role === 'MANAGER'">
            <div class="fld">后台登录密码 *</div>
            <input v-model="roleDlg.password" class="inp" type="password" placeholder="6-32 位" autocomplete="new-password" />
            <div class="fld">确认密码 *</div>
            <input v-model="roleDlg.password2" class="inp" type="password" placeholder="再次输入密码" autocomplete="new-password" />
          </template>
          <div class="dlg-actions">
            <button class="btn ghost" @click="roleDlg = null">取消</button>
            <button class="btn dan" :disabled="acting" @click="confirmRole">确认变更</button>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="pwdDlg" class="dlg-mask" @click.self="pwdDlg = null">
        <section class="dlg">
          <div class="st">重置后台密码</div>
          <p class="dlg-body">为「<b>{{ pwdDlg.row.nick }}</b>」设置新的后台登录密码。旧密码立即失效，无法查看。</p>
          <div class="fld">新密码 *</div>
          <input v-model="pwdDlg.password" class="inp" type="password" placeholder="6-32 位" autocomplete="new-password" />
          <div class="fld">确认密码 *</div>
          <input v-model="pwdDlg.password2" class="inp" type="password" placeholder="再次输入新密码" autocomplete="new-password" />
          <p class="tiny add-pwd-hint">仅影响 Web 后台登录；小程序仍用手机号登录。</p>
          <div class="dlg-actions">
            <button class="btn ghost" @click="pwdDlg = null">取消</button>
            <button class="btn pri" :disabled="acting" @click="confirmResetPwd">确认重置</button>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="revokeDlg" class="dlg-mask" @click.self="revokeDlg = null">
        <section class="dlg dlg-confirm">
          <div class="st">撤销员工权限</div>
          <p class="dlg-body">
            确认撤销「<b>{{ revokeDlg.nick }}</b>」的员工身份？
            <br />· 将自动变为普通会员（沿用原账号/手机号），小程序会员端可继续使用
            <br />· 员工端 / Web 后台不可再进
            <br />· 从本列表移除；同一手机号可再次添加为员工
            <br />· 历史接单等记录保留
          </p>
          <div class="dlg-actions">
            <button class="btn ghost" @click="revokeDlg = null">取消</button>
            <button class="btn dan" :disabled="acting" @click="confirmRevoke">确认撤销</button>
          </div>
        </section>
      </div>
    </Teleport>
  </AppAsyncPage>
</template>

<style scoped>
.staff-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.add-pwd-hint { margin: 8px 0 0; color: #9c9a93; line-height: 1.45; }
.staff-table { table-layout: fixed; min-width: 760px; }
.staff-table :is(th,td):nth-child(1){width:14%}
.staff-table :is(th,td):nth-child(2){width:14%}
.staff-table :is(th,td):nth-child(3){width:12%}
.staff-table :is(th,td):nth-child(4){width:9%}
.staff-table :is(th,td):nth-child(5){width:11%}
.staff-table :is(th,td):nth-child(6){width:9%}
.staff-table :is(th,td):nth-child(7){width:22%}
.staff-table td.col-op { white-space: nowrap; }
.op-grid {
  display: grid;
  grid-template-columns: 5.5rem 3.2rem 5.5rem;
  gap: 6px;
  justify-content: center;
  align-items: center;
  min-height: 28px;
}
.op-slot {
  display: flex;
  justify-content: center;
  min-width: 0;
}
.op-slot .btn {
  margin: 0;
  width: 100%;
  padding-left: 0;
  padding-right: 0;
}
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
.dlg-confirm { width: min(440px, 100%); }
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

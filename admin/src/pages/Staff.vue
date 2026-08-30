<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
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

const roleDlg = ref<{ row: StaffRow; role: string; reason: string } | null>(null);
const disableDlg = ref<StaffRow | null>(null);

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
    await load();
    showToast("已添加，该手机号登录后自动识别为员工");
  } catch (e: any) {
    showToast(e?.message || "添加失败", true);
  } finally {
    acting.value = false;
  }
}

function onRoleChange(row: StaffRow, event: Event) {
  const select = event.target as HTMLSelectElement;
  const role = select.value;
  if (role === "BOSS" || row.role === "BOSS") {
    showToast("老板角色不可在此变更", true);
    select.value = row.role;
    return;
  }
  if (role === row.role) return;
  roleDlg.value = { row, role, reason: "" };
  select.value = row.role;
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
  <AppAsyncPage :loading="loading" :error="err" @retry="load">
    <div>
      <div class="hdr">员工与权限 <em>仅老板 · 员工不可自助注册</em></div>
      <div class="card tb-wrap">
        <table class="tb2">
          <thead>
            <tr>
              <th style="width: 16%">姓名</th>
              <th style="width: 18%">手机号</th>
              <th style="width: 14%">角色</th>
              <th style="width: 12%">接单</th>
              <th style="width: 12%">收款额</th>
              <th style="width: 12%">核销</th>
              <th style="width: 16%">操作</th>
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
                <select
                  v-else
                  class="inp role-select"
                  :value="row.role"
                  :disabled="row.status === 'DISABLED'"
                  @change="onRoleChange(row, $event)"
                >
                  <option value="STAFF">店员</option>
                  <option value="MANAGER">店长</option>
                </select>
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
              <td colspan="7" class="empty-row">暂无员工</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card add-card">
        <div class="st">新增员工</div>
        <div class="g3 add-form">
          <input v-model="addForm.phone" class="inp" placeholder="手机号" />
          <input v-model="addForm.nick" class="inp" placeholder="姓名" />
          <select v-model="addForm.role" class="inp">
            <option value="STAFF">店员</option>
            <option value="MANAGER">店长</option>
          </select>
        </div>
        <button class="btn pri add-btn" :disabled="acting" @click="addStaff">添加员工</button>
      </div>
    </div>

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

    <div v-if="disableDlg" class="dlg-mask" @click.self="disableDlg = null">
      <section class="dlg">
        <div class="st">停用员工</div>
        <p class="dlg-body">确认停用「<b>{{ disableDlg.nick }}</b>」？停用后立即无法登录，历史记录保留。</p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="disableDlg = null">取消</button>
          <button class="btn dan" :disabled="acting" @click="confirmDisable">确认停用</button>
        </div>
      </section>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.tb-wrap { padding: 0; overflow: auto; }
.name { font-weight: 500; }
.disabled-tag { margin-left: 6px; color: var(--red); font-size: 11px; font-weight: 400; }
.boss-pill { background: var(--goldbg); color: var(--gold); }
.role-select { padding: 4px 7px; font-size: 12px; width: 100%; max-width: 120px; }
.empty-row { text-align: center; color: var(--ink3); padding: 24px; font-size: 12px; }
.mut { color: var(--ink3); font-size: 12px; }
.add-card { max-width: 560px; margin-top: 12px; }
.add-form { gap: 8px; }
.add-btn { margin-top: 9px; }
.dlg-mask {
  position: fixed; z-index: 30; inset: 0; display: grid; place-items: center;
  padding: 20px; background: rgba(0, 0, 0, 0.38);
}
.dlg {
  width: min(520px, 100%); background: #fff; border-radius: 16px; padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.fld { color: var(--ink2); font-size: 12px; margin: 8px 0 4px; }
.dlg .inp { width: 100%; margin-bottom: 4px; }
.dlg-body { font-size: 13px; line-height: 1.65; margin: 8px 0 4px; white-space: pre-line; }
.dlg-actions { display: grid; grid-template-columns: 1fr 1.6fr; gap: 10px; margin-top: 18px; }
.dlg-actions .btn { width: 100%; }
</style>

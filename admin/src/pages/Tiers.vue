<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

type TierRow = { id: number; amount: number; bonus: number; rec: boolean; pendingCount?: number };

const loading = ref(true);
const err = ref("");
const singleLimit = ref(0);
const rows = ref<TierRow[]>([]);
const drafts = ref<Record<number, { amount: number; bonus: number }>>({});
const savingId = ref<number | null>(null);
const showAdd = ref(false);
const addForm = ref({ amount: null as number | null, bonus: 0 });
const adding = ref(false);
const deleteTarget = ref<TierRow | null>(null);
const deleting = ref(false);

const sortedRows = computed(() => [...rows.value].sort((a, b) => a.amount - b.amount));

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

function pct(row: TierRow) {
  const amount = draftOf(row).amount;
  const bonus = draftOf(row).bonus;
  if (amount <= 0) return "—";
  return `${((bonus / amount) * 100).toFixed(1)}%`;
}

function draftOf(row: TierRow) {
  return drafts.value[row.id] || { amount: row.amount, bonus: row.bonus };
}

function syncDrafts(list: TierRow[]) {
  const next: Record<number, { amount: number; bonus: number }> = {};
  for (const row of list) {
    next[row.id] = { amount: row.amount, bonus: row.bonus };
  }
  drafts.value = next;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const res = await api<{ tiers: TierRow[]; singleLimit: number }>("/admin/tiers-page");
    rows.value = res.tiers || [];
    singleLimit.value = Number(res.singleLimit || 0);
    syncDrafts(rows.value);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function setAmount(row: TierRow, value: number) {
  const v = Number(value || 0);
  if (v <= 0) {
    showToast("金额必须大于 0", true);
    syncDrafts(rows.value);
    return;
  }
  if (rows.value.some((x) => x.id !== row.id && x.amount === v)) {
    showToast(`已存在 ¥${v} 档位`, true);
    syncDrafts(rows.value);
    return;
  }
  drafts.value[row.id] = { ...draftOf(row), amount: v };
}

function setBonus(row: TierRow, value: number) {
  const v = Number(value || 0);
  if (v < 0) {
    showToast("赠送金币不能为负", true);
    syncDrafts(rows.value);
    return;
  }
  drafts.value[row.id] = { ...draftOf(row), bonus: v };
}

async function saveRow(row: TierRow) {
  const draft = draftOf(row);
  savingId.value = row.id;
  try {
    const saved = await api<TierRow>(`/admin/tiers/${row.id}`, {
      method: "PUT",
      body: { data: { amount: draft.amount, bonus: draft.bonus } },
    });
    const idx = rows.value.findIndex((x) => x.id === row.id);
    if (idx >= 0) rows.value[idx] = { ...rows.value[idx], ...saved };
    syncDrafts(rows.value);
    showToast("已保存，C 端同步");
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
    syncDrafts(rows.value);
  } finally {
    savingId.value = null;
  }
}

async function toggleRec(row: TierRow) {
  try {
    const saved = await api<TierRow>(`/admin/tiers/${row.id}/recommend`, { method: "POST" });
    rows.value = rows.value.map((x) => ({ ...x, rec: x.id === saved.id ? saved.rec : false }));
    showToast(saved.rec ? "已设为最划算" : "已取消推荐");
  } catch (e: any) {
    showToast(e?.message || "操作失败", true);
  }
}

function openAdd() {
  addForm.value = { amount: null, bonus: 0 };
  showAdd.value = true;
}

async function createTier() {
  const amount = Number(addForm.value.amount || 0);
  const bonus = Number(addForm.value.bonus || 0);
  if (amount <= 0) {
    showToast("请填写有效的充值金额", true);
    return;
  }
  if (bonus < 0) {
    showToast("赠送金币不能为负", true);
    return;
  }
  adding.value = true;
  try {
    const saved = await api<TierRow>("/admin/tiers", {
      method: "POST",
      body: { data: { amount, bonus } },
    });
    showAdd.value = false;
    await load();
    showToast(
      singleLimit.value && amount > singleLimit.value
        ? `已新增，但超过单笔上限 ¥${fmt(singleLimit.value)}，C 端不展示`
        : "已新增，C 端充值页同步",
    );
    if (!rows.value.some((x) => x.id === saved.id)) {
      rows.value.push({ ...saved, pendingCount: 0 });
      syncDrafts(rows.value);
    }
  } catch (e: any) {
    showToast(e?.message || "创建失败", true);
  } finally {
    adding.value = false;
  }
}

function openDelete(row: TierRow) {
  if (rows.value.length <= 1) {
    showToast("至少保留一个充值档位", true);
    return;
  }
  deleteTarget.value = row;
}

async function confirmDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await api(`/admin/tiers/${deleteTarget.value.id}`, { method: "DELETE" });
    deleteTarget.value = null;
    await load();
    showToast("已删除，C 端同步");
  } catch (e: any) {
    showToast(e?.message || "删除失败", true);
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :data="rows" :err="err" @retry="load">
    <div>
      <div class="hdr">充值档位配置 <em>仅老板可改 · 资金规则</em></div>
      <div class="toolbar row">
        <button class="btn sm pri" @click="openAdd">＋ 新增档位</button>
        <span class="tiny">新增后 C 端充值页立即出现该档位，按金额升序排列</span>
      </div>

      <div class="card table-card">
        <table class="tb2">
          <thead>
            <tr>
              <th style="width:16%">金额</th>
              <th style="width:16%">赠送</th>
              <th style="width:14%">到账</th>
              <th style="width:14%">赠送比例</th>
              <th style="width:14%">推荐</th>
              <th style="width:26%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedRows" :key="row.id">
              <td>
                <input
                  class="inp tier-inp amount"
                  type="number"
                  min="1"
                  :value="draftOf(row).amount"
                  @change="setAmount(row, Number(($event.target as HTMLInputElement).value))"
                />
              </td>
              <td>
                <input
                  class="inp tier-inp bonus"
                  type="number"
                  min="0"
                  :value="draftOf(row).bonus"
                  @change="setBonus(row, Number(($event.target as HTMLInputElement).value))"
                />
              </td>
              <td><b>{{ fmt(draftOf(row).amount + draftOf(row).bonus) }}</b></td>
              <td class="tiny">{{ pct(row) }}</td>
              <td>
                <span class="chip" :class="{ on: row.rec }" @click="toggleRec(row)">
                  {{ row.rec ? "最划算" : "设为推荐" }}
                </span>
              </td>
              <td>
                <div class="ops">
                  <button class="btn sm ghost" :disabled="savingId === row.id" @click="saveRow(row)">保存</button>
                  <button class="btn sm ghost danger-btn" @click="openDelete(row)">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!sortedRows.length">
              <td colspan="6" class="table-empty">暂无充值档位，请点击上方新增</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="note rd">
        <b>资金规则只归老板：</b>店长不可改充值档位与赠送比例。单笔充值上限 ¥{{ fmt(singleLimit) }}（风控参数中配置），
        <b>超过上限的档位不会在 C 端展示</b>。「最划算」为单选，设了新的会自动取消旧的。
      </div>
    </div>

    <div v-if="showAdd" class="dlg-mask" @click.self="showAdd = false">
      <section class="dlg">
        <div class="st">新增充值档位</div>
        <div class="create-grid">
          <label>
            <div class="fld">充值金额（元）*</div>
            <input v-model.number="addForm.amount" class="inp" type="number" min="1" placeholder="如 2000" />
          </label>
          <label>
            <div class="fld">赠送金币</div>
            <input v-model.number="addForm.bonus" class="inp" type="number" min="0" />
          </label>
        </div>
        <div class="tiny dlg-hint">
          当前单笔充值上限 ¥{{ fmt(singleLimit) }}，超出上限的档位在 C 端不展示。
        </div>
        <div class="dlg-actions">
          <button class="btn ghost" @click="showAdd = false">取消</button>
          <button class="btn pri" :disabled="adding" @click="createTier">创建档位</button>
        </div>
      </section>
    </div>

    <div v-if="deleteTarget" class="dlg-mask" @click.self="deleteTarget = null">
      <section class="dlg">
        <div class="st">删除充值档位</div>
        <p>
          确认删除 <b>¥{{ fmt(deleteTarget.amount) }}</b> 档位（赠 {{ fmt(deleteTarget.bonus) }}）？
        </p>
        <p class="tiny delete-note">
          C 端充值页不再展示该档位。
          <template v-if="deleteTarget.pendingCount">
            <b class="warn">当前有 {{ deleteTarget.pendingCount }} 张该金额的待付款充值单，删除档位不影响这些单据继续收款。</b>
          </template>
          <template v-else>历史充值记录不受影响。</template>
        </p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="deleteTarget = null">取消</button>
          <button class="btn dan" :disabled="deleting" @click="confirmDelete">确认删除</button>
        </div>
      </section>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.toolbar { gap: 8px; margin-bottom: 11px; align-items: center; }
.table-card { padding: 0; overflow: auto; }
.tb2 :is(th, td):nth-child(4),
.tb2 :is(th, td):nth-child(5),
.tb2 :is(th, td):nth-child(6) { text-align: center; }
.tb2 td:nth-child(6) .ops { justify-content: center; width: 100%; }
.tier-inp { padding: 4px 7px; }
.tier-inp.amount { width: 90px; }
.tier-inp.bonus { width: 80px; }
.danger-btn { color: var(--red); border-color: #E9C4C4; }
.note.rd { margin-top: 12px; padding: 12px; border-radius: 10px; font-size: 12px; line-height: 1.6; }
.dlg-mask {
  position: fixed; z-index: 30; inset: 0; display: grid; place-items: center;
  padding: 20px; background: rgba(0, 0, 0, 0.38);
}
.dlg {
  width: min(520px, 100%); background: #fff; border-radius: 16px; padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.fld { color: var(--ink2); font-size: 12px; margin-bottom: 5px; }
.create-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.dlg-hint { margin-top: 8px; color: var(--ink3); }
.dlg-actions { display: grid; grid-template-columns: 1fr 1.6fr; gap: 10px; margin-top: 20px; }
.dlg-actions .btn { width: 100%; }
.delete-note { margin-top: 8px; line-height: 1.6; }
.warn { color: var(--red); }
</style>

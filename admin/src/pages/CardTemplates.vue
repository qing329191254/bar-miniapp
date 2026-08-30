<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppSelect from "../components/AppSelect.vue";
import { showToast } from "../composables/useToast";

const rows = ref<any[]>([]);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");
const saving = ref(false);
const isNew = ref(false);
const editingId = ref<number | null>(null);

const CAT_FORM: Record<string, string> = {
  GAME: "游戏卡",
  FOOD: "酒水小食卡",
  OTHER: "其他卡",
};
const CAT_TABLE: Record<string, string> = {
  GAME: "游戏卡",
  FOOD: "酒水",
  OTHER: "其他",
};
const catOpts = computed(() =>
  Object.entries(CAT_FORM).map(([value, label]) => ({ value, label })),
);

function blank() {
  return {
    name: "",
    cat: "GAME",
    cost: 0,
    days: 30,
    perLimit: -1,
    stock: -1,
    exch: true,
    use: "",
    prize: "",
    desc: "",
    rules: { durationMinutes: 0, weekdays: [] as number[] },
  };
}
const form = ref(blank());

const showForm = () => isNew.value || editingId.value !== null;

function catTable(cat: string) {
  return CAT_TABLE[cat] || cat;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const res = await api<any>("/admin/cardTpls?pageSize=0");
    rows.value = Array.isArray(res) ? res : res.items || [];
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function openNew() {
  isNew.value = true;
  editingId.value = null;
  form.value = blank();
}

function openEdit(row: any) {
  isNew.value = false;
  editingId.value = row.id;
  form.value = {
    ...blank(),
    ...row,
    rules: {
      durationMinutes: Number(row.rules?.durationMinutes || 0),
      weekdays: (row.rules?.weekdays || []).map(Number),
    },
  };
}

function closeForm() {
  isNew.value = false;
  editingId.value = null;
  form.value = blank();
}

function normalized() {
  const cost = Number(form.value.cost || 0);
  return {
    name: String(form.value.name || "").trim(),
    cat: form.value.cat || "GAME",
    cost,
    days: Math.max(1, Number(form.value.days || 30)),
    perLimit: Number(form.value.perLimit ?? -1),
    stock: Number(form.value.stock ?? -1),
    exch: form.value.exch !== false,
    use: String(form.value.use || ""),
    prize: String(form.value.prize || ""),
    desc: String(form.value.desc || ""),
    rules: form.value.rules || { durationMinutes: 0, weekdays: [] },
  };
}

function limitText(v: number | null | undefined) {
  return v == null || v < 0 ? "不限" : String(v);
}

function exchText(row: any) {
  return row.cost > 0 && row.exch !== false ? "是" : "否";
}

async function save() {
  if (!form.value.name.trim()) {
    showToast("请填写卡券名称", true);
    return;
  }
  saving.value = true;
  try {
    const item = normalized();
    if (isNew.value) {
      const saved = await api<any>("/admin/card-templates", { method: "POST", body: { data: item } });
      isNew.value = false;
      editingId.value = saved.id;
      showToast("已新增");
    } else {
      await api(`/admin/card-templates/${editingId.value}`, { method: "PUT", body: { data: item } });
      showToast("已保存");
    }
    await load();
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="card-tpl-page">
    <div class="hdr card-tpl-hdr">
      <span class="hdr-title">卡券配置</span>
      <em class="hdr-note">含积分可兑换内容配置 · 宝箱奖品仅店员可见</em>
    </div>

    <AppAsyncPage
      :loading="loading"
      :data="loaded"
      :err="err"
      :skeleton="{ showHeader: false, tableCols: 7, tableRows: 8 }"
      @retry="load"
    >
      <div class="card-tpl-layout">
        <div class="main-col">
          <section class="card list-card">
            <div class="list-head">
              <b>卡券模板列表</b>
              <button class="btn sm pri" @click="openNew">＋ 新增卡券</button>
            </div>
            <div class="tb-wrap">
              <table class="tb2 card-tpl-table" data-cols="lcccccc">
                <thead>
                  <tr>
                    <th style="width:24%">名称</th>
                    <th style="width:9%">分类</th>
                    <th style="width:11%">积分</th>
                    <th style="width:9%">有效期</th>
                    <th style="width:11%">兑换页</th>
                    <th style="width:16%">上限/库存</th>
                    <th style="width:8%">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in rows" :key="row.id">
                    <td><b>{{ row.name }}</b></td>
                    <td class="mut">{{ catTable(row.cat) }}</td>
                    <td>{{ row.cost || "—" }}</td>
                    <td>{{ row.days }} 天</td>
                    <td class="tiny">{{ exchText(row) }}</td>
                    <td class="tiny">{{ limitText(row.perLimit) }} / {{ limitText(row.stock) }}</td>
                    <td><button class="btn sm" @click="openEdit(row)">编辑</button></td>
                  </tr>
                  <tr v-if="!rows.length">
                    <td colspan="7" class="table-empty">暂无卡券模板，可点击右上角新增</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="card rule-card">
            <div class="st">有效期规则</div>
            <table class="tb2">
              <thead>
                <tr><th>卡类型</th><th>有效期</th></tr>
              </thead>
              <tbody>
                <tr><td>游戏卡 / 酒水卡</td><td><b>默认 30 天</b></td></tr>
                <tr><td>其他卡</td><td>后台自定义</td></tr>
                <tr><td>宝箱卡</td><td><b class="gold">固定 7 天</b></td></tr>
              </tbody>
            </table>
          </section>

          <section class="card tips-card">
            <div class="st tips-title">兑换配置要点</div>
            <div class="tiny tips-body">
              · 设置积分价并开启「兑换页展示」后，顾客即可在小程序兑换<br />
              · 月末清零前可集中兑换，需配置库存与每人上限防挤兑<br />
              · 宝箱卡积分价 0、不出现兑换页，仅奖励发放
            </div>
          </section>
        </div>

        <aside class="side-col">
          <section v-if="showForm()" class="card edit-card">
            <div class="st">
              {{ isNew ? "新增卡券" : `编辑 · ${form.name}` }}
              <em class="close-btn" @click="closeForm">✕</em>
            </div>

            <div class="form-grid">
              <label class="field">
                <span class="fld">名称 *</span>
                <input v-model="form.name" class="inp" />
              </label>
              <label class="field">
                <span class="fld">分类 *</span>
                <AppSelect v-model="form.cat" :options="catOpts" no-margin />
              </label>
              <label class="field">
                <span class="fld">积分价 <b class="hint-red">（0 = 仅奖励发放，不进兑换页）</b></span>
                <input v-model.number="form.cost" type="number" min="0" class="inp inp-num" />
              </label>
              <label class="field">
                <span class="fld">有效期（天）</span>
                <input v-model.number="form.days" type="number" min="1" class="inp inp-num" />
              </label>
              <label class="field">
                <span class="fld">每人兑换上限（-1 不限）</span>
                <input v-model.number="form.perLimit" type="number" class="inp inp-num" />
              </label>
              <label class="field">
                <span class="fld">库存（-1 不限）</span>
                <input v-model.number="form.stock" type="number" class="inp inp-num" />
              </label>
            </div>

            <label class="toggle-row">
              <span class="tiny">出现在兑换页（积分可兑换）</span>
              <input v-model="form.exch" type="checkbox" class="ui-toggle" />
            </label>

            <div v-if="form.cat === 'OTHER'" class="field">
              <span class="fld">宝箱奖品说明 * <b class="hint-red">仅店员端核销可见</b></span>
              <input v-model="form.prize" class="inp" placeholder="如 任选一瓶 300 元内洋酒" />
            </div>

            <div class="field">
              <span class="fld">使用限制</span>
              <input v-model="form.use" class="inp" placeholder="如 仅限周一至周四" />
            </div>

            <button class="btn pri save-btn" :disabled="saving" @click="save">
              {{ saving ? "保存中…" : isNew ? "创建卡券" : "保存修改" }}
            </button>
          </section>
        </aside>
      </div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.card-tpl-page {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}
.card-tpl-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 12px;
  align-items: start;
}
.card-tpl-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  text-align: right;
  pointer-events: auto;
  white-space: normal;
}
.main-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.list-card {
  margin-bottom: 0;
  padding: 14px;
}
.list-head {
  display: flex;
  align-items: center;
  margin-bottom: 11px;
}
.list-head b {
  font-size: 14px;
}
.list-head .btn {
  margin-left: auto;
}
.tb-wrap {
  overflow: auto;
}
.card-tpl-table td b {
  font-weight: 500;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 0;
}
.edit-card {
  margin-bottom: 0;
}
.close-btn {
  margin-left: auto;
  cursor: pointer;
  font-style: normal;
  color: var(--ink3);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
  margin-bottom: 8px;
}
.form-grid .field {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  min-width: 0;
}
.form-grid .fld {
  min-height: 34px;
  line-height: 1.55;
  margin-bottom: 4px;
}
.form-grid .inp {
  width: 100%;
  margin: 0;
}
.form-grid .inp-num {
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.inp-num::-webkit-outer-spin-button,
.inp-num::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.inp-num[type="number"] {
  -moz-appearance: textfield;
  appearance: textfield;
}
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  padding: 10px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  cursor: pointer;
}
.toggle-row .tiny {
  color: var(--ink2);
  line-height: 1.5;
}
.field {
  display: block;
  margin-bottom: 8px;
}
.fld {
  display: block;
  margin-bottom: 4px;
  color: var(--ink2);
  font-size: 11px;
}
.fld b,
.hint-red {
  color: var(--red);
  font-weight: 500;
}
.save-btn {
  width: 100%;
}
.rule-card,
.tips-card {
  margin-bottom: 0;
}
.gold {
  color: var(--gold);
}
.tips-card {
  background: var(--redbg);
  border-color: #e24b4a;
}
.tips-title {
  color: var(--red);
}
.tips-body {
  color: var(--red);
  line-height: 1.8;
}
@media (max-width: 960px) {
  .card-tpl-layout {
    grid-template-columns: 1fr;
  }
  .side-col {
    position: static;
  }
  .card-tpl-hdr .hdr-note {
    margin-left: 0;
    text-align: left;
    width: 100%;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, DEFAULT_PAGE_SIZE } from "../api";
import AppSelect from "../components/AppSelect.vue";
import ImgField from "../components/ImgField.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppPagination from "../components/AppPagination.vue";
import { usePagination } from "../composables/usePagination";
import { showToast } from "../composables/useToast";

const products = ref<any[]>([]);
const cats = ref<any[]>([]);
const tpls = ref<any[]>([]);
const edit = ref<any>(null);
const catDlg = ref<null | "add" | { id: number; name: string }>(null);
const catForm = ref({ name: "", sort: 9 });
const deleteCatTarget = ref<any>(null);
const catBusy = ref(false);
const deletingCat = ref(false);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const [p, c, t] = await Promise.all([
      api<any>("/admin/products?pageSize=0"),
      api<any>("/admin/cats?pageSize=0"),
      api<any>("/admin/cardTpls?pageSize=0"),
    ]);
    products.value = Array.isArray(p) ? p : p.items || [];
    cats.value = Array.isArray(c) ? c : c.items || [];
    tpls.value = Array.isArray(t) ? t : t.items || [];
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "商品数据加载失败";
    if (loaded.value) showToast(err.value, true);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function catName(id: number) {
  return cats.value.find((c) => c.id === id)?.name || "未分类";
}
function catCount(cid: number) {
  return products.value.filter((p) => p.cid === cid && !p.offline).length;
}
function imageUrl(value: unknown) {
  const url = String(value || "");
  return /^(https?:\/\/|data:|\/uploads\/)/.test(url) ? url : "";
}
const online = computed(() => products.value.filter((p) => !p.offline));
const offline = computed(() => products.value.filter((p) => p.offline));
const allProducts = computed(() => [...online.value, ...offline.value]);
const prodPg = usePagination(allProducts, DEFAULT_PAGE_SIZE);
const shownProducts = prodPg.items;
const tablePage = prodPg.page;
const tablePageSize = prodPg.pageSize;
const rowTotal = prodPg.total;

const deleteCatHint = computed(() => {
  const c = deleteCatTarget.value;
  if (!c) return "";
  const offlineN = products.value.filter((p) => p.cid === c.id && p.offline).length;
  if (!offlineN) return "";
  return `该分类下有 ${offlineN} 个已下架商品，删除后它们将归为「未分类」，重新上架前需先改分类。`;
});
const catOpts = computed(() =>
  cats.value.filter((c) => !c.disabled).map((c) => ({ value: c.id, label: c.name })),
);
const tplOpts = computed(() => tpls.value.map((t) => ({ value: t.id, label: t.name })));
const typeOpts = [
  { value: "SINGLE", label: "单品（下单核销）" },
  { value: "COMBO", label: "套餐（下单自动发卡）" },
];
const catRows = computed(() =>
  [...cats.value].sort((a, b) => (a.sort || 99) - (b.sort || 99)),
);
const defaultCid = computed(() => cats.value.find((c) => !c.disabled)?.id || cats.value[0]?.id);

function tplName(id: number) {
  return tpls.value.find((t) => t.id === id)?.name || "（卡券已删）";
}
function comboText(p: any) {
  if (p.type !== "COMBO") return "—";
  const parts = (p.combo || []).map((c: any) => `${tplName(c.tpl)}×${c.qty || 1}`);
  return parts.length ? parts.join("、") : "—";
}
function blankProduct() {
  return {
    name: "",
    cid: defaultCid.value,
    price: 0,
    type: "SINGLE",
    desc: "",
    combo: [] as { tpl: number; qty: number }[],
    dailyLimit: -1,
    img: "",
  };
}
function openEdit(p: any) {
  edit.value = {
    ...p,
    type: p.type || "SINGLE",
    combo: (p.combo || []).map((c: any) => ({ tpl: Number(c.tpl), qty: Number(c.qty || 1) })),
    dailyLimit: p.dailyLimit ?? -1,
  };
}
function onTypeChange() {
  if (!edit.value) return;
  if (edit.value.type === "COMBO" && !edit.value.combo?.length) {
    edit.value.combo = [{ tpl: tpls.value[0]?.id || 1, qty: 1 }];
  }
}
function addComboRow() {
  if (!edit.value) return;
  edit.value.combo = edit.value.combo || [];
  edit.value.combo.push({ tpl: tpls.value[0]?.id || 1, qty: 1 });
}
function removeComboRow(i: number) {
  edit.value?.combo?.splice(i, 1);
}

function openCatAdd() {
  catForm.value = { name: "", sort: 9 };
  catDlg.value = "add";
}
function openCatRename(c: any) {
  catForm.value = { name: c.name, sort: c.sort || 99 };
  catDlg.value = { id: c.id, name: c.name };
}
function closeCatDlg() {
  catDlg.value = null;
  catForm.value = { name: "", sort: 9 };
}

async function saveCat() {
  const name = catForm.value.name.trim();
  if (!name) {
    showToast("请填写分类名称", true);
    return;
  }
  catBusy.value = true;
  try {
    if (catDlg.value === "add") {
      await api("/admin/cats", {
        method: "POST",
        body: { data: { name, sort: Number(catForm.value.sort) || 9 } },
      });
      showToast("商品已新增，并同步至顾客点单页");
    } else if (catDlg.value && typeof catDlg.value === "object") {
      await api(`/admin/cats/${catDlg.value.id}`, {
        method: "PUT",
        body: { data: { name, sort: Number(catForm.value.sort) || 99 } },
      });
      showToast("已保存");
    }
    closeCatDlg();
    await load();
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    catBusy.value = false;
  }
}

async function saveCatSort(c: any, sort: number) {
  try {
    await api(`/admin/cats/${c.id}`, { method: "PUT", body: { data: { name: c.name, sort } } });
    c.sort = sort;
  } catch (e: any) {
    showToast(e?.message || "排序保存失败", true);
    await load();
  }
}

async function toggleCat(c: any) {
  try {
    await api(`/admin/cats/${c.id}`, {
      method: "PUT",
      body: { data: { name: c.name, sort: c.sort || 99, disabled: !c.disabled } },
    });
    await load();
  } catch (e: any) {
    showToast(e?.message || "操作失败", true);
  }
}

function deleteCat(c: any) {
  deleteCatTarget.value = c;
}

async function confirmDeleteCat() {
  if (!deleteCatTarget.value) return;
  deletingCat.value = true;
  try {
    await api(`/admin/cats/${deleteCatTarget.value.id}`, { method: "DELETE" });
    deleteCatTarget.value = null;
    showToast("已删除");
    await load();
  } catch (e: any) {
    showToast(e?.message || "删除失败", true);
  } finally {
    deletingCat.value = false;
  }
}

async function toggleSold(p: any) {
  await api("/admin/products", { method: "POST", body: { data: { ...p, soldOut: !p.soldOut } } });
  await load();
}
async function toggleOff(p: any, off: boolean) {
  await api("/admin/products", { method: "POST", body: { data: { ...p, offline: off } } });
  await load();
}
async function save() {
  if (!edit.value?.name) {
    showToast("请填写商品名称", true);
    return;
  }
  const c = cats.value.find((x) => x.id === edit.value.cid);
  if (c?.disabled) {
    showToast(`该商品所属分类「${c.name}」已停用，请先启用分类或改分类`, true);
    return;
  }
  if (edit.value.type === "COMBO" && !(edit.value.combo || []).length) {
    showToast("套餐商品请至少配置一项发放内容", true);
    return;
  }
  const payload = {
    ...edit.value,
    dailyLimit: Number(edit.value.dailyLimit ?? -1),
    combo: edit.value.type === "COMBO" ? edit.value.combo : [],
  };
  await api("/admin/products", { method: "POST", body: { data: payload } });
  edit.value = null;
  showToast("已保存");
  await load();
}
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 0, showNote: false }" @retry="load">
  <div class="prod-page">
    <div class="hdr products-hdr"><span class="hdr-title">商品管理</span><em class="hdr-note">单品到店核销 · 套餐下单后自动发放卡券</em></div>
    <div class="prod-grid">
      <div class="card prod-list">
        <div class="row" style="margin-bottom:11px;flex:none">
          <b>商品列表</b>
          <span class="tiny" style="margin-left:8px">在售 {{ online.length }} · 已下架 {{ offline.length }}</span>
          <button
            class="btn gold"
            style="margin-left:auto"
            @click="edit = blankProduct()"
          >＋ 新增商品</button>
        </div>
        <div class="tb-wrap">
          <table class="tb2 prod-table" data-cols="lcccccc">
            <thead>
              <tr><th>商品</th><th>分类</th><th>价格</th><th>类型</th><th>发放配置</th><th>状态</th><th class="col-op">操作</th></tr>
            </thead>
            <tbody>
            <tr v-for="p in shownProducts" :key="p.id" :style="p.offline ? 'opacity:.55' : ''">
              <td>
                <div v-if="!p.offline" class="row" style="gap:8px">
                  <img v-if="imageUrl(p.img)" class="pimg" :src="imageUrl(p.img)" alt="" />
                  <div v-else class="pimg empty">{{ (p.name || "商").slice(0,1) }}</div>
                  <div>
                    <b>{{ p.name }}</b>
                    <div class="tiny">{{ p.desc || "—" }}</div>
                  </div>
                </div>
                <b v-else>{{ p.name }}</b>
              </td>
              <td class="tiny">{{ catName(p.cid) }}</td>
              <td><b>{{ p.price }}</b></td>
              <td><span class="pill" :class="p.type === 'COMBO' ? 'combo-pill' : 'single-pill'">{{ p.type === "COMBO" ? "套餐发卡" : "单品" }}</span></td>
              <td class="tiny combo-cell">{{ comboText(p) }}</td>
              <td>
                <span v-if="p.offline" class="pill" style="color:#6B6A65">已下架</span>
                <span v-else class="pill" :style="{ color: p.soldOut ? '#A32D2D' : '#3B6D11' }">{{ p.soldOut ? "已估清" : "在售" }}</span>
              </td>
              <td class="col-op">
                <div v-if="!p.offline" class="prod-ops">
                  <button class="btn sm ghost" @click="openEdit(p)">编辑</button>
                  <button class="btn sm ghost" @click="toggleSold(p)">{{ p.soldOut ? "恢复" : "估清" }}</button>
                  <button class="btn sm ghost prod-off-btn" @click="toggleOff(p, true)">下架</button>
                </div>
                <button v-else class="btn sm ghost" @click="toggleOff(p, false)">重新上架</button>
              </td>
            </tr>
            <tr v-if="!allProducts.length"><td colspan="7" class="table-empty">暂无商品，可点击右上角新增</td></tr>
            </tbody>
          </table>
          <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>

        <div class="card cat-section">
          <div class="row" style="margin-bottom:11px">
            <b style="font-size:14px">商品分类</b>
            <span class="tiny" style="margin-left:8px">拖动排序会同步调整顾客点单页的分类顺序</span>
            <button class="btn sm pri" style="margin-left:auto" @click="openCatAdd">＋ 新增分类</button>
          </div>
          <table class="tb2 cat-table" data-cols="lcccc">
            <thead>
              <tr><th style="width:12%">排序</th><th style="width:34%">分类名称</th><th style="width:18%">商品数</th><th style="width:14%">状态</th><th style="width:22%">操作</th></tr>
            </thead>
            <tbody>
            <tr v-for="c in catRows" :key="c.id" :style="c.disabled ? 'opacity:.55' : ''">
              <td>
                <input
                  class="inp sort-inp"
                  type="number"
                  :value="c.sort || 99"
                  @change="saveCatSort(c, Number(($event.target as HTMLInputElement).value) || 99)"
                />
              </td>
              <td><b>{{ c.name }}</b></td>
              <td>{{ catCount(c.id) }} 个在售</td>
              <td>
                <span class="pill" :style="{ color: c.disabled ? '#6B6A65' : '#3B6D11', background: c.disabled ? '#EEECE6' : '#EAF3DE' }">
                  {{ c.disabled ? "已停用" : "启用中" }}
                </span>
              </td>
              <td>
                <div class="row cat-ops">
                  <button class="btn sm" @click="openCatRename(c)">改名</button>
                  <button class="btn sm" @click="toggleCat(c)">{{ c.disabled ? "启用" : "停用" }}</button>
                  <button class="btn sm dan" @click="deleteCat(c)">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!catRows.length"><td colspan="5" class="table-empty">暂无商品分类</td></tr>
            </tbody>
          </table>
          <div class="tiny cat-foot">分类下仍有在售商品时不可删除，请先移动商品或将其下架；停用后，该分类不会在顾客点单页展示，也无法用于新商品。</div>
        </div>
      </div>

      <div class="prod-side">
        <div v-if="edit" class="card">
          <div class="st">{{ edit.id ? "编辑 · " + edit.name : "新增商品" }} <em style="cursor:pointer" @click="edit=null">✕</em></div>
          <div class="img-block">
            <div class="img-left">
              <ImgField v-model="edit.img" size="md" actions />
            </div>
            <div class="img-copy">
              <div class="fld">商品图片 <b>（顾客点单页展示）</b></div>
              <p class="img-note">建议 1:1 方图，单张 ≤ 2MB，图片越清晰越好。</p>
              <p class="img-note">未上传图片时将显示商品名称首字，仍可正常下单。</p>
            </div>
          </div>
          <div class="edit-grid">
            <label class="field">
              <span class="fld">商品名称 *</span>
              <input class="inp" v-model="edit.name" />
            </label>
            <label class="field">
              <span class="fld">分类 *</span>
              <AppSelect v-model="edit.cid" :options="catOpts" no-margin />
            </label>
            <label class="field">
              <span class="fld">金币价格 *</span>
              <input class="inp inp-num" type="number" v-model.number="edit.price" />
            </label>
            <label class="field">
              <span class="fld">类型 *</span>
              <AppSelect v-model="edit.type" :options="typeOpts" no-margin @change="onTypeChange" />
            </label>
          </div>
          <div class="fld">描述</div>
          <input class="inp" v-model="edit.desc" />
          <div v-if="edit.type === 'COMBO'" class="combo-editor">
            <div class="fld">发放配置 *</div>
            <div v-if="!(edit.combo || []).length" class="tiny combo-empty">尚未配置发放内容</div>
            <div v-for="(row, i) in edit.combo || []" :key="i" class="combo-row">
              <AppSelect v-model="row.tpl" :options="tplOpts" compact no-margin class="combo-tpl" />
              <input v-model.number="row.qty" class="inp combo-qty inp-num" type="number" min="1" />
              <button type="button" class="btn sm" @click="removeComboRow(i)">删</button>
            </div>
            <button type="button" class="btn sm combo-add" @click="addComboRow">＋ 添加发放项</button>
          </div>
          <div class="fld">每日限量（-1 不限）</div>
          <input v-model.number="edit.dailyLimit" class="inp inp-num limit-inp" type="number" />
          <button class="btn" style="width:100%;margin-top:8px" @click="save">{{ edit.id ? "保存修改" : "创建商品" }}</button>
        </div>
      </div>
    </div>
    <div class="note prod-note"><b>商品说明：</b>单品按正常流程下单、接单与出单；套餐在店员接单后，会按设置自动发放卡券。商品下架后不再对外展示，历史订单仍会保留。</div>

    <Teleport to="body">
    <div v-if="catDlg" class="cat-mask" @click.self="closeCatDlg">
      <div class="cat-dialog">
        <div class="st">{{ catDlg === 'add' ? '新增商品分类' : '分类改名' }}</div>
        <div class="fld">分类名称 *</div>
        <input v-model="catForm.name" class="inp" placeholder="如 无酒精特调" />
        <div class="fld" style="margin-top:9px">排序（数字越小越靠前）</div>
        <input v-model.number="catForm.sort" class="inp" type="number" />
        <div class="cat-actions">
          <button class="btn ghost" :disabled="catBusy" @click="closeCatDlg">取消</button>
          <button class="btn pri" :disabled="catBusy" @click="saveCat">{{ catBusy ? "保存中…" : (catDlg === 'add' ? "创建分类" : "保存") }}</button>
        </div>
      </div>
    </div>
    <div v-if="deleteCatTarget" class="dlg-mask" @click.self="deleteCatTarget = null">
      <section class="dlg dlg-confirm">
        <div class="st">删除商品分类</div>
        <p class="dlg-body">确认删除分类「<b>{{ deleteCatTarget.name }}</b>」？</p>
        <p v-if="deleteCatHint" class="tiny dlg-hint">{{ deleteCatHint }}</p>
        <div class="dlg-actions">
          <button class="btn ghost" @click="deleteCatTarget = null">取消</button>
          <button class="btn dan" :disabled="deletingCat" @click="confirmDeleteCat">确认删除</button>
        </div>
      </section>
    </div>
    </Teleport>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.prod-page {
  flex: none;
  min-height: auto;
  display: flex;
  flex-direction: column;
  width: 100%;
}
.prod-page .prod-grid {
  flex: none;
  min-height: auto;
  align-items: start;
}
.prod-page .hdr { flex: none; }
.products-hdr .hdr-note { position: static; transform: none; margin-left: auto; text-align: right; pointer-events: auto; white-space: normal; }
@media (max-width: 900px) {
  .products-hdr .hdr-note { margin-left: 0; text-align: left; width: 100%; }
}
.prod-list {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  min-height: auto;
  overflow: visible;
}
.tb-wrap {
  overflow-x: auto;
  overflow-y: visible;
}
.prod-table :is(th, td):nth-child(7) {
  width: 1%;
  white-space: nowrap;
}
.prod-ops {
  display: inline-flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px;
}
.prod-off-btn {
  color: #a32d2d;
}
.prod-side {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.prod-side .card { margin-bottom: 0; }
.prod-note { flex: none; margin-top: 12px; margin-bottom: 0; }
.pimg {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
  flex: none;
  background: #EDEBE4;
}
.pimg.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--ink3);
}
.cat-section {
  margin-top: 12px;
  margin-bottom: 0;
  flex: none;
}
.sort-inp {
  width: 56px;
  padding: 4px 7px;
  margin: 0;
}
.cat-ops { gap: 4px; flex-wrap: wrap; }
.cat-foot { margin-top: 8px; color: var(--ink3); line-height: 1.65; }
.cat-dialog {
  background: var(--card);
  border-radius: 14px;
  padding: 16px 18px;
  width: min(400px, 100%);
  box-shadow: 0 8px 28px rgba(28, 27, 25, 0.12);
}
.cat-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  justify-content: flex-end;
}
.dlg {
  width: min(400px, 100%);
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.dlg .st { margin-bottom: 12px; }
.dlg-body {
  font-size: 13px;
  line-height: 1.65;
  margin: 0;
  color: var(--ink2);
}
.dlg-hint {
  margin-top: 8px;
  line-height: 1.6;
  color: var(--ink3);
}
.dlg-actions {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 10px;
  margin-top: 18px;
}
.dlg-actions .btn { width: 100%; }
.fld {
  font-size: 12px;
  color: var(--ink2);
  margin-bottom: 4px;
  margin-top: 8px;
}
.fld:first-of-type { margin-top: 0; }
.edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
  margin-top: 8px;
}
.edit-grid .field { display: block; min-width: 0; }
.edit-grid .fld { margin-top: 0; margin-bottom: 4px; }
.edit-grid .inp { width: 100%; margin: 0; }
.edit-grid :deep(.sel) { width: 100%; margin-bottom: 0; }
.inp-num { text-align: center; font-variant-numeric: tabular-nums; }
.inp-num::-webkit-outer-spin-button,
.inp-num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.inp-num[type="number"] { -moz-appearance: textfield; appearance: textfield; }
.limit-inp { max-width: 120px; }
.img-block {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.img-left { flex: none; text-align: center; }
.img-copy { flex: 1; min-width: 0; }
.img-copy .fld { margin-top: 0; }
.img-copy .fld b { font-weight: 500; color: var(--ink3); }
.img-note {
  margin: 0;
  font-size: 11px;
  color: var(--ink3);
  line-height: 1.7;
}
.img-note + .img-note { margin-top: 2px; }
.combo-cell { max-width: 220px; line-height: 1.5; }
.single-pill { border: 1px solid var(--line); color: var(--ink2); background: transparent; white-space: nowrap; }
.combo-pill { background: #F3EEFB; color: #4A2A7A; white-space: nowrap; }
.combo-editor { margin-top: 4px; }
.combo-empty { margin-bottom: 6px; color: var(--ink3); }
.combo-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.combo-tpl { flex: 1; min-width: 0; }
.combo-row :deep(.combo-tpl.sel) { flex: 1; min-width: 0; margin-bottom: 0; }
.combo-qty { width: 64px; margin: 0; }
.combo-add { margin-top: 2px; }
</style>

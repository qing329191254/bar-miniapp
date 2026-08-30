<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppSelect from "../components/AppSelect.vue";
import ImgField from "../components/ImgField.vue";

const products = ref<any[]>([]);
const cats = ref<any[]>([]);
const edit = ref<any>(null);
const msg = ref("");
const catDlg = ref<null | "add" | { id: number; name: string }>(null);
const catForm = ref({ name: "", sort: 9 });
const catBusy = ref(false);

async function load() {
  const [p, c] = await Promise.all([
    api<any>("/admin/products?pageSize=0"),
    api<any>("/admin/cats?pageSize=0"),
  ]);
  products.value = Array.isArray(p) ? p : p.items || [];
  cats.value = Array.isArray(c) ? c : c.items || [];
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
const catOpts = computed(() =>
  cats.value.filter((c) => !c.disabled).map((c) => ({ value: c.id, label: c.name })),
);
const catRows = computed(() =>
  [...cats.value].sort((a, b) => (a.sort || 99) - (b.sort || 99)),
);
const defaultCid = computed(() => cats.value.find((c) => !c.disabled)?.id || cats.value[0]?.id);

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
    msg.value = "请填写分类名称";
    return;
  }
  catBusy.value = true;
  msg.value = "";
  try {
    if (catDlg.value === "add") {
      await api("/admin/cats", {
        method: "POST",
        body: { data: { name, sort: Number(catForm.value.sort) || 9 } },
      });
      msg.value = "已新增，C 端点单页同步";
    } else if (catDlg.value && typeof catDlg.value === "object") {
      await api(`/admin/cats/${catDlg.value.id}`, {
        method: "PUT",
        body: { data: { name, sort: Number(catForm.value.sort) || 99 } },
      });
      msg.value = "已保存";
    }
    closeCatDlg();
    await load();
  } catch (e: any) {
    msg.value = e?.message || "保存失败";
  } finally {
    catBusy.value = false;
  }
}

async function saveCatSort(c: any, sort: number) {
  try {
    await api(`/admin/cats/${c.id}`, { method: "PUT", body: { data: { name: c.name, sort } } });
    c.sort = sort;
  } catch (e: any) {
    msg.value = e?.message || "排序保存失败";
    await load();
  }
}

async function toggleCat(c: any) {
  msg.value = "";
  try {
    await api(`/admin/cats/${c.id}`, {
      method: "PUT",
      body: { data: { name: c.name, sort: c.sort || 99, disabled: !c.disabled } },
    });
    await load();
  } catch (e: any) {
    msg.value = e?.message || "操作失败";
  }
}

async function deleteCat(c: any) {
  const offlineN = products.value.filter((p) => p.cid === c.id && p.offline).length;
  const tip = offlineN
    ? `该分类下有 ${offlineN} 个已下架商品，删除后它们将归为「未分类」，重新上架前需先改分类。`
    : "";
  if (!window.confirm(`确认删除分类「${c.name}」？${tip ? "\n" + tip : ""}`)) return;
  msg.value = "";
  try {
    await api(`/admin/cats/${c.id}`, { method: "DELETE" });
    msg.value = "已删除";
    await load();
  } catch (e: any) {
    msg.value = e?.message || "删除失败";
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
    msg.value = "请填写商品名称";
    return;
  }
  const c = cats.value.find((x) => x.id === edit.value.cid);
  if (c?.disabled) {
    msg.value = `该商品所属分类「${c.name}」已停用，请先启用分类或改分类`;
    return;
  }
  await api("/admin/products", { method: "POST", body: { data: edit.value } });
  edit.value = null;
  msg.value = "已保存";
  await load();
}
</script>

<template>
  <div class="prod-page">
    <div class="hdr">商品管理 <em>两类 SKU：单品走核销 · 套餐下单自动发卡</em></div>
    <p class="tiny" v-if="msg" style="margin-bottom:8px">{{ msg }}</p>
    <div class="prod-grid">
      <div class="card prod-list">
        <div class="row" style="margin-bottom:11px;flex:none">
          <b>商品列表</b>
          <span class="tiny" style="margin-left:8px">在售 {{ online.length }} · 已下架 {{ offline.length }}</span>
          <button
            class="btn gold"
            style="margin-left:auto"
            @click="edit = { name:'', cid: defaultCid, price:0, type:'SINGLE', desc:'', combo:[], img:'' }"
          >＋ 新增商品</button>
        </div>
        <div class="tb-wrap">
          <table class="tb2" data-cols="lccccc">
            <thead>
              <tr><th>商品</th><th>分类</th><th>价格</th><th>类型</th><th>状态</th><th>操作</th></tr>
            </thead>
            <tbody>
            <tr v-for="p in online" :key="p.id">
              <td>
                <div class="row" style="gap:8px">
                  <img v-if="imageUrl(p.img)" class="pimg" :src="imageUrl(p.img)" alt="" />
                  <div v-else class="pimg empty">{{ (p.name || "商").slice(0,1) }}</div>
                  <div>
                    <b>{{ p.name }}</b>
                    <div class="tiny">{{ p.desc || "—" }}</div>
                  </div>
                </div>
              </td>
              <td class="tiny">{{ catName(p.cid) }}</td>
              <td><b>{{ p.price }}</b></td>
              <td><span class="pill">{{ p.type === "COMBO" ? "套餐发卡" : "单品" }}</span></td>
              <td><span class="pill" :style="{ color: p.soldOut ? '#A32D2D' : '#3B6D11' }">{{ p.soldOut ? "已估清" : "在售" }}</span></td>
              <td>
                <button class="btn ghost" @click="edit = { ...p }">编辑</button>
                <button class="btn ghost" @click="toggleSold(p)">{{ p.soldOut ? "恢复" : "估清" }}</button>
                <button class="btn ghost" style="color:#A32D2D" @click="toggleOff(p, true)">下架</button>
              </td>
            </tr>
            <tr v-if="offline.length"><td colspan="6" class="tiny" style="background:#FAF9F5">— 已下架 {{ offline.length }} 个 —</td></tr>
            <tr v-for="p in offline" :key="'o'+p.id" style="opacity:.55">
              <td>{{ p.name }}</td>
              <td class="tiny">{{ catName(p.cid) }}</td>
              <td>{{ p.price }}</td>
              <td colspan="2"></td>
              <td><button class="btn ghost" @click="toggleOff(p, false)">重新上架</button></td>
            </tr>
            <tr v-if="!online.length && !offline.length"><td colspan="6" class="table-empty">暂无商品，可点击右上角新增</td></tr>
            </tbody>
          </table>
        </div>

        <div class="card cat-section">
          <div class="row" style="margin-bottom:11px">
            <b style="font-size:14px">商品分类</b>
            <span class="tiny" style="margin-left:8px">决定 C 端点单页的顶部分类顺序</span>
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
                  <button class="btn sm cat-del" @click="deleteCat(c)">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="!catRows.length"><td colspan="5" class="table-empty">暂无商品分类</td></tr>
            </tbody>
          </table>
          <div class="tiny cat-foot">分类下仍有在售商品时不可删除，需先把商品改到其他分类或下架；停用的分类不在 C 端出现，也不能被新商品选中。</div>
        </div>
      </div>

      <div class="prod-side">
        <div v-if="edit" class="card">
          <div class="st">{{ edit.id ? "编辑 · " + edit.name : "新增商品" }} <em style="cursor:pointer" @click="edit=null">✕</em></div>
          <div class="tiny">商品图片</div>
          <ImgField v-model="edit.img" size="md" />
          <div class="tiny" style="margin:4px 0 8px">建议方图，单张 ≤ 2MB</div>
          <div class="tiny">商品名称 *</div>
          <input class="inp" v-model="edit.name" />
          <div class="tiny">分类</div>
          <AppSelect v-if="edit" v-model="edit.cid" :options="catOpts" />
          <div class="tiny">金币价格 *</div>
          <input class="inp" type="number" v-model.number="edit.price" />
          <div class="tiny">描述</div>
          <input class="inp" v-model="edit.desc" />
          <button class="btn" style="width:100%;margin-top:8px" @click="save">{{ edit.id ? "保存修改" : "创建商品" }}</button>
        </div>
      </div>
    </div>
    <div class="note prod-note">两类 SKU：① 单品走正常下单 → 接单 → 出单；② 套餐在店员接单时按配置自动发卡。下架为软删除，历史订单不受影响。</div>

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
  </div>
</template>

<style scoped>
.prod-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
}
.prod-page .hdr { flex: none; }
.prod-list {
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  overflow: hidden;
}
.tb-wrap {
  flex: none;
  overflow: auto;
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
.cat-del { color: var(--red); border-color: #E9C4C4; }
.cat-foot { margin-top: 8px; color: var(--ink3); line-height: 1.65; }
.cat-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
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
.fld {
  font-size: 12px;
  color: var(--ink2);
  margin-bottom: 4px;
}
</style>

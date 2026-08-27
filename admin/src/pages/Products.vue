<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppSelect from "../components/AppSelect.vue";
import ImgField from "../components/ImgField.vue";

const products = ref<any[]>([]);
const cats = ref<any[]>([]);
const tpls = ref<any[]>([]);
const edit = ref<any>(null);
const msg = ref("");

async function load() {
  products.value = await api("/admin/products");
  cats.value = await api("/admin/cats");
  tpls.value = await api("/admin/cardTpls");
}
onMounted(load);

function catName(id: number) {
  return cats.value.find((c) => c.id === id)?.name || "—";
}
const online = computed(() => products.value.filter((p) => !p.offline));
const offline = computed(() => products.value.filter((p) => p.offline));
const catOpts = computed(() => cats.value.map((c) => ({ value: c.id, label: c.name })));
const catRows = computed(() =>
  [...cats.value].sort((a, b) => (a.sort || 99) - (b.sort || 99)),
);

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
          <button class="btn gold" style="margin-left:auto" @click="edit = { name:'', cid: cats[0]?.id, price:0, type:'SINGLE', desc:'', combo:[], img:'' }">＋ 新增商品</button>
        </div>
        <div class="tb-wrap">
          <table class="tb2">
            <thead>
              <tr><th>商品</th><th>分类</th><th>价格</th><th>类型</th><th>状态</th><th>操作</th></tr>
            </thead>
            <tbody>
            <tr v-for="p in online" :key="p.id">
              <td>
                <div class="row" style="gap:8px">
                  <img v-if="p.img" class="pimg" :src="p.img" alt="" />
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
            </tbody>
          </table>
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
        <div class="card cat-card">
          <div class="st">商品分类 <em>点单页顶部分类</em></div>
          <table class="tb2">
            <thead>
              <tr><th>分类</th><th>在售</th></tr>
            </thead>
            <tbody>
            <tr v-for="c in catRows" :key="c.id">
              <td>
                <b>{{ c.name }}</b>
                <div class="tiny">{{ c.disabled ? "已停用" : "启用中" }}</div>
              </td>
              <td>{{ products.filter(p => p.cid === c.id && !p.offline).length }} 个</td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="note prod-note">两类 SKU：① 单品走正常下单 → 接单 → 出单；② 套餐在店员接单时按配置自动发卡。下架为软删除，历史订单不受影响。</div>
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
  flex: 1;
  min-height: 0;
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
</style>

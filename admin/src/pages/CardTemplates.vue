<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";

const rows = ref<any[]>([]);
const editingId = ref<number | null>(null);
const saving = ref(false);
const msg = ref("");
const blank = () => ({ name: "", cat: "GAME", cost: 0, days: 30, perLimit: -1, stock: -1, exch: true, use: "", desc: "", prize: "", rules: { durationMinutes: 0, weekdays: [] as number[] } });
const form = ref<any>(blank());
const categoryName = (cat: string) => cat === "GAME" ? "游戏卡" : cat === "FOOD" ? "酒水" : "其他";
const isEditing = computed(() => editingId.value !== null);
const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

async function load() { rows.value = await api<any[]>("/admin/cardTpls"); }
function openNew() { editingId.value = null; form.value = blank(); msg.value = ""; }
function openEdit(row: any) {
  editingId.value = row.id;
  form.value = { ...row, rules: { durationMinutes: Number(row.rules?.durationMinutes || 0), weekdays: (row.rules?.weekdays || []).map(Number) } };
  msg.value = "";
}
function closeForm() { openNew(); }
function normalized() {
  return { ...form.value, cost: Number(form.value.cost || 0), days: Number(form.value.days || 0),
    perLimit: Number(form.value.perLimit ?? -1), stock: Number(form.value.stock ?? -1),
    exch: form.value.cost > 0 && form.value.exch !== false,
    rules: { durationMinutes: Number(form.value.rules?.durationMinutes || 0), weekdays: (form.value.rules?.weekdays || []).map(Number) } };
}
function toggleWeekday(day: number) {
  const selected = new Set<number>(form.value.rules.weekdays || []);
  selected.has(day) ? selected.delete(day) : selected.add(day);
  form.value.rules.weekdays = [...selected].sort((a, b) => a - b);
}
async function save() {
  if (!form.value.name.trim()) { msg.value = "请填写卡券名称"; return; }
  saving.value = true;
  try {
    const item = normalized();
    if (editingId.value === null) await api("/admin/card-templates", { method: "POST", body: item });
    else await api(`/admin/card-templates/${editingId.value}`, { method: "PUT", body: item });
    await load(); openNew(); msg.value = "已保存，小程序同步更新";
  } catch (e: any) { msg.value = e.message || "保存失败"; }
  finally { saving.value = false; }
}
onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">卡券配置 <em>含积分可兑换内容配置，宝箱奖品仅店员可见</em></div>
    <div v-if="msg" class="notice">{{ msg }}</div>
    <div class="card-layout">
      <section class="card list-card">
        <div class="list-title"><b>卡券模板列表</b><button class="btn" @click="openNew">＋ 新增卡券</button></div>
        <div class="tb-wrap"><table class="tb2"><thead><tr><th>名称</th><th>分类</th><th>积分</th><th>有效期</th><th>兑换页</th><th>上限/库存</th><th>操作</th></tr></thead>
          <tbody><tr v-for="row in rows" :key="row.id"><td><b>{{ row.name }}</b></td><td class="tiny">{{ categoryName(row.cat) }}</td><td>{{ row.cost || "—" }}</td><td>{{ row.days }} 天</td><td class="tiny">{{ row.cost > 0 && row.exch !== false ? "是" : "否" }}</td><td class="tiny">{{ row.perLimit < 0 ? "不限" : row.perLimit }} / {{ row.stock < 0 ? "不限" : row.stock }}</td><td><button class="btn ghost mini" @click="openEdit(row)">编辑</button></td></tr><tr v-if="!rows.length"><td colspan="7" class="table-empty">暂无卡券模板，可点击右上角新增</td></tr></tbody>
        </table></div>
      </section>
      <section class="card edit-card">
        <div class="st">{{ isEditing ? `编辑 · ${form.name}` : "新增卡券" }} <button v-if="isEditing" class="close" @click="closeForm">×</button></div>
        <div class="form-grid"><label><span>名称 *</span><input v-model="form.name" class="inp" /></label><label><span>分类 *</span><select v-model="form.cat" class="inp"><option value="GAME">游戏卡</option><option value="FOOD">酒水卡</option><option value="OTHER">其他卡</option></select></label>
          <label><span>积分价 <i class="red">（0 = 仅奖励发放，不进兑换页）</i></span><input v-model.number="form.cost" type="number" min="0" class="inp" /></label><label><span>有效期（天）</span><input v-model.number="form.days" type="number" min="1" class="inp" /></label>
          <label><span>每人兑换上限（-1 不限）</span><input v-model.number="form.perLimit" type="number" class="inp" /></label><label><span>库存（-1 不限）</span><input v-model.number="form.stock" type="number" class="inp" /></label>
        </div>
        <label class="check"><input v-model="form.exch" :disabled="Number(form.cost) <= 0" type="checkbox" /> 出现在兑换页（积分可兑换）</label>
        <label>使用限制<input v-model="form.use" class="inp" placeholder="如 仅限周一至周四" /></label>
        <label>核销后使用时长（分钟，0 表示不限制）<input v-model.number="form.rules.durationMinutes" type="number" min="0" max="1440" class="inp" /></label>
        <div class="week-limit"><span>可核销星期（不选表示每天可核销）</span><button v-for="(day, index) in weekdays" :key="day" type="button" class="day" :class="{ on: form.rules.weekdays.includes(index + 1) }" @click="toggleWeekday(index + 1)">{{ day }}</button></div>
        <label v-if="form.cat === 'OTHER'">宝箱奖品说明（仅店员端核销可见）<input v-model="form.prize" class="inp" placeholder="如 任选一瓶 300 元内洋酒" /></label>
        <button class="btn submit" :disabled="saving" @click="save">{{ saving ? "保存中…" : isEditing ? "保存修改" : "创建卡券" }}</button>
      </section>
    </div>
    <section class="card rule-card"><div class="st">有效期规则</div><table class="tb2"><thead><tr><th>卡类型</th><th>有效期</th></tr></thead><tbody><tr><td>游戏卡 / 酒水卡</td><td><b>默认 30 天</b></td></tr><tr><td>其他卡</td><td>后台自定义</td></tr><tr><td>宝箱卡</td><td><b style="color:#BA7517">固定 7 天</b></td></tr></tbody></table></section>
    <section class="note rd tips"><b>兑换配置要点</b><br>· 积分价 &gt; 0 且勾选「兑换页」即出现在小程序兑换页<br>· 月末清零前可集中兑换，需配置库存与每人上限防挤兑<br>· 宝箱卡积分价 0，不出现在兑换页，仅奖励发放</section>
  </div>
</template>

<style scoped>
.card-layout { display:grid; grid-template-columns:minmax(0,1fr) 360px; gap:12px; align-items:start; }
.list-title { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; font-size:14px; }
.mini { padding:5px 10px; font-size:12px; }
.edit-card label { display:block; color:var(--ink2); font-size:12px; margin-bottom:9px; }
.form-grid > label > span { display:block; min-height:38px; }
.edit-card .inp { margin:5px 0 0; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:0 10px; }
.check { display:flex !important; align-items:center; gap:6px; }
.check input { margin:0; }
.week-limit { margin:-1px 0 10px; color:var(--ink2); font-size:12px; }
.week-limit > span { display:block; margin-bottom:6px; }
.day { margin:0 4px 4px 0; padding:4px 7px; border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--ink2); font-size:11px; cursor:pointer; }
.day.on { border-color:var(--blue); background:#E6F1FB; color:var(--blue); }
.submit { width:100%; margin-top:3px; }
.close { margin-left:auto; border:0; background:transparent; color:var(--ink3); font-size:20px; cursor:pointer; }
.red { color:var(--red); font-style:normal; }
.rule-card { max-width:calc(100% - 372px); }
.tips { max-width:calc(100% - 372px); color:var(--red); background:var(--redbg); border:1px solid #E24B4A; padding:12px; }
.notice { margin-bottom:10px; color:var(--green); font-size:12px; }
@media(max-width:960px) { .card-layout { grid-template-columns:1fr; }.rule-card,.tips { max-width:none; }.form-grid { grid-template-columns:1fr; } }
</style>

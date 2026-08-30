<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const cfg = ref<any>({
  enabled: true,
  order: true,
  todo: true,
  settle: true,
  tplOrder: "",
  tplTodo: "",
  tplSettle: "",
});
const loading = ref(true);
const err = ref("");
const saving = ref(false);

const scenes = [
  { key: "order", label: "新订单提醒", note: "顾客下单后推送店员：「您有新的订单，请及时处理」" },
  { key: "todo", label: "待办事项提醒", note: "待接单 / 待收款 / 草稿未提交提醒" },
  { key: "settle", label: "周结算提醒", note: "每周一结算完成后的结果通知" },
] as const;

const tplFields = [
  { key: "tplOrder", label: "新订单模板" },
  { key: "tplTodo", label: "待办模板" },
  { key: "tplSettle", label: "结算模板" },
] as const;

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<any>("/admin/push");
    cfg.value = {
      enabled: true,
      order: true,
      todo: true,
      settle: true,
      tplOrder: "模板ID：新单提醒",
      tplTodo: "模板ID：待办提醒",
      tplSettle: "模板ID：结算提醒",
      ...(data || {}),
    };
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    await api("/admin/push", { method: "PUT", body: { data: cfg.value } });
    showToast("已保存");
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'form', formSections: 3, formColumns: 1, showFilter: false, metrics: 0, showNote: true }" @retry="load">
    <div>
      <div class="hdr push-hdr">
        <span class="hdr-title">消息推送配置</span>
        <em class="hdr-note">统一管理订单、充值与卡券等业务提醒</em>
      </div>

      <div class="card push-card">
        <div class="st">总开关</div>
        <label class="push-row">
          <span class="gr">
            <b>启用微信推送</b>
            <span class="mut">需在微信公众平台申请订阅消息模板（一次授权一次推送）</span>
          </span>
          <input v-model="cfg.enabled" type="checkbox" class="ui-toggle" />
        </label>
      </div>

      <div class="card push-card">
        <div class="st">推送场景</div>
        <label v-for="scene in scenes" :key="scene.key" class="push-row" :class="{ 'no-border': scene.key === 'settle' }">
          <span class="gr">
            <b>{{ scene.label }}</b>
            <span class="mut">{{ scene.note }}</span>
          </span>
          <input v-model="cfg[scene.key]" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" />
        </label>
      </div>

      <div class="card push-card">
        <div class="st">订阅消息模板 ID</div>
        <div v-for="(field, index) in tplFields" :key="field.key" class="push-row" :class="{ 'no-border': index === tplFields.length - 1 }">
          <span class="gr"><b>{{ field.label }}</b></span>
          <input v-model="cfg[field.key]" class="inp tpl-inp" />
        </div>
      </div>

      <div class="push-actions">
        <button class="btn gold save-btn" :disabled="saving" @click="save">
          {{ saving ? "保存中…" : "保存配置" }}
        </button>
      </div>

      <div class="side-note multi">
        <div class="side-note-body">
          <p><b>替代说明：</b>已移除「打印机配置」与「语音播报」（含强制播报）。新单/待办到达通过微信订阅消息推送店员端；推送配置为全局，店员本机不再有开关。</p>
          <p>订阅消息为一次性授权，店员需在接单场景周期性授权，或在订单详情提供「开启提醒」入口。</p>
        </div>
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.push-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.push-card{padding-bottom:4px}
.push-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:20px;
  padding:12px 0;
  border-bottom:1px solid var(--line);
  cursor:pointer;
}
.push-row.no-border{border-bottom:none}
.gr{flex:1;min-width:0}
.gr b{font-size:13px;font-weight:500}
.mut{
  display:block;
  font-size:11px;
  color:var(--ink3);
  margin-top:2px;
  line-height:1.5;
}
.tpl-inp{
  width:min(280px,100%);
  margin:0;
}
.push-actions{
  display:flex;
  justify-content:flex-end;
  margin-top:2px;
}
.save-btn{
  min-width:112px;
  margin:0;
}
.save-btn:disabled{opacity:.55;cursor:not-allowed}
@media (max-width:640px){
  .push-row{align-items:flex-start;flex-direction:column;gap:10px}
  .tpl-inp{width:100%}
  .push-actions{justify-content:stretch}
  .save-btn{width:100%}
}
</style>

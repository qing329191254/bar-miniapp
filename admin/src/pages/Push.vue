<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

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
const msg = ref("");
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
  msg.value = "";
  try {
    await api("/admin/push", { method: "PUT", body: { data: cfg.value } });
    msg.value = "已保存";
  } catch (e: any) {
    msg.value = e?.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :error="err" @retry="load">
    <div>
      <div class="hdr">消息推送配置 <em>微信订阅消息 · 替代原语音播报/打印机</em></div>
      <p v-if="msg" class="notice">{{ msg }}</p>

      <div class="card">
        <div class="st">总开关</div>
        <div class="li">
          <div class="gr">
            <b>启用微信推送</b>
            <span class="mut">需在微信公众平台申请订阅消息模板（一次授权一次推送）</span>
          </div>
          <input v-model="cfg.enabled" type="checkbox" />
        </div>
      </div>

      <div class="card">
        <div class="st">推送场景</div>
        <div v-for="scene in scenes" :key="scene.key" class="li">
          <div class="gr">
            <b>{{ scene.label }}</b>
            <span class="mut">{{ scene.note }}</span>
          </div>
          <input v-model="cfg[scene.key]" type="checkbox" />
        </div>
      </div>

      <div class="card">
        <div class="st">订阅消息模板 ID</div>
        <div v-for="field in tplFields" :key="field.key" class="li">
          <div class="gr"><b>{{ field.label }}</b></div>
          <input v-model="cfg[field.key]" class="inp tpl-inp" />
        </div>
      </div>

      <button class="btn pri save-btn" :disabled="saving" @click="save">保存配置</button>

      <div class="note">
        <b>替代说明：</b>已移除「打印机配置」与「语音播报」（含强制播报）。新单/待办到达通过微信订阅消息推送店员端；推送配置为全局，店员本机不再有开关。<b>订阅消息为一次性授权</b>，店员需在接单场景周期性授权，或在订单详情提供「开启提醒」入口。
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.notice { color: var(--green); font-size: 12px; margin-bottom: 8px; }
.mut { display: block; font-size: 11px; color: var(--ink3); margin-top: 1px; }
.tpl-inp { max-width: 280px; margin: 0; }
.save-btn { margin-top: 4px; }
.note {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  font-size: 12px;
  line-height: 1.7;
}
.card .li:last-child { border-bottom: none; }
</style>

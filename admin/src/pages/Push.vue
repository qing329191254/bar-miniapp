<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const cfg = ref<any>({
  enabled: true,
  order: true,
  pay: true,
  recharge: true,
  withdrawal: true,
  pcVoice: true,
  miniVoice: true,
  miniVibrate: true,
  miniBadge: true,
  repeatSeconds: 60,
  repeatTimes: 5,
});
const router = useRouter();
const loading = ref(true);
const err = ref("");
const saving = ref(false);

const scenes = [
  { key: "order", label: "新订单", note: "实时语音、震动并更新待办角标" },
  { key: "pay", label: "待收款", note: "现场付款订单进入待处理时提醒" },
  { key: "recharge", label: "待确认充值", note: "顾客生成充值单后更新待办" },
  { key: "withdrawal", label: "待确认提分", note: "顾客提交提分单后更新待办" },
] as const;

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<any>("/admin/push");
    cfg.value = {
      enabled: true,
      order: true,
      pay: true,
      recharge: true,
      withdrawal: true,
      pcVoice: true,
      miniVoice: true,
      miniVibrate: true,
      miniBadge: true,
      repeatSeconds: 60,
      repeatTimes: 5,
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
        <span class="hdr-title">门店提醒设置</span>
        <em class="hdr-note">电脑值守 + 员工端前台实时提醒</em>
      </div>

      <div class="card push-card">
        <div class="st">门店提醒</div>
        <label class="push-row">
          <span class="gr">
            <b>启用实时值守提醒</b>
            <span class="mut">通过 WebSocket 实时通知；断线时自动切换为定时刷新</span>
          </span>
          <input v-model="cfg.enabled" type="checkbox" class="ui-toggle" />
        </label>
      </div>

      <div class="card push-card">
        <div class="st">提醒场景</div>
        <label v-for="(scene,index) in scenes" :key="scene.key" class="push-row" :class="{ 'no-border': index === scenes.length - 1 }">
          <span class="gr">
            <b>{{ scene.label }}</b>
            <span class="mut">{{ scene.note }}</span>
          </span>
          <input v-model="cfg[scene.key]" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" />
        </label>
      </div>

      <div class="card push-card">
        <div class="st">提醒方式</div>
        <label class="push-row"><span class="gr"><b>电脑端语音播报</b><span class="mut">吧台值守页收到新单后立即播报</span></span><input v-model="cfg.pcVoice" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" /></label>
        <label class="push-row"><span class="gr"><b>小程序前台语音</b><span class="mut">员工端保持前台时播放提示音</span></span><input v-model="cfg.miniVoice" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" /></label>
        <label class="push-row"><span class="gr"><b>小程序震动</b><span class="mut">新单到达时同步震动</span></span><input v-model="cfg.miniVibrate" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" /></label>
        <label class="push-row no-border"><span class="gr"><b>待办角标</b><span class="mut">员工端底部“待办”显示未处理数量</span></span><input v-model="cfg.miniBadge" type="checkbox" class="ui-toggle" :disabled="!cfg.enabled" /></label>
      </div>

      <div class="card push-card">
        <div class="st">未接单重复提醒</div>
        <div class="push-row"><span class="gr"><b>重复间隔（秒）</b><span class="mut">建议 60 秒，避免提醒过于频繁</span></span><input v-model.number="cfg.repeatSeconds" type="number" min="30" max="300" class="inp num-inp" /></div>
        <div class="push-row no-border"><span class="gr"><b>最多重复次数</b></span><input v-model.number="cfg.repeatTimes" type="number" min="0" max="10" class="inp num-inp" /></div>
      </div>

      <div class="push-actions">
        <button class="btn ghost" @click="router.push('/counter')">打开吧台值守</button>
        <button class="btn gold save-btn" :disabled="saving" @click="save">
          {{ saving ? "保存中…" : "保存配置" }}
        </button>
      </div>

      <div class="side-note multi">
        <div class="side-note-body">
          <p><b>使用说明：</b>电脑端需点击一次“开始值守”解锁浏览器音频，并保持页面打开、电脑不休眠。员工端提醒仅在小程序前台运行时生效。</p>
          <p>WebSocket 负责即时提醒；连接中断后会自动使用轮询兜底，恢复连接时重新校准待办状态。</p>
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
.num-inp{
  width:88px;
  margin:0;
  text-align:center;
}
.push-actions{
  display:flex;
  justify-content:flex-end;
  gap:8px;
  margin-top:2px;
}
.save-btn{
  min-width:112px;
  margin:0;
}
.save-btn:disabled{opacity:.55;cursor:not-allowed}
@media (max-width:640px){
  .push-row{align-items:flex-start;flex-direction:column;gap:10px}
  .num-inp{width:100%}
  .push-actions{justify-content:stretch}
  .save-btn{width:100%}
}
</style>

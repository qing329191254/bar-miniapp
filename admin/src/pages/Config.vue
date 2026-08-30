<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, savedUser } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const defaults = {
  pointLimit: false,
  pointVal: 0,
  shardLimit: false,
  shardVal: 0,
  alertRatio: 3,
  singleLimit: 5000,
  offlineTimeout: 30,
  rechargeTimeout: 30,
  verifyTtl: 5,
};

const cfg = ref({ ...defaults });
const loading = ref(true);
const err = ref("");
const saving = ref(false);
const isBoss = savedUser()?.role === "BOSS";

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<any>("/admin/config");
    cfg.value = { ...defaults, ...(data || {}) };
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!isBoss) return;
  saving.value = true;
  try {
    await api("/admin/config", { method: "PUT", body: { data: cfg.value } });
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
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'form', formSections: 1, formColumns: 1, showFilter: false, metrics: 0, showNote: true }" @retry="load">
    <div>
      <div class="hdr config-hdr">
        <span class="hdr-title">风控参数</span>
        <em class="hdr-note">{{ isBoss ? "老板可编辑" : "当前账号仅可查看" }}</em>
      </div>
      <div class="card config-card">
        <div class="config-row">
          <div class="gr">
            <b>单笔积分上限</b>
            <span class="mut">默认关闭，运营一个月后按 P95/P99 定阈值</span>
          </div>
          <div class="config-ctrl limit-ctrl">
            <input v-model="cfg.pointLimit" type="checkbox" class="ui-toggle" :disabled="!isBoss" />
            <div class="limit-inp-control" :class="{ off: !cfg.pointLimit }">
              <input
                v-model.number="cfg.pointVal"
                class="inp num-inp limit-inp"
                type="number"
                min="0"
                :disabled="!cfg.pointLimit || !isBoss"
              />
              <span class="limit-unit">分</span>
            </div>
          </div>
        </div>

        <div class="config-row">
          <div class="gr"><b>单笔碎片上限</b></div>
          <div class="config-ctrl limit-ctrl">
            <input v-model="cfg.shardLimit" type="checkbox" class="ui-toggle" :disabled="!isBoss" />
            <div class="limit-inp-control" :class="{ off: !cfg.shardLimit }">
              <input
                v-model.number="cfg.shardVal"
                class="inp num-inp limit-inp"
                type="number"
                min="0"
                :disabled="!cfg.shardLimit || !isBoss"
              />
              <span class="limit-unit">个</span>
            </div>
          </div>
        </div>

        <div class="config-row">
          <div class="gr"><b>当日录入超均值倍数告警</b></div>
          <div class="config-ctrl">
            <input v-model.number="cfg.alertRatio" class="inp num-inp" type="number" min="0" step="0.1" :disabled="!isBoss" />
          </div>
        </div>

        <div class="config-row">
          <div class="gr"><b>单笔充值上限（元）</b></div>
          <div class="config-ctrl">
            <input v-model.number="cfg.singleLimit" class="inp num-inp" type="number" min="0" :disabled="!isBoss" />
          </div>
        </div>

        <div class="config-row">
          <div class="gr"><b>到吧台付款超时（分钟）</b></div>
          <div class="config-ctrl">
            <input v-model.number="cfg.offlineTimeout" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
          </div>
        </div>

        <div class="config-row">
          <div class="gr"><b>充值单超时（分钟）</b></div>
          <div class="config-ctrl">
            <input v-model.number="cfg.rechargeTimeout" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
          </div>
        </div>

        <div class="config-row no-border">
          <div class="gr"><b>核销码有效（分钟）</b></div>
          <div class="config-ctrl">
            <input v-model.number="cfg.verifyTtl" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
          </div>
        </div>

        <div v-if="isBoss" class="config-foot">
          <button class="btn gold save-btn" :disabled="saving" @click="save">
            {{ saving ? "保存中…" : "保存配置" }}
          </button>
        </div>
      </div>

      <div class="side-note">
        <div class="side-note-body">
          <b>设置建议：</b>请先根据门店真实业务数据观察一段时间，再设置合理阈值。上限过低可能影响员工正常录入；建议结合操作记录与异常提醒持续调整。
        </div>
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.config-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.config-card{padding-bottom:0}
.config-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:20px;
  padding:12px 0;
  border-bottom:1px solid var(--line);
}
.config-row.no-border{border-bottom:none}
.gr{flex:1;min-width:0}
.gr b{font-size:13px;font-weight:500}
.mut {
  display: block;
  font-size: 11px;
  color: var(--ink3);
  margin-top: 2px;
  line-height: 1.5;
}
.config-ctrl {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: none;
  min-width: 88px;
}
.limit-ctrl {
  min-width: 148px;
  gap: 10px;
}
.limit-inp-control {
  display: inline-flex;
  align-items: stretch;
  flex: none;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(74, 52, 28, 0.04);
}
.limit-inp-control.off {
  opacity: 0.58;
}
.limit-inp {
  width: 72px;
  min-width: 72px;
  padding: 6px 8px;
  border-radius: 8px 0 0 8px;
  border-right: 0;
}
.limit-unit {
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border: 1px solid rgba(82, 59, 32, 0.18);
  border-left: 0;
  border-radius: 0 8px 8px 0;
  background: linear-gradient(180deg, #fbf8f2, #f5efe6);
  color: var(--ink2);
  font-size: 12px;
}
.num-inp {
  width: 88px;
  margin: 0;
  padding: 6px 10px;
  text-align: center;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  border-radius: 8px;
}
.num-inp:disabled,
.limit-inp:disabled {
  opacity: 1;
  background: #f7f4ee;
  cursor: not-allowed;
}
.config-foot{
  display:flex;
  justify-content:flex-end;
  padding:14px 0 16px;
  margin-top:4px;
  border-top:1px solid var(--line);
}
.save-btn {
  min-width: 112px;
  margin: 0;
}
.save-btn:disabled{opacity:.55;cursor:not-allowed}
@media (max-width: 640px) {
  .config-row{align-items:flex-start;flex-direction:column;gap:8px}
  .config-ctrl,.limit-ctrl{width:100%;justify-content:flex-start}
  .config-foot{justify-content:stretch}
  .save-btn{width:100%}
}
</style>

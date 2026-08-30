<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, savedUser } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

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
const msg = ref("");
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
  msg.value = "";
  try {
    await api("/admin/config", { method: "PUT", body: { data: cfg.value } });
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
      <div class="hdr">风控参数 <em>{{ isBoss ? "仅老板可改" : "店长只读" }}</em></div>
      <p v-if="msg" class="notice">{{ msg }}</p>

      <div class="card">
        <div class="li">
          <div class="gr">
            <b>单笔积分上限</b>
            <span class="mut">默认关闭，运营一个月后按 P95/P99 定阈值</span>
          </div>
          <div class="ctrl">
            <input v-model="cfg.pointLimit" type="checkbox" :disabled="!isBoss" />
            <input
              v-if="cfg.pointLimit"
              v-model.number="cfg.pointVal"
              class="inp num-inp"
              type="number"
              min="0"
              :disabled="!isBoss"
            />
          </div>
        </div>

        <div class="li">
          <div class="gr"><b>单笔碎片上限</b></div>
          <div class="ctrl">
            <input v-model="cfg.shardLimit" type="checkbox" :disabled="!isBoss" />
            <input
              v-if="cfg.shardLimit"
              v-model.number="cfg.shardVal"
              class="inp num-inp"
              type="number"
              min="0"
              :disabled="!isBoss"
            />
          </div>
        </div>

        <div class="li">
          <div class="gr"><b>当日录入超均值倍数告警</b></div>
          <input v-model.number="cfg.alertRatio" class="inp num-inp" type="number" min="0" step="0.1" :disabled="!isBoss" />
        </div>

        <div class="li">
          <div class="gr"><b>单笔充值上限（元）</b></div>
          <input v-model.number="cfg.singleLimit" class="inp num-inp" type="number" min="0" :disabled="!isBoss" />
        </div>

        <div class="li">
          <div class="gr"><b>到吧台付款超时（分钟）</b></div>
          <input v-model.number="cfg.offlineTimeout" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
        </div>

        <div class="li">
          <div class="gr"><b>充值单超时（分钟）</b></div>
          <input v-model.number="cfg.rechargeTimeout" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
        </div>

        <div class="li no-border">
          <div class="gr"><b>核销码有效（分钟）</b></div>
          <input v-model.number="cfg.verifyTtl" class="inp num-inp" type="number" min="1" :disabled="!isBoss" />
        </div>
      </div>

      <button v-if="isBoss" class="btn pri save-btn" :disabled="saving" @click="save">保存配置</button>

      <div class="note">
        <b>上限默认关闭的理由：</b>阈值必须来自真实业务分布，拍数字会导致店员抗拒录入——风控没做到，效率先垮。策略：先保证录入顺畅，留痕 + 告警兜底。
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.notice {
  color: var(--green);
  font-size: 12px;
  margin-bottom: 8px;
}
.mut {
  display: block;
  font-size: 11px;
  color: var(--ink3);
  margin-top: 1px;
}
.ctrl {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}
.num-inp {
  width: 90px;
  margin: 0;
  padding: 4px 7px;
  text-align: right;
}
.li.no-border {
  border-bottom: none;
}
.save-btn {
  margin-top: 4px;
}
.note {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  font-size: 12px;
  line-height: 1.7;
}
</style>

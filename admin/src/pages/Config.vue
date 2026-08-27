<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, savedUser } from "../api";

const cfg = ref<any>({});
const msg = ref("");
const isBoss = savedUser()?.role === "BOSS";

onMounted(async () => {
  cfg.value = await api("/admin/config");
});

async function save() {
  msg.value = "";
  try {
    await api("/admin/config", { method: "PUT", body: { data: cfg.value } });
    msg.value = "已保存";
  } catch (e: any) {
    msg.value = e.message;
  }
}
</script>

<template>
  <div>
    <div class="hdr">风控参数 <em>{{ isBoss ? "仅老板可改" : "店长只读" }}</em></div>
    <p class="tiny" v-if="msg" style="color:#3B6D11">{{ msg }}</p>
    <div class="card" v-if="cfg">
      <div class="li">
        <div class="gr"><b>单笔积分上限</b><span class="tiny">默认关闭，运营一个月后按真实分布定阈值</span></div>
        <input type="checkbox" v-model="cfg.pointLimit" :disabled="!isBoss" />
        <input v-if="cfg.pointLimit" class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.pointVal" :disabled="!isBoss" />
      </div>
      <div class="li">
        <div class="gr"><b>单笔碎片上限</b></div>
        <input type="checkbox" v-model="cfg.shardLimit" :disabled="!isBoss" />
        <input v-if="cfg.shardLimit" class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.shardVal" :disabled="!isBoss" />
      </div>
      <div class="li">
        <div class="gr"><b>当日录入超均值倍数告警</b></div>
        <input class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.alertRatio" :disabled="!isBoss" />
      </div>
      <div class="li">
        <div class="gr"><b>单笔充值上限（元）</b></div>
        <input class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.singleLimit" :disabled="!isBoss" />
      </div>
      <div class="li">
        <div class="gr"><b>到吧台付款超时（分钟）</b></div>
        <input class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.offlineTimeout" :disabled="!isBoss" />
      </div>
      <div class="li">
        <div class="gr"><b>充值单超时（分钟）</b></div>
        <input class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.rechargeTimeout" :disabled="!isBoss" />
      </div>
      <div class="li" style="border:none">
        <div class="gr"><b>核销码有效（分钟）</b></div>
        <input class="inp" style="width:90px;margin:0;text-align:right" type="number" v-model.number="cfg.verifyTtl" :disabled="!isBoss" />
      </div>
    </div>
    <button class="btn" v-if="isBoss" @click="save">保存配置</button>
    <div class="note" style="margin-top:12px">上限默认关闭：阈值必须来自真实业务分布。先保证录入顺畅，留痕 + 告警兜底。</div>
  </div>
</template>

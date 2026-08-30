<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

type ShopInfo = {
  name: string;
  addr: string;
  tel: string;
  hours: string;
  notice: string;
  bizDayStart: number;
};

const form = ref<ShopInfo>({
  name: "",
  addr: "",
  tel: "",
  hours: "",
  notice: "",
  bizDayStart: 6,
});
const loading = ref(true);
const err = ref("");
const saving = ref(false);

const missing = computed(() => {
  const miss: string[] = [];
  if (!form.value.name.trim()) miss.push("门店名称");
  if (!form.value.addr.trim()) miss.push("门店地址");
  if (!form.value.tel.trim()) miss.push("联系电话");
  return miss;
});

const complete = computed(() => missing.value.length === 0);

const bizDayLabel = computed(() => {
  const h = String(form.value.bizDayStart ?? 6).padStart(2, "0");
  return `${h}:00 起算`;
});

const bizDayHint = computed(() => {
  const h = String(form.value.bizDayStart ?? 6).padStart(2, "0");
  return `:00 · 营业日按「当日 ${h}:00 ~ 次日 ${h}:00」切分`;
});

function clampBizDay(v: number) {
  return Math.max(0, Math.min(23, Math.floor(Number(v) || 0)));
}

function fieldInvalid(key: "name" | "addr" | "tel") {
  return !form.value[key].trim();
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const data = await api<any>("/admin/content");
    const s = data?.shopInfo || {};
    form.value = {
      name: s.name || "",
      addr: s.addr || "",
      tel: s.tel || "",
      hours: s.hours || "",
      notice: s.notice || "",
      bizDayStart: s.bizDayStart != null ? clampBizDay(s.bizDayStart) : 6,
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
    const shopInfo = {
      ...form.value,
      name: form.value.name.trim(),
      addr: form.value.addr.trim(),
      tel: form.value.tel.trim(),
      hours: form.value.hours.trim(),
      notice: form.value.notice.trim(),
      bizDayStart: clampBizDay(form.value.bizDayStart),
    };
    await api("/admin/content", { method: "PUT", body: { data: { shopInfo } } });
    form.value = { ...shopInfo };
    showToast("门店信息已保存，并同步至顾客端");
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 0, showNote: false }" @retry="load">
    <div>
      <div class="hdr shop-hdr">
        <span class="hdr-title">门店信息</span>
        <em class="hdr-note">保存后将同步展示在小程序门店资料中</em>
        <span class="pill" :class="complete ? 'ok' : 'bad'">
          {{ complete ? "资料完整" : "待完善" }}
        </span>
      </div>
      <div v-if="missing.length" class="note rd">
        <b>门店资料尚未完善。</b>请补充：<b>{{ missing.join(" / ") }}</b>。完整、准确的经营信息便于顾客联系门店，也有助于顺利通过小程序审核。
      </div>

      <div class="layout">
        <div class="card form-card">
          <div class="field">
            <div class="fld">门店名称 <b class="req">*必填</b></div>
            <input v-model="form.name" class="inp" :class="{ invalid: fieldInvalid('name') }" placeholder="如 玩咖桌游酒吧（万象城店）" />
            <div class="hint">与营业执照一致，会显示在小程序标题与订单凭据上</div>
          </div>

          <div class="field">
            <div class="fld">门店地址 <b class="req">*必填</b></div>
            <input v-model="form.addr" class="inp" :class="{ invalid: fieldInvalid('addr') }" placeholder="如 广州市天河区天河路 208 号万象城 B2-17" />
            <div class="hint">精确到楼层与铺号，顾客靠这行字找店</div>
          </div>

          <div class="field">
            <div class="fld">联系电话 <b class="req">*必填</b></div>
            <input v-model="form.tel" class="inp" :class="{ invalid: fieldInvalid('tel') }" placeholder="如 020-8866 2043" />
            <div class="hint">顾客可从小程序直接拨打，建议填写营业时段内有人接听的号码</div>
          </div>

          <div class="field">
            <div class="fld">营业时间 <span class="opt">选填</span></div>
            <input v-model="form.hours" class="inp" placeholder="如 周一至周日 14:00 - 次日 02:00" />
            <div class="hint">跨夜时段写清「次日」，否则顾客会以为凌晨不营业</div>
          </div>

          <div class="field">
            <div class="fld">营业日起点 <span class="opt">默认 06:00 · 仅开业初期可调</span></div>
            <div class="biz-row">
              <input
                v-model.number="form.bizDayStart"
                class="inp biz-inp"
                type="number"
                min="0"
                max="23"
                @change="form.bizDayStart = clampBizDay(form.bizDayStart)"
              />
              <span class="hint inline">{{ bizDayHint }}</span>
            </div>
            <div class="hint warn">
              <b>仅开业初期可调，改动会让历史日报口径断裂：</b>凌晨 2 点的营收归前一天正是靠这个起点切出来的，一旦改动，08-25 的营收可能算进 08-24 的日报，新旧两段数据口径不同、无法横向对比。开业稳定后请勿调整。
            </div>
          </div>

          <div class="field">
            <div class="fld">门店公告 <span class="opt">选填</span></div>
            <textarea v-model="form.notice" class="inp notice-inp" placeholder="如 本店为酒类经营场所，未成年人不得饮酒。" />
            <div class="hint">展示在小程序「联系店员」页面底部，可填写预约方式或到店须知</div>
          </div>

          <button class="btn pri" :disabled="saving" @click="save">保存门店信息</button>
        </div>

        <aside>
          <div class="card">
            <div class="st">顾客端预览 <em>我的 → 联系店员</em></div>
            <div class="preview-card">
              <b>{{ form.name.trim() || "（未配置门店名称）" }}</b>
              <div class="preview-body">
                地址：{{ form.addr.trim() || "—" }}<br />
                电话：{{ form.tel.trim() || "—" }}<br />
                营业：{{ form.hours.trim() || "—" }}<br />
                营业日：{{ bizDayLabel }}
              </div>
              <div v-if="form.notice.trim()" class="preview-notice">{{ form.notice.trim() }}</div>
            </div>
          </div>
          <div class="note side-note">
            <b>展示位置：</b>小程序「我的 → 帮助与联系 → 联系店员」。请确保门店名称、地址和电话真实有效，方便顾客顺利到店或及时联系工作人员。
          </div>
        </aside>
      </div>
    </div>
  </AppAsyncPage>
</template>

<style scoped>
.shop-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.shop-hdr .pill{margin-left:8px;flex:none}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}
.pill.ok {
  background: var(--greenbg);
  color: var(--green);
}
.pill.bad {
  background: var(--redbg);
  color: var(--red);
}
.note.rd {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.6;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
  align-items: start;
}
.form-card .field {
  margin-bottom: 11px;
}
.fld {
  font-size: 12px;
  color: var(--ink2);
  margin-bottom: 4px;
}
.req {
  color: var(--red);
  font-weight: 600;
}
.opt {
  color: var(--ink3);
  font-size: 11px;
}
.inp.invalid {
  border-color: #e24b4a;
}
.hint {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink3);
  line-height: 1.6;
}
.hint.warn {
  color: var(--red);
}
.hint.inline {
  margin-top: 0;
}
.biz-row {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
}
.biz-inp {
  max-width: 110px;
  text-align: right;
  margin: 0;
}
.notice-inp {
  height: 78px;
  font-size: 12px;
  line-height: 1.7;
  resize: vertical;
}
.preview-card {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: var(--bg);
}
.preview-card > b {
  font-size: 13px;
}
.preview-body {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.9;
  color: var(--ink2);
}
.preview-notice {
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  color: var(--ink3);
  line-height: 1.7;
}
.side-note {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  font-size: 12px;
  line-height: 1.7;
}
@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>

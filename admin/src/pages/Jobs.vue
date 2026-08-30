<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import AppDateInput from "../components/AppDateInput.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";

const router = useRouter();

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

const preset = ref("7d");
const dateFrom = ref("");
const dateTo = ref("");
const opUid = ref(0);
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function avText(u: { nick?: string; av?: string }) {
  return (u.av || u.nick || "?").trim().slice(0, 2);
}
function amtPct(amount: number) {
  const max = data.value?.maxAmount || 1;
  return Math.round((amount / max) * 100);
}
function setPreset(p: string) {
  if (p !== "custom" && p === preset.value) return;
  preset.value = p;
  if (p !== "custom") {
    dateFrom.value = "";
    dateTo.value = "";
    load();
  }
}
function onCustomDateChange() {
  if (preset.value === "custom" && dateFrom.value && dateTo.value) load();
}
function openDetail(uid: number) {
  const q: Record<string, string> = { preset: preset.value };
  if (preset.value === "custom") {
    if (dateFrom.value) q.from = dateFrom.value;
    if (dateTo.value) q.to = dateTo.value;
  }
  router.push({ path: `/jobs/${uid}`, query: q });
}

const summary = computed(() => data.value?.summary || { acts: 0, amount: 0, verifies: 0, games: 0 });
const rows = computed(() => data.value?.rows || []);
const showTotal = computed(() => rows.value.length > 1);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams({ preset: preset.value });
    if (opUid.value) params.set("opUid", String(opUid.value));
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/jobs-page?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(opUid, () => load());
</script>

<template>
  <div>
    <div class="hdr jobs-hdr">
      <span class="hdr-title">员工作业记录</span>
      <em v-if="data" class="hdr-note">{{ data.staffCount }} 名操作人 · 含核销 / 接单 / 收款 / 对局录入全量流水</em>
    </div>

    <AppAsyncPage :loading="loading" :data="data" :err="err" :skeleton="{ showHeader: false, tableCols: 7 }" @retry="load">
      <div class="card flt-card">
        <div class="st">筛选 <em>当前范围：{{ data.rangeLabel }}</em></div>
        <div class="flt-chips">
          <span v-for="[p, label] in PRESETS" :key="p" class="chip" :class="{ on: preset === p }" @click="setPreset(p)">{{ label }}</span>
        </div>
        <div v-if="preset === 'custom'" class="flt-custom">
          <span class="tiny">起</span>
          <AppDateInput v-model="dateFrom" @change="onCustomDateChange" />
          <span class="tiny">止</span>
          <AppDateInput v-model="dateTo" @change="onCustomDateChange" />
        </div>
        <div class="flt-extra">
          <label class="flt-field">
            <span class="fld">操作人</span>
            <select v-model.number="opUid" class="inp flt-select">
              <option :value="0">全部操作人</option>
              <option v-for="s in data.staff || []" :key="s.id" :value="s.id">{{ s.nick }} · {{ ROLE[s.role] || s.role }}</option>
            </select>
          </label>
        </div>
      </div>

      <div class="cards job-metrics">
        <div class="mtr">
          <div class="k">作业条目</div>
          <div class="v">{{ fmt(summary.acts) }}</div>
          <div class="tiny">{{ data.rangeLabel }}</div>
        </div>
        <div class="mtr">
          <div class="k">经手金额</div>
          <div class="v">¥{{ fmt(summary.amount) }}</div>
          <div class="tiny">已归属经手人部分</div>
        </div>
        <div class="mtr">
          <div class="k">核销卡券</div>
          <div class="v">{{ fmt(summary.verifies) }}</div>
          <div class="tiny">张</div>
        </div>
        <div class="mtr">
          <div class="k">对局录入</div>
          <div class="v">{{ fmt(summary.games) }}</div>
          <div class="tiny">局</div>
        </div>
      </div>

      <div class="card table-card">
        <table class="tb2 tb-even job-table" data-cols="lccclcccc">
          <thead>
            <tr>
              <th>操作人</th><th>角色</th><th>接单</th><th>经手金额</th><th>核销</th><th>对局</th><th>发分</th><th>作业总量</th><th class="col-op">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.user.id" :class="{ inactive: r.user.status !== 'ACTIVE' }">
              <td>
                <div class="staff-cell">
                  <div class="av">{{ avText(r.user) }}</div>
                  <div>
                    <b>{{ r.user.nick }}</b>
                    <div class="tiny">{{ r.user.phone || "—" }}</div>
                  </div>
                </div>
              </td>
              <td>
                <span class="pill role-pill">{{ ROLE[r.user.role] || r.user.role }}</span>
                <div v-if="r.user.status !== 'ACTIVE'" class="tiny inactive-tag">已停用</div>
              </td>
              <td>{{ r.orders }}</td>
              <td>
                <b>¥{{ fmt(r.amount) }}</b>
                <div class="amt-bar"><div class="amt-fill" :style="{ width: amtPct(r.amount) + '%' }" /></div>
              </td>
              <td>{{ r.verifies }}</td>
              <td>{{ r.games }}<div class="tiny">{{ r.heads }} 人次</div></td>
              <td>{{ r.wds }}</td>
              <td><b>{{ r.acts }}</b> 条</td>
              <td class="col-op"><button class="btn sm" @click="openDetail(r.user.id)">查看流水</button></td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="9" class="tiny empty-row">当前筛选条件下无操作人</td>
            </tr>
            <tr v-if="showTotal" class="total-row">
              <td>合计</td>
              <td class="tiny">{{ rows.length }} 人</td>
              <td>{{ summary.orders }}</td>
              <td><b>¥{{ fmt(summary.amount) }}</b></td>
              <td>{{ summary.verifies }}</td>
              <td>{{ summary.games }}</td>
              <td>—</td>
              <td>{{ summary.acts }} 条</td>
              <td>—</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="note">
        <b>统计说明：</b>作业总量包含接单、确认充值、核销与对局录入，用于了解员工工作量，不代表个人业绩。经手金额仅统计已分配操作人的订单；「发分」统计确认发放的提分单数量。对局记录如需撤销，请前往「对局记录」处理；其他记录请联系老板。
      </div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.jobs-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  flex: none;
}
.flt-card .st em { font-weight: normal; color: var(--ink2); }
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.flt-custom { display: flex; align-items: center; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.flt-extra { margin-top: 9px; }
.flt-field .fld { display: block; color: var(--ink2); font-size: 12px; margin-bottom: 4px; }
.flt-select { max-width: 170px; margin: 0; }
.job-metrics { margin-bottom: 12px; }
.table-card { padding: 0; overflow: auto; }
.staff-cell { display: flex; align-items: center; gap: 7px; }
.av { width: 26px; height: 26px; border-radius: 50%; background: #e6f1fb; color: #185fa5; font-size: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.role-pill { background: #e6f1fb; color: #185fa5; }
.inactive { opacity: 0.5; }
.inactive-tag { color: #a32d2d; margin-top: 2px; }
.amt-bar { height: 3px; background: var(--line); border-radius: 2px; margin-top: 3px; }
.amt-fill { height: 3px; background: #ba7517; border-radius: 2px; }
.total-row { background: #faf9f5; font-weight: 600; }
.empty-row { text-align: center; padding: 26px; color: var(--ink3); }
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";

const route = useRoute();
const router = useRouter();
const uid = computed(() => Number(route.params.uid));
const preset = ref(String(route.query.preset || "today"));
const dateFrom = ref(String(route.query.from || ""));
const dateTo = ref(String(route.query.to || ""));
const tab = ref("all");
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const feedPage = ref(1);
const feedPageSize = ref(DEFAULT_PAGE_SIZE);

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

const ODST: Record<string, [string, string, string]> = {
  PENDING_PAY: ["待付款", "#BA7517", "#FAEEDA"],
  PENDING_ACCEPT: ["待接单", "#185FA5", "#E6F1FB"],
  MAKING: ["制作中", "#534AB7", "#EEEDFE"],
  FINISHED: ["已完成", "#3B6D11", "#EAF3DE"],
  CANCELLED: ["已取消", "#6B6A65", "#F5F4F0"],
  CLOSED: ["已关闭", "#6B6A65", "#F5F4F0"],
  REFUNDED: ["已退款", "#A32D2D", "#FCEBEB"],
};

type FeedItem = {
  t: string;
  kind: string;
  title: string;
  sub: string;
  val: string;
  color: string;
  pill: [string, string, string];
};

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function fmtDay(dt: Date) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
function weekName(d: string) {
  const w = new Date(`${d}T00:00:00`).getDay();
  return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][w];
}
function pillStyle(p: [string, string, string]) {
  return { color: p[1], background: p[2] };
}
function memberLabel(members: Record<number, { nick: string; tail: string }>, id: number) {
  const x = members[id];
  return x ? `${x.nick} ${x.tail}`.trim() : "—";
}
function back() {
  router.push("/jobs");
}
function setPreset(p: string) {
  preset.value = p;
  if (p !== "custom") {
    dateFrom.value = "";
    dateTo.value = "";
  }
  load(true);
}

const feed = computed<FeedItem[]>(() => data.value?.feed || []);
const feedTotal = computed(() => data.value?.feedTotal ?? 0);

const dayGroups = computed(() => {
  const map = new Map<string, FeedItem[]>();
  for (const e of feed.value) {
    const d = String(e.t || "").slice(0, 10);
    if (!map.has(d)) map.set(d, []);
    map.get(d)!.push(e);
  }
  return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
});

const tabs = computed(() => {
  const st = data.value?.stat || {};
  return [
    ["all", `全部 ${st.acts || 0}`],
    ["order", `接单 ${st.orders || 0}`],
    ["recharge", `充值 ${st.rcCount || 0}`],
    ["verify", `核销 ${st.verifies || 0}`],
    ["game", `对局 ${st.games || 0}`],
  ] as [string, string][];
});

const today = fmtDay(new Date());

async function load(resetPage = false) {
  if (resetPage) feedPage.value = 1;
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(pageQs(feedPage.value, feedPageSize.value, { preset: preset.value, tab: tab.value }));
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/jobs/${uid.value}?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => load());
watch(uid, () => load(true));
watch(tab, () => load(true));
watch([feedPage, feedPageSize], () => load());
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">{{ data?.user?.nick || "员工" }} 的作业流水</span>
      <em v-if="data" class="hdr-note">
        {{ ROLE[data.user?.role] || data.user?.role }} · {{ data.user?.phone || "—" }} · {{ data.stat?.range?.label || "—" }}
      </em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回员工列表</button>
    </div>

    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
      <div class="card">
        <div class="st">筛选 <em>当前范围：{{ data.stat?.range?.label || "—" }}</em></div>
        <div class="flt-chips">
          <span
            v-for="[p, label] in PRESETS"
            :key="p"
            class="chip"
            :class="{ on: preset === p }"
            @click="setPreset(p)"
          >{{ label }}</span>
        </div>
        <div v-if="preset === 'custom'" class="flt-custom">
          <span class="tiny">起</span>
          <input v-model="dateFrom" type="date" class="inp flt-date" @change="load" />
          <span class="tiny">止</span>
          <input v-model="dateTo" type="date" class="inp flt-date" @change="load" />
        </div>
      </div>

      <div class="cards">
        <div class="mtr">
          <div class="k">经手金额</div>
          <div class="v">¥{{ fmt(data.stat?.amount) }}</div>
          <div class="tiny">充值 ¥{{ fmt(data.stat?.rcAmt) }} + 点单 ¥{{ fmt(data.stat?.odAmt) }}</div>
        </div>
        <div class="mtr">
          <div class="k">接单</div>
          <div class="v">{{ data.stat?.orders || 0 }}</div>
          <div class="tiny">已收款 {{ data.stat?.paidOrders || 0 }} 单</div>
        </div>
        <div class="mtr">
          <div class="k">核销</div>
          <div class="v">{{ data.stat?.verifies || 0 }}</div>
          <div class="tiny">张卡券</div>
        </div>
        <div class="mtr">
          <div class="k">对局录入</div>
          <div class="v">{{ data.stat?.games || 0 }}</div>
          <div class="tiny">发出 {{ fmt(data.stat?.pts) }} 分 / {{ fmt(data.stat?.shs) }} 碎片</div>
        </div>
      </div>

      <div class="card">
        <div class="st">流水分类 <em>共 {{ feedTotal }} 条</em></div>
        <div class="flt-chips">
          <span v-for="[k, label] in tabs" :key="k" class="chip" :class="{ on: tab === k }" @click="tab = k">{{ label }}</span>
        </div>
      </div>

      <template v-if="dayGroups.length">
        <div v-for="[day, rows] in dayGroups" :key="day" class="card job-day-card">
          <div class="st">
            {{ day }}
            <em>{{ weekName(day) }} · {{ rows.length }} 条{{ day === today ? " · 今日" : "" }}</em>
          </div>
          <table class="tb2 tb-even tb-feed" data-cols="cllcc">
            <thead>
              <tr><th>时间</th><th>作业内容</th><th>对象与明细</th><th>数量/金额</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in rows" :key="day + i">
                <td class="tiny">{{ String(e.t).slice(11) || "—" }}</td>
                <td><b>{{ e.title }}</b></td>
                <td class="tiny">{{ e.sub }}</td>
                <td><b :style="{ color: e.color }">{{ e.val }}</b></td>
                <td><span class="pill" :style="pillStyle(e.pill)">{{ e.pill[0] }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <AppPagination v-if="feedTotal" v-model:page="feedPage" v-model:page-size="feedPageSize" :total="feedTotal" class="job-feed-pg" />
      <div v-else class="card"><p class="tiny" style="padding:30px;text-align:center">所选时间范围与分类下无作业流水</p></div>

      <div class="note">
        流水按作业发生时间倒序，同一天的条目归为一组。<b>此页只读</b>：核销与对局录入不可在此撤销，需分别走「对局记录查询」作废或由老板处理；订单退款在「订单记录与管理」页操作。
      </div>
    </template>
  </div>
</template>

<style scoped>
.flt-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.flt-custom {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.flt-date {
  width: auto;
  max-width: 150px;
  margin: 0;
}
.job-day-card {
  padding-bottom: 4px;
}
.job-feed-pg {
  margin-bottom: 12px;
}
</style>

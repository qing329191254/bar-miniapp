<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const WD: Record<string, [string, string]> = {
  PENDING_CONFIRM: ["待确认", "#BA7517"],
  GRANTED: ["已发放", "#3B6D11"],
  REJECTED: ["已驳回", "#A32D2D"],
  CANCELLED: ["已取消", "#9C9A93"],
  CLOSED_TIMEOUT: ["超时关闭", "#A32D2D"],
};

const route = useRoute();
const coll = computed(() => String(route.params.coll || route.path.replace("/", "")));
const rows = ref<any[]>([]);
const rowTotal = ref(0);
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const pendingItems = ref<any[]>([]);
const members = ref<any[]>([]);
const status = ref("");
const voidPreview = ref<any>(null);
const voidCards = ref(true);
const voidReason = ref("");
const voiding = ref(false);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");

const titles: Record<string, [string, string]> = {
  withdrawals: ["提分单管理", "本页仅供查询 · 请在商家移动端当面发放"],
  gameRecords: ["对局记录查询", "作废需店长以上"],
};

onMounted(load);
watch(() => route.fullPath, () => { status.value = ""; tablePage.value = 1; load(); });
watch([tablePage, tablePageSize], () => load());
watch(status, () => { tablePage.value = 1; load(); });

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const c = coll.value;
    const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value));
    if (status.value) params.set("status", status.value);
    const res = await api<any>(`/admin/${c}?${params}`);
    rows.value = res.items || [];
    rowTotal.value = res.total ?? rows.value.length;
    pendingItems.value = res.pendingItems || [];
    if (!members.value.length) members.value = await api("/admin/members?pageSize=0");
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "记录加载失败";
    if (loaded.value) showToast(err.value, true);
  } finally {
    loading.value = false;
  }
}
function nick(uid: number) {
  return members.value.find((x) => x.id === uid)?.nick || uid;
}
function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function pill(map: Record<string, [string, string]>, s: string) {
  return map[s] || [s, "#9C9A93"];
}
async function openVoid(game: any) {
  voidReason.value = "";
  voidCards.value = true;
  try {
    voidPreview.value = await api(`/admin/games/${game.id}/void-preview`);
  } catch (e: any) {
    showToast(e?.message || "加载预览失败", true);
    voidPreview.value = { id: game.id, pname: game.pname, rows: [], _err: true };
  }
}
function closeVoid() {
  voidPreview.value = null;
  voidReason.value = "";
}
async function submitVoid() {
  if (!voidPreview.value || voidPreview.value._err) return;
  if (voidReason.value.trim().length < 2) {
    showToast("作废原因至少 2 个字", true);
    return;
  }
  voiding.value = true;
  try {
    await api(`/admin/games/${voidPreview.value.id}/void`, {
      method: "POST",
      body: { reason: voidReason.value.trim(), voidCards: voidCards.value },
    });
    closeVoid();
    await load();
  } catch (e: any) {
    showToast(e?.message || "作废失败", true);
  } finally {
    voiding.value = false;
  }
}
const shown = computed(() => rows.value || []);
const pendingWdr = computed(() =>
  coll.value === "withdrawals" ? pendingItems.value : [],
);
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ showFilter: false, tableCols: coll === 'gameRecords' ? 9 : 6 }" @retry="load">
  <div>
    <div class="hdr records-hdr">{{ titles[coll]?.[0] || coll }} <em>{{ titles[coll]?.[1] }}{{ coll === 'gameRecords' ? ' · 先预览影响' : '' }}</em></div>
    <div class="note rd" v-if="coll==='withdrawals'">本页仅供查询，不支持确认发放。请由店员在商家移动端「待办」中核对顾客信息，并当面完成兑付。</div>
    <div class="card" v-if="pendingWdr.length" style="background:#FAEEDA;border-color:#BA7517">
      <div class="st" style="color:#BA7517">待确认提分单 {{ pendingWdr.length }} 张 · 发放在商家移动端完成</div>
      <div class="li" v-for="w in pendingWdr" :key="w.id">
        <div class="gr"><b>{{ w.no }} · {{ fmt(w.pts) }} 分</b><span class="tiny">{{ nick(w.uid) }} · {{ w.at || w.created }}</span></div>
        <span class="tiny">此处无操作按钮是刻意设计</span>
      </div>
    </div>
    <div class="card" style="padding:0;overflow-x:auto">
      <table class="tb2" v-if="coll==='withdrawals'" data-cols="llcccc">
        <thead>
          <tr><th>单号</th><th>会员</th><th>积分数</th><th>状态</th><th>提交时间</th><th>发放时间</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.no }}</b></td>
          <td>{{ nick(r.uid) }}</td>
          <td>{{ fmt(r.pts) }}</td>
          <td><span class="pill" :style="{ color: pill(WD, r.status)[1] }">{{ pill(WD, r.status)[0] }}</span></td>
          <td class="tiny">{{ r.at || r.created }}</td>
          <td class="tiny">{{ r.grantAt || "—" }}</td>
        </tr>
        <tr v-if="!shown.length"><td colspan="6" class="table-empty">当前筛选条件下无提分单</td></tr>
        </tbody>
      </table>
      <table class="tb2 records-table" v-else data-cols="lcccccclc">
        <thead>
          <tr><th>项目</th><th>桌台</th><th>时间</th><th>人数</th><th>积分总额</th><th>碎片总额</th><th>录入</th><th>状态</th><th class="col-op">操作</th></tr>
        </thead>
        <tbody>
        <tr v-for="r in shown" :key="r.id">
          <td><b>{{ r.pname }}</b><div v-if="r.round" class="tiny">{{ r.round }}</div></td>
          <td>{{ r.table || "—" }}</td>
          <td class="tiny">{{ r.time }}</td>
          <td>{{ (r.players || []).length }}</td>
          <td>{{ fmt((r.players || []).reduce((s: number, p: any) => s + (p.pts || 0), 0)) }}</td>
          <td>{{ fmt((r.players || []).reduce((s: number, p: any) => s + (p.sh || 0), 0)) }}</td>
          <td class="tiny">{{ r.op }}</td>
          <td><span class="pill" :class="r.status === 'VOID' ? 'records-status-void' : 'records-status-live'">{{ r.status === "VOID" ? "已作废" : "正常" }}</span></td>
          <td class="col-op"><button v-if="r.status !== 'VOID'" class="btn sm records-void-btn" @click="openVoid(r)">作废</button><span v-else class="tiny">—</span></td>
        </tr>
        <tr v-if="!shown.length"><td colspan="9" class="table-empty">当前筛选条件下无对局记录</td></tr>
        </tbody>
      </table>
      <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
    </div>
    <div v-if="coll === 'gameRecords'" class="note rd records-note"><b>作废规则：</b>余额充足时将直接扣减；余额不足会记为负数，并在顾客端显示「待抵扣」；已兑换但未核销的卡券将优先作废。跨月记录因积分已清零，不再重复扣减。作废原因必填并记入操作日志。</div>

    <div v-if="voidPreview" class="void-mask" @click.self="closeVoid">
      <div class="void-dialog">
        <div class="st">作废影响预览 <em>{{ voidPreview.pname }}</em></div>
        <table v-if="!voidPreview._err" class="tb2 void-table" data-cols="lccc">
          <thead><tr><th>玩家</th><th>应扣积分</th><th>当前余额</th><th>处理结果</th></tr></thead>
          <tbody>
            <tr v-for="item in voidPreview.rows" :key="item.uid">
              <td><b>{{ item.nick }}</b></td><td>{{ fmt(item.pts) }}</td><td>{{ fmt(item.balance) }}</td>
              <td>
                <span v-if="item.skipPts" class="pill">跨月作废 · 不扣积分</span>
                <span v-else-if="!item.pts" class="pill">无积分变动</span>
                <template v-else-if="item.neg"><span class="pill void-pill-warn">将产生负余额</span><label v-if="item.relCards" class="tiny void-card-opt"><input v-model="voidCards" type="checkbox" /> 同时作废未核销卡券 {{ item.relCards }} 张（推荐）</label></template>
                <span v-else class="pill void-pill-ok">直接扣减</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="tiny void-reason-label">作废原因（必填，至少 2 个字）</div>
        <textarea v-model="voidReason" class="inp void-reason" maxlength="100" placeholder="例如：玩家身份录错"></textarea>
        <div class="void-actions"><button class="btn ghost" :disabled="voiding" @click="closeVoid">取消</button><button class="btn void-submit" :disabled="voiding || voidPreview._err" @click="submitVoid">{{ voiding ? "处理中…" : "确认作废" }}</button></div>
      </div>
    </div>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.records-hdr em{margin-left:auto;text-align:right}
.records-table :is(th,td):first-child,.records-table :is(th,td):nth-child(7){text-align:left}
.records-table .col-op{text-align:center}
.records-status-live{background:var(--greenbg);color:var(--green)}
.records-status-void{background:var(--redbg);color:var(--red)}
.records-void-btn{border:1px solid #E9C4C4;background:#fff;color:var(--red)}
.records-note{margin-top:12px}
.void-mask{position:fixed;inset:0;z-index:60;display:flex;align-items:center;justify-content:center;padding:20px;background:rgba(28,27,25,.42)}
.void-dialog{width:min(560px,100%);max-height:min(90vh,640px);overflow:auto;padding:18px;border-radius:14px;background:#fff;box-shadow:0 18px 48px rgba(28,27,25,.24)}
.void-table td{vertical-align:top}.void-pill-warn{background:var(--redbg);color:var(--red)}.void-pill-ok{background:var(--greenbg);color:var(--green)}
.void-card-opt{display:block;margin-top:6px;line-height:1.5}.void-reason-label{margin:10px 0 6px}.void-reason{min-height:72px;resize:vertical}
.void-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}.void-actions .btn{margin:0}.void-submit{background:var(--red);color:#fff}
</style>

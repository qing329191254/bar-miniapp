<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppDateInput from "../components/AppDateInput.vue";
import AppSelect from "../components/AppSelect.vue";
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

const PRESETS: [string, string][] = [
  ["today", "今天"],
  ["yday", "昨天"],
  ["7d", "近 7 天"],
  ["30d", "近 30 天"],
  ["month", "本月"],
  ["all", "全部"],
  ["custom", "自定义"],
];
const GAME_STATUS_OPTS = [
  { value: "", label: "全部状态" },
  { value: "LIVE", label: "正常" },
  { value: "VOID", label: "已作废" },
];
const gPreset = ref("all");
const gFrom = ref("");
const gTo = ref("");
const gPid = ref(0);
const gKw = ref("");
const gStatus = ref("");
const gProjects = ref<any[]>([]);
const gTotalAll = ref(0);
const gRangeLabel = ref("");
let kwTimer: ReturnType<typeof setTimeout> | undefined;
const projectOpts = computed(() => [
  { value: 0, label: "全部项目" },
  ...gProjects.value.map((p: any) => ({ value: p.id, label: p.disabled ? `${p.name}（已停用）` : p.name })),
]);
const gFiltered = computed(() =>
  gPreset.value !== "all" || !!gPid.value || !!gKw.value.trim() || !!gStatus.value,
);
function setPreset(p: string) {
  if (p !== "custom" && p === gPreset.value) return;
  gPreset.value = p;
  if (p !== "custom") {
    gFrom.value = "";
    gTo.value = "";
    reloadFirst();
  }
}
function onCustomDateChange() {
  if (gPreset.value === "custom" && gFrom.value && gTo.value) reloadFirst();
}
function resetGameFilters() {
  gPreset.value = "all";
  gFrom.value = gTo.value = gKw.value = gStatus.value = "";
  gPid.value = 0;
  reloadFirst();
}
function reloadFirst() {
  if (tablePage.value !== 1) tablePage.value = 1;
  else load();
}

onMounted(load);
watch(() => route.fullPath, () => { status.value = ""; tablePage.value = 1; load(); });
watch([tablePage, tablePageSize], () => load());
watch(status, () => { tablePage.value = 1; load(); });
watch([gPid, gStatus], () => reloadFirst());
watch(gKw, () => {
  clearTimeout(kwTimer);
  kwTimer = setTimeout(reloadFirst, 350);
});

let loadSeq = 0;
async function load() {
  const seq = ++loadSeq;
  loading.value = true;
  err.value = "";
  try {
    const c = coll.value;
    const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value));
    let res: any;
    if (c === "gameRecords") {
      params.set("preset", gPreset.value);
      if (gPreset.value === "custom") {
        if (gFrom.value) params.set("from", gFrom.value);
        if (gTo.value) params.set("to", gTo.value);
      }
      if (gPid.value) params.set("pid", String(gPid.value));
      if (gKw.value.trim()) params.set("kw", gKw.value.trim());
      if (gStatus.value) params.set("status", gStatus.value);
      res = await api<any>(`/admin/games-page?${params}`);
      if (seq !== loadSeq) return;
      gProjects.value = res.projects || [];
      gTotalAll.value = res.totalAll ?? 0;
      gRangeLabel.value = res.rangeLabel || "";
    } else {
      if (status.value) params.set("status", status.value);
      res = await api<any>(`/admin/${c}?${params}`);
      if (seq !== loadSeq) return;
    }
    rows.value = res.items || [];
    rowTotal.value = res.total ?? rows.value.length;
    pendingItems.value = res.pendingItems || [];
    if (!members.value.length) members.value = await api("/admin/members?pageSize=0");
    loaded.value = true;
  } catch (e: any) {
    if (seq !== loadSeq) return;
    err.value = e?.message || "记录加载失败";
    if (loaded.value) showToast(err.value, true);
  } finally {
    if (seq === loadSeq) loading.value = false;
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
function closeVoid(force = false) {
  if (voiding.value && !force) return;
  voidPreview.value = null;
  voidReason.value = "";
}
async function submitVoid() {
  if (voiding.value) return;
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
    closeVoid(true);
    showToast("对局已作废");
    await load();
  } catch (e: any) {
    showToast(e?.message || "作废失败", true);
  } finally {
    voiding.value = false;
  }
}
const gameDetail = ref<any>(null);
const detailLoadingId = ref(0);
async function openDetail(game: any) {
  if (detailLoadingId.value) return;
  detailLoadingId.value = game.id;
  try {
    gameDetail.value = await api(`/admin/games/${game.id}/detail`);
  } catch (e: any) {
    showToast(e?.message || "加载详情失败", true);
  } finally {
    detailLoadingId.value = 0;
  }
}
function closeDetail() {
  gameDetail.value = null;
}
function giftCardClass(status: string) {
  if (status === "UNUSED") return "pill green";
  if (status === "LOCKED") return "pill gold";
  if (status === "USED") return "pill blue";
  return "pill grey";
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
    <div v-if="coll === 'gameRecords'" class="card flt-card">
      <div class="st">筛选 <em>当前范围：{{ gRangeLabel || "全部时间" }} · 共 {{ gTotalAll }} 局，筛出 {{ rowTotal }} 局</em><button v-if="gFiltered" class="btn sm ghost flt-reset" @click="resetGameFilters">清空筛选</button></div>
      <div class="flt-chips">
        <span v-for="[p, label] in PRESETS" :key="p" class="chip" :class="{ on: gPreset === p }" @click="setPreset(p)">{{ label }}</span>
      </div>
      <div v-if="gPreset === 'custom'" class="flt-custom">
        <span class="tiny">起</span>
        <AppDateInput v-model="gFrom" @change="onCustomDateChange" />
        <span class="tiny">止</span>
        <AppDateInput v-model="gTo" @change="onCustomDateChange" />
      </div>
      <div class="flt-extra">
        <label class="flt-field">
          <span class="fld">会员</span>
          <input v-model="gKw" class="inp flt-kw" placeholder="昵称 / 会员号 / 手机尾号" />
        </label>
        <label class="flt-field">
          <span class="fld">对局项目</span>
          <AppSelect v-model="gPid" :options="projectOpts" no-margin class="flt-select" />
        </label>
        <label class="flt-field">
          <span class="fld">状态</span>
          <AppSelect v-model="gStatus" :options="GAME_STATUS_OPTS" no-margin class="flt-select" />
        </label>
      </div>
    </div>
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
          <td class="col-op"><div class="records-ops"><button class="btn sm ghost" :class="{ 'is-loading': detailLoadingId === r.id }" :disabled="!!detailLoadingId" @click="openDetail(r)">详情</button><button v-if="r.status !== 'VOID'" class="btn sm records-void-btn" @click="openVoid(r)">作废</button><span v-else class="btn sm records-void-btn records-op-ph" aria-hidden="true">作废</span></div></td>
        </tr>
        <tr v-if="!shown.length"><td colspan="9" class="table-empty">{{ gFiltered ? "当前筛选条件下无对局记录" : "暂无对局记录" }}</td></tr>
        </tbody>
      </table>
      <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
    </div>
    <div v-if="coll === 'gameRecords'" class="note rd records-note"><b>作废规则：</b>余额充足时将直接扣减；余额不足会记为负数，并在顾客端显示「待抵扣」；已兑换但未核销的卡券将优先作废。本局赠送且未使用的卡券一并作废回滚；已核销的赠卡不回滚。跨月记录因积分已清零，不再重复扣减。作废原因必填并记入操作日志。</div>

    <Teleport to="body">
    <div v-if="gameDetail" class="void-mask" @click.self="closeDetail">
      <div class="void-dialog game-detail-dialog">
        <div class="st game-detail-head">
          <span>对局详情 <em>{{ gameDetail.pname }}{{ gameDetail.round ? ` · ${gameDetail.round}` : "" }}</em></span>
          <span class="pill" :class="gameDetail.status === 'VOID' ? 'records-status-void' : 'records-status-live'">{{ gameDetail.status === "VOID" ? "已作废" : "正常" }}</span>
        </div>
          <div class="game-detail-meta">
            <div><span class="tiny">对局时间</span><b>{{ gameDetail.time || "—" }}</b></div>
            <div><span class="tiny">桌台</span><b>{{ gameDetail.table || "未指定桌台" }}</b></div>
            <div><span class="tiny">录入人</span><b>{{ gameDetail.op || "—" }}</b></div>
            <div><span class="tiny">记录编号</span><b>#{{ gameDetail.id }}</b></div>
          </div>
          <div class="game-detail-sum tiny">共 {{ gameDetail.players.length }} 人 · 获胜 {{ gameDetail.winners }} 人 · 积分 {{ fmt(gameDetail.totalPts) }} · 碎片 {{ fmt(gameDetail.totalSh) }} · 赠卡 {{ gameDetail.totalCards }} 张</div>
          <div v-if="gameDetail.status === 'VOID'" class="note rd game-detail-void">
            <b>已作废</b>
            <template v-if="gameDetail.void">
              · {{ gameDetail.void.at }} · {{ gameDetail.void.op }}{{ gameDetail.void.role && gameDetail.void.role !== "—" ? `（${gameDetail.void.role}）` : "" }}
              <div v-if="gameDetail.void.reason">原因：{{ gameDetail.void.reason }}</div>
            </template>
          </div>
          <table class="tb2 game-detail-table" data-cols="lcccl">
            <thead><tr><th>玩家</th><th>结果</th><th>积分</th><th>碎片</th><th>赠送卡券</th></tr></thead>
            <tbody>
              <tr v-for="p in gameDetail.players" :key="p.uid">
                <td><b>{{ p.nick }}</b><div v-if="p.no" class="tiny">{{ p.no }}</div></td>
                <td>
                  <span v-if="p.win" class="pill gold">获胜</span><span v-else class="tiny">—</span>
                  <div v-if="p.win && p.event" class="tiny">{{ p.event }}</div>
                </td>
                <td>{{ p.pts ? `+${fmt(p.pts)}` : "—" }}</td>
                <td>{{ p.sh ? `+${fmt(p.sh)}` : "—" }}</td>
                <td>
                  <span v-if="!p.cards.length" class="tiny">—</span>
                  <div v-for="c in p.cards" :key="c.id || c.name" class="game-detail-card">
                    <span>{{ c.name }}</span>
                    <span v-if="c.no" class="tiny">{{ c.no }}</span>
                    <span v-if="c.statusText" :class="giftCardClass(c.status)">{{ c.statusText }}</span>
                  </div>
                </td>
              </tr>
              <tr v-if="!gameDetail.players.length"><td colspan="5" class="table-empty">本局无玩家记录</td></tr>
            </tbody>
          </table>
        <div class="void-actions"><button class="btn ghost" @click="closeDetail">关闭</button></div>
      </div>
    </div>
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
                <div v-if="item.giftUnused || item.giftUsed" class="tiny" style="margin-top:4px">
                  <span v-if="item.giftUnused">回滚赠卡 {{ item.giftUnused }} 张</span>
                  <span v-if="item.giftUsed" style="color:var(--ink3)">{{ item.giftUnused ? " · " : "" }}已用 {{ item.giftUsed }} 张不回滚</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="tiny void-reason-label">作废原因（必填，至少 2 个字）</div>
        <textarea v-model="voidReason" class="inp void-reason" maxlength="100" placeholder="例如：玩家身份录错"></textarea>
        <div class="void-actions"><button class="btn ghost" :disabled="voiding" @click="closeVoid">取消</button><button class="btn void-submit" :disabled="voiding || voidPreview._err" @click="submitVoid">{{ voiding ? "处理中…" : "确认作废" }}</button></div>
      </div>
    </div>
    </Teleport>
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
.records-ops{display:flex;justify-content:center;gap:6px}.records-ops .btn{margin:0}
.flt-card .st{display:flex;align-items:center;gap:8px}
.flt-card .st em{font-weight:normal;color:var(--ink2)}
.flt-card .st em{margin-left:auto}
.flt-reset{margin:0}
.flt-chips{display:flex;flex-wrap:wrap;gap:6px}
.flt-custom{display:flex;align-items:center;gap:6px;margin-top:10px;flex-wrap:wrap}
.flt-extra{display:flex;gap:10px;margin-top:9px;flex-wrap:wrap}
.flt-field{display:block}
.flt-field .fld{display:block;color:var(--ink2);font-size:12px;margin-bottom:4px}
.flt-field :deep(.flt-select){width:170px;max-width:170px}
.flt-kw{width:220px;margin:0}
.void-dialog.game-detail-dialog{width:min(760px,100%);max-height:min(90vh,760px)}
.game-detail-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.records-op-ph{visibility:hidden;pointer-events:none}
.records-ops .btn.is-loading{opacity:.55;cursor:progress}
.game-detail-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0 8px}
.game-detail-meta>div{display:flex;flex-direction:column;gap:2px;padding:8px 10px;border-radius:8px;background:#F7F6F2}
.game-detail-sum{margin-bottom:8px}
.game-detail-void{margin:0 0 10px;line-height:1.6}
.game-detail-table td{vertical-align:top}
.game-detail-table :is(th,td):first-child,.game-detail-table :is(th,td):last-child{text-align:left}
.game-detail-card{display:flex;flex-wrap:wrap;align-items:center;gap:6px;line-height:1.6}
.game-detail-card+.game-detail-card{margin-top:4px}
.pill.green{background:var(--greenbg);color:var(--green)}
.pill.blue{background:#E6F1FB;color:var(--blue)}
.pill.gold{background:var(--goldbg);color:var(--gold)}
.pill.grey{background:#F1EFE8;color:var(--ink3)}
.records-note{margin-top:12px}
.void-dialog{width:min(560px,100%);max-height:min(90vh,640px);overflow:auto;padding:18px;border-radius:14px;background:#fff;box-shadow:0 18px 48px rgba(28,27,25,.24)}
.void-table td{vertical-align:top}.void-pill-warn{background:var(--redbg);color:var(--red)}.void-pill-ok{background:var(--greenbg);color:var(--green)}
.void-card-opt{display:block;margin-top:6px;line-height:1.5}.void-reason-label{margin:10px 0 6px}.void-reason{min-height:72px;resize:vertical}
.void-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}.void-actions .btn{margin:0}.void-submit{background:var(--red);color:#fff}
</style>

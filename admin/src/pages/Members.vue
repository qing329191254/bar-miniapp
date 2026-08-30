<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs, savedUser } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppPagination from "../components/AppPagination.vue";
import AppSelect from "../components/AppSelect.vue";
import { showToast } from "../composables/useToast";

const route = useRoute();
const router = useRouter();
const isBoss = computed(() => savedUser()?.role === "BOSS");
const canGrantCard = computed(() => ["BOSS", "MANAGER"].includes(savedUser()?.role || ""));

const members = ref<any[]>([]);
const memberTotal = ref(0);
const totalAll = ref(0);
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const kw = ref("");
const loading = ref(true);
const err = ref("");

const detail = ref<any>(null);
const detailLoading = ref(false);
const acting = ref(false);

const uid = computed(() => Number(route.query.uid || 0));
const me = computed(() => detail.value?.member || null);
const cardTplOpts = computed(() =>
  (detail.value?.cardTpls || []).map((t: any) => ({ value: t.id, label: t.name })),
);

type AdjKind = "coin" | "point" | "shard" | "card";
const adjOpen = ref<AdjKind | null>(null);
const adjForm = ref({ delta: null as number | null, tpl: 0, qty: 1, reason: "" });

const WDR_ST: Record<string, [string, string, string]> = {
  GRANTED: ["已发放", "green", "greenbg"],
  PENDING_CONFIRM: ["待确认", "gold", "goldbg"],
  REJECTED: ["已驳回", "red", "redbg"],
  CANCELLED: ["已取消", "red", "redbg"],
  CLOSED_TIMEOUT: ["已超时", "red", "redbg"],
};

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}

function fmtPoint(av: number) {
  if (av < 0) return `−${fmt(-av)}`;
  return fmt(av);
}

function pointSub(p: { av?: number; fz?: number; wg?: number; mg?: number; pd?: number }) {
  const av = Number(p.av || 0);
  const fz = Number(p.fz || 0);
  const wg = Number(p.wg || 0);
  const mg = Number(p.mg || 0);
  const pd = Number(p.pd || 0);
  if (av < 0) return `待抵扣 ${fmt(pd || -av)}`;
  if (fz > 0) return `冻结 ${fmt(fz)} · 周 ${fmt(wg)}`;
  return `周 ${fmt(wg)} · 月 ${fmt(mg)}`;
}

function cardStatusText(status: string) {
  if (status === "UNUSED") return "未使用";
  if (status === "USED") return "已核销";
  return "已失效";
}

function cardStatusClass(status: string) {
  if (status === "UNUSED") return "pill green";
  if (status === "USED") return "pill blue";
  return "pill red";
}

function wdrOp(w: any) {
  if (w.grantBy != null) return `${w.grantOpName || "—"} · ${w.grantAt || ""}`;
  if (w.rejectBy != null) return `${w.rejectOpName || "—"} 驳回`;
  if (w.status === "CANCELLED") return "顾客取消";
  return "—";
}

function wdrStatus(w: any) {
  const st = WDR_ST[w.status];
  if (!st) return { text: w.status, cls: "pill" };
  return { text: st[0], cls: `pill ${st[1]}` };
}

async function loadMembers() {
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams(pageQs(tablePage.value, tablePageSize.value));
    if (kw.value.trim()) params.set("kw", kw.value.trim());
    const res = await api<any>(`/admin/members?${params}`);
    if (Array.isArray(res)) {
      members.value = res;
      memberTotal.value = res.length;
      totalAll.value = res.length;
    } else {
      members.value = res.items || [];
      memberTotal.value = res.total ?? members.value.length;
      totalAll.value = res.totalAll ?? memberTotal.value;
    }
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    members.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadDetail(id = uid.value) {
  if (!id) {
    detail.value = null;
    return;
  }
  detailLoading.value = true;
  err.value = "";
  try {
    detail.value = await api(`/admin/members/${id}`);
  } catch (e: any) {
    err.value = e?.message || "加载会员详情失败";
    detail.value = null;
  } finally {
    detailLoading.value = false;
  }
}

function openDetail(id: number) {
  router.push({ path: "/members", query: { uid: String(id) } });
}

function backList() {
  router.push("/members");
}

function openAdj(kind: AdjKind) {
  const tpls = detail.value?.cardTpls || [];
  adjForm.value = {
    delta: null,
    tpl: tpls[0]?.id || 0,
    qty: 1,
    reason: "",
  };
  adjOpen.value = kind;
}

async function submitAdj() {
  if (!me.value || !adjOpen.value) return;
  const reason = adjForm.value.reason.trim();
  if (reason.length < 2) {
    showToast("原因至少 2 个字", true);
    return;
  }
  if (adjOpen.value !== "card") {
    const n = Number(adjForm.value.delta || 0);
    if (!n) {
      showToast("请输入调整值", true);
      return;
    }
    if (adjOpen.value === "coin") {
      const before = Number(me.value.coin?.total || 0);
      if (n < 0 && -n > before) {
        showToast(`${isBoss.value ? "扣减失败，超出" : "扣减申请超出"}余额（当前 ${fmt(before)}）`, true);
        return;
      }
    }
    if (adjOpen.value === "shard") {
      const w = Number(me.value.shard?.w || 0);
      if (n < 0 && -n > w) {
        showToast(`扣减失败，超出本周碎片（当前 ${fmt(w)}）`, true);
        return;
      }
    }
  }
  acting.value = true;
  try {
    const id = me.value.id;
    if (adjOpen.value === "coin") {
      const res = await api<any>(`/admin/members/${id}/adjust-coin`, {
        method: "POST",
        body: { data: { delta: Number(adjForm.value.delta || 0), reason } },
      });
      showToast(res.pending ? "申请已提交，待老板审批后生效" : "已调整并留痕");
    } else if (adjOpen.value === "point") {
      await api(`/admin/members/${id}/adjust-point`, {
        method: "POST",
        body: { data: { delta: Number(adjForm.value.delta || 0), reason } },
      });
      showToast("已调整并留痕");
    } else if (adjOpen.value === "shard") {
      await api(`/admin/members/${id}/adjust-shard`, {
        method: "POST",
        body: { data: { delta: Number(adjForm.value.delta || 0), reason } },
      });
      showToast("已调整并留痕");
    } else {
      await api(`/admin/members/${id}/grant-cards`, {
        method: "POST",
        body: { data: { tpl: Number(adjForm.value.tpl), qty: Number(adjForm.value.qty || 1), reason } },
      });
      showToast("已补发");
    }
    adjOpen.value = null;
    await loadDetail(id);
  } catch (e: any) {
    showToast(e?.message || "操作失败", true);
  } finally {
    acting.value = false;
  }
}

const rejectRemarks = computed(() =>
  (detail.value?.withdrawals || []).filter((w: any) => w.rejectRemark).slice(0, 3),
);

onMounted(async () => {
  if (uid.value) await loadDetail();
  else await loadMembers();
});

watch(uid, async (id) => {
  if (id) await loadDetail(id);
  else {
    detail.value = null;
    await loadMembers();
  }
});

watch([tablePage, tablePageSize], () => {
  if (!uid.value) loadMembers();
});

let kwTimer: number | undefined;
watch(kw, () => {
  window.clearTimeout(kwTimer);
  kwTimer = window.setTimeout(() => {
    tablePage.value = 1;
    loadMembers();
  }, 300);
});
</script>

<template>
  <AppAsyncPage :loading="uid ? detailLoading : loading" :err="err" :skeleton="{ variant: uid ? 'detail' : 'table', showFilter: !uid, metrics: uid ? 4 : 0, tableCols: uid ? 5 : 9, showNote: false }" @retry="uid ? loadDetail() : loadMembers()">
    <div v-if="me">
      <div class="hdr">
        会员详情 · {{ me.nick }}
        <em class="back" @click="backList">← 返回列表</em>
      </div>
      <div class="card">
        <div class="st">基本信息</div>
        <div class="g4">
          <div><div class="fld">会员号</div><div class="ro">{{ me.no }}</div></div>
          <div><div class="fld">手机号</div><div class="ro">{{ me.phone }}</div></div>
          <div><div class="fld">性别</div><div class="ro">{{ me.gender === 1 ? "男" : me.gender === 2 ? "女" : "未知" }}</div></div>
          <div><div class="fld">注册时间</div><div class="ro muted">{{ detail.registered || "—" }}</div></div>
        </div>
      </div>

      <div class="card">
        <div class="st">资产</div>
        <div class="g4">
          <div class="mtr">
            <div class="k">金币</div>
            <div class="v gold">{{ fmt(me.coin.total) }}</div>
            <div class="tiny">本金 {{ fmt(me.coin.p) }} / 赠送 {{ fmt(me.coin.b) }}</div>
          </div>
          <div class="mtr">
            <div class="k">积分</div>
            <div class="v" :class="me.point.av < 0 ? 'red' : 'blue'">{{ fmtPoint(me.point.av) }}</div>
            <div class="tiny">{{ pointSub(me.point) }}</div>
          </div>
          <div class="mtr">
            <div class="k">碎片</div>
            <div class="v purple">{{ fmt(me.shard.w) }}</div>
            <div class="tiny">周值 · 历史 {{ fmt(me.shard.t) }}</div>
          </div>
          <div class="mtr">
            <div class="k">卡包</div>
            <div class="v">{{ detail.cardStats?.unused || 0 }} 张</div>
            <div class="tiny">已用 {{ detail.cardStats?.used || 0 }} · 失效 {{ detail.cardStats?.void || 0 }}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="st">战队</div>
        <div class="li">
          <div class="gr">
            <b>{{ me.teamName || "（无战队）" }}</b>
            <span class="mut">战队冠军 {{ detail.teamChampions || 0 }}（实时聚合）</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="st">个人冠军 <em>{{ detail.champTotal || 0 }} 次</em></div>
        <div v-for="(ch, i) in detail.champs || []" :key="i" class="li">
          <div class="gr">
            <b>{{ ch.event }}</b>
            <span class="mut">{{ ch.date }} · 参赛 {{ ch.n }} 人 · 获奖时 {{ ch.teamName }}</span>
          </div>
        </div>
        <div v-if="!(detail.champs || []).length" class="tiny empty">暂无夺冠记录</div>
      </div>

      <div class="card table-card">
        <div class="st">卡包明细</div>
        <table class="tb2 member-detail-table">
          <thead><tr><th>卡券</th><th>来源</th><th>有效期</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="cd in detail.cards || []" :key="cd.id">
              <td><b>{{ cd.tplName }}</b></td>
              <td class="tiny">{{ cd.srcDesc }}</td>
              <td class="tiny">{{ cd.expire || `${cd.daysLeft || 30} 天` }}</td>
              <td><span :class="cardStatusClass(cd.status)">{{ cardStatusText(cd.status) }}</span></td>
            </tr>
            <tr v-if="!(detail.cards || []).length"><td colspan="4" class="table-empty">暂无卡券</td></tr>
          </tbody>
        </table>
      </div>

      <div class="card table-card">
        <div class="st">
          提分单明细
          <em>累计已提出 {{ fmt(me.point.wd || 0) }} 分<span v-if="me.point.fz > 0"> · 冻结中 {{ fmt(me.point.fz) }} 分</span></em>
        </div>
        <table class="tb2 member-detail-table">
          <thead><tr><th>单号</th><th>数量</th><th>提交时间</th><th>操作人</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="w in detail.withdrawals || []" :key="w.id">
              <td><b>{{ w.no }}</b></td>
              <td>{{ fmt(w.pts) }}</td>
              <td class="tiny">{{ w.created }}</td>
              <td class="tiny">{{ wdrOp(w) }}</td>
              <td><span :class="wdrStatus(w).cls">{{ wdrStatus(w).text }}</span></td>
            </tr>
            <tr v-if="!(detail.withdrawals || []).length"><td colspan="5" class="table-empty">暂无提分记录</td></tr>
          </tbody>
        </table>
        <div v-if="rejectRemarks.length" class="tiny reject-note">
          驳回原因：{{ rejectRemarks.map((w: any) => `${w.no} — ${w.rejectRemark}`).join("；") }}
        </div>
      </div>

      <div class="card">
        <div class="st">
          手动调整
          <em>{{ isBoss ? "老板可直接调整 · 每笔留痕并推送" : "店长可发起申请 / 补发卡券" }}</em>
        </div>
        <div v-if="isBoss" class="row adj-btns">
          <button class="btn sm" @click="openAdj('coin')">调整金币</button>
          <button class="btn sm" @click="openAdj('point')">调整积分</button>
          <button class="btn sm" @click="openAdj('shard')">调整碎片</button>
          <button class="btn sm" @click="openAdj('card')">补发卡券</button>
        </div>
        <div v-else>
          <div class="row adj-btns">
            <button class="btn sm" @click="openAdj('coin')">申请调整金币</button>
            <button v-if="canGrantCard" class="btn sm" @click="openAdj('card')">补发卡券</button>
          </div>
          <div class="tiny mgr-note">
            店长提交金币调整后，<b>会员余额不会立即变化</b>；老板需在「数据看板 → 经营提醒 → 金币手动调整」中审批，审批通过后才会生效。积分与碎片仅老板可调整。
          </div>
        </div>
      </div>

      <div class="note rd multi">
        <p><b>手动调整规则：</b>老板可直接调整金币，店长提交后需老板审批；积分与碎片仅老板可调整；店长与老板均可补发卡券。每次操作必须填写原因并保留记录。碎片会影响周榜排名与宝箱卡归属，已完成结算的奖励不会随之后续调整而改变。</p>
      </div>
    </div>

    <div v-else>
      <div class="hdr members-hdr">
        <span class="hdr-title">会员列表</span>
        <em class="hdr-note">{{ totalAll }} 人 · 点击查看详情</em>
      </div>
      <div class="row toolbar">
        <input v-model="kw" class="inp search" placeholder="搜索昵称 / 会员号 / 手机尾号" />
      </div>
      <div class="card table-card">
        <table class="tb2">
          <thead>
            <tr>
              <th style="width:16%">会员</th>
              <th style="width:16%">手机</th>
              <th style="width:14%">战队</th>
              <th style="width:14%">金币</th>
              <th style="width:14%">积分</th>
              <th style="width:16%">碎片(周/总)</th>
              <th style="width:10%"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="x in members" :key="x.id" class="click-row" @click="openDetail(x.id)">
              <td><b>{{ x.nick }}</b><div class="tiny">{{ x.no }}</div></td>
              <td>{{ x.phone }}</td>
              <td class="mut">{{ x.teamName || "—" }}</td>
              <td><b class="gold">{{ fmt(x.coin.total) }}</b></td>
              <td><b class="blue">{{ fmt(x.point.av) }}</b></td>
              <td class="mut">{{ fmt(x.shard.w) }} / {{ fmt(x.shard.t) }}</td>
              <td class="tiny link">详情 ›</td>
            </tr>
            <tr v-if="!members.length">
              <td colspan="7" class="table-empty">{{ kw.trim() ? "没有匹配的会员" : "暂无会员数据" }}</td>
            </tr>
          </tbody>
        </table>
        <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="memberTotal" />
      </div>
    </div>

    <Teleport to="body">
    <div v-if="adjOpen" class="dlg-mask" @click.self="adjOpen = null">
      <section class="dlg">
        <div class="st">
          {{
            adjOpen === "coin"
              ? isBoss ? "调整金币" : "申请调整金币"
              : adjOpen === "point"
                ? "调整积分"
                : adjOpen === "shard"
                  ? "调整碎片"
                  : "补发卡券"
          }}
        </div>

        <template v-if="adjOpen === 'shard'">
          <div class="tiny shard-hint">
            当前：本周 <b class="purple">{{ fmt(me?.shard?.w || 0) }}</b> · 历史累计 <b>{{ fmt(me?.shard?.t || 0) }}</b>
          </div>
        </template>

        <template v-if="adjOpen === 'card'">
          <div class="fld">卡券模板</div>
          <AppSelect v-model="adjForm.tpl" :options="cardTplOpts" no-margin class="adj-select" />
          <div class="fld">数量</div>
          <input v-model.number="adjForm.qty" class="inp" type="number" min="1" />
        </template>

        <template v-else>
          <div class="fld">{{ adjOpen === "shard" ? "本周碎片调整值（正数增加 / 负数扣减）" : "调整值（正数增加 / 负数扣减）" }}</div>
          <input v-model.number="adjForm.delta" class="inp" type="number" :placeholder="adjOpen === 'coin' ? '如 100 或 -50' : ''" />
          <div v-if="adjOpen === 'coin' && !isBoss" class="tiny coin-hint">
            提交后<b>不会立即改动余额</b>，老板审批通过后才会正式入账。
          </div>
          <div v-if="adjOpen === 'shard'" class="tiny shard-warn">
            碎片直接影响<b>周榜排名与宝箱卡归属</b>。若本周已结算，调整不会改变已发放的奖励。历史累计将同步变动。
          </div>
        </template>

        <div class="fld">原因 *</div>
        <input v-model="adjForm.reason" class="inp" placeholder="必填，至少 2 个字" />

        <div class="dlg-actions">
          <button class="btn ghost" @click="adjOpen = null">取消</button>
          <button
            class="btn"
            :class="{ dan: adjOpen !== 'card' }"
            :disabled="acting"
            @click="submitAdj"
          >
            {{
              adjOpen === "coin"
                ? isBoss ? "确认调整" : "提交申请"
                : adjOpen === "card"
                  ? "确认补发"
                  : "确认调整"
            }}
          </button>
        </div>
      </section>
    </div>
    </Teleport>
  </AppAsyncPage>
</template>

<style scoped>
.members-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  text-align: right;
  pointer-events: auto;
  white-space: normal;
}
.back { cursor: pointer; margin-left: auto; }
.toolbar { gap: 8px; margin-bottom: 11px; }
.search { max-width: 260px; }
.table-card { padding: 0; overflow: auto; }
.table-card .st { padding: 14px 14px 0; }
.member-detail-table :is(th, td):last-child { text-align: center; }
.click-row { cursor: pointer; }
.gold { color: var(--gold); }
.blue { color: var(--blue); }
.red { color: var(--red); }
.purple { color: #534AB7; }
.mut { color: var(--ink3); }
.link { color: var(--blue); }
.g4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.fld { font-size: 12px; color: var(--ink2); margin-bottom: 4px; }
.ro { padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; font-size: 13px; }
.ro.muted { color: var(--ink3); }
.empty { padding: 8px 0; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; }
.pill.green { background: var(--greenbg); color: var(--green); }
.pill.blue { background: #E6F1FB; color: var(--blue); }
.pill.red { background: var(--redbg); color: var(--red); }
.pill.gold { background: var(--goldbg); color: var(--gold); }
.reject-note { margin: 7px 14px 14px; color: var(--ink3); }
.adj-btns { gap: 8px; flex-wrap: wrap; }
.mgr-note { margin-top: 7px; color: var(--ink3); line-height: 1.7; }
.note.rd { margin-top: 12px; padding: 12px 12px 12px 38px; border-radius: 10px; font-size: 12px; line-height: 1.6; }
.dlg {
  width: min(520px, 100%); background: #fff; border-radius: 16px; padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.dlg .inp { width: 100%; margin-bottom: 8px; }
.dlg :deep(.adj-select) { margin-bottom: 8px; }
.dlg-actions { display: grid; grid-template-columns: 1fr 1.6fr; gap: 10px; margin-top: 16px; }
.dlg-actions .btn { width: 100%; }
.shard-hint { margin-bottom: 8px; color: var(--ink3); }
.shard-warn, .coin-hint { margin: 4px 0 8px; color: var(--ink3); line-height: 1.7; }
.shard-warn { color: var(--red); }
@media (max-width: 900px) {
  .g4 { grid-template-columns: repeat(2, 1fr); }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, DEFAULT_PAGE_SIZE, pageQs } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import PointTrendChart from "./PointTrendChart.vue";

const props = defineProps<{ kind?: "coin" | "point" | "card" | "alert" }>();
const route = useRoute();
const router = useRouter();
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");
const tablePage = ref(1);
const tablePageSize = ref(DEFAULT_PAGE_SIZE);
const voidPreview = ref<any>(null);
const voidReason = ref("");
const voidCards = ref(true);
const voiding = ref(false);
const voidMsg = ref("");

const kind = computed(() => {
  const map: Record<string, "coin" | "point" | "card" | "alert"> = {
    liabCoin: "coin",
    liabPoint: "point",
    liabCard: "card",
    alertPoint: "alert",
  };
  const seg = route.path.replace(/^\//, "");
  return props.kind || map[seg] || "alert";
});

const meta = computed(() => ({
  coin: { title: "未消费金币明细", api: "/admin/liab/coin" },
  point: { title: "未清零积分明细", api: "/admin/liab/point" },
  card: { title: "未核销卡券明细", api: "/admin/liab/cards" },
  alert: { title: "积分录入异常审计", api: "/admin/alert/points" },
}[kind.value]));

const liabRows = computed(() => (kind.value !== "alert" ? data.value?.rows || [] : []));
const rowTotal = computed(() => {
  if (kind.value === "alert") return data.value?.gamesTotal ?? 0;
  return data.value?.rowTotal ?? liabRows.value.length;
});
const alertGames = computed(() => (kind.value === "alert" ? data.value?.games || [] : []));

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function back() {
  router.push("/dash");
}
function member(uid: number) {
  router.push("/members?uid=" + uid);
}
function jobs(uid: number) {
  router.push({ path: `/jobs/${uid}`, query: { preset: "today" } });
}
function catLabel(cat: string) {
  if (cat === "OTHER") return "宝箱卡";
  if (cat === "GAME") return "游戏卡";
  if (cat === "FOOD") return "酒水卡";
  return cat || "—";
}
function gamePts(g: any) {
  return (g.players || []).reduce((s: number, p: any) => s + Number(p.pts || 0), 0);
}
function gamePlayers(g: any) {
  return (g.players || []).map((p: any) => `${p.nick}${p.pts ? "（+" + fmt(p.pts) + "）" : ""}`).join("、");
}
function monthEnd(m: string) {
  const [y, mo] = String(m || "").split("-").map(Number);
  if (!y || !mo) return "月底";
  return `${mo}-${new Date(y, mo, 0).getDate()} 清零`;
}
function fmtDay(dt: Date) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
function last10Days() {
  const days: string[] = [];
  const now = new Date();
  for (let i = 9; i >= 0; i--) {
    const dt = new Date(now);
    dt.setDate(now.getDate() - i);
    days.push(fmtDay(dt));
  }
  return days;
}
const pointTrend = computed(() => {
  const today = fmtDay(new Date());
  const map = new Map((data.value?.trend || []).map((x: any) => [x.d, x]));
  return last10Days().map((d) => map.get(d) || { d, pts: 0, today: d === today });
});

async function load(resetPage = false, resetData = false) {
  if (resetPage) tablePage.value = 1;
  loading.value = true;
  err.value = "";
  if (resetData) data.value = null;
  try {
    const params = pageQs(tablePage.value, tablePageSize.value);
    data.value = await api(`${meta.value.api}?${params}`);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    if (resetData || !data.value) data.value = null;
  } finally {
    loading.value = false;
  }
}

async function openVoid(g: any) {
  voidMsg.value = "";
  voidReason.value = "";
  voidCards.value = true;
  try {
    voidPreview.value = await api(`/admin/games/${g.id}/void-preview`);
  } catch (e: any) {
    voidMsg.value = e?.message || "加载预览失败";
    voidPreview.value = { id: g.id, pname: g.pname, rows: [], _err: true };
  }
}

function closeVoid() {
  voidPreview.value = null;
  voidMsg.value = "";
  voidReason.value = "";
}

async function submitVoid() {
  if (!voidPreview.value || voidPreview.value._err) return;
  if (voidReason.value.trim().length < 2) {
    voidMsg.value = "作废原因至少 2 个字";
    return;
  }
  voiding.value = true;
  voidMsg.value = "";
  try {
    await api(`/admin/games/${voidPreview.value.id}/void`, {
      method: "POST",
      body: { reason: voidReason.value.trim(), voidCards: voidCards.value },
    });
    closeVoid();
    await load();
  } catch (e: any) {
    voidMsg.value = e?.message || "作废失败";
  } finally {
    voiding.value = false;
  }
}

onMounted(() => load());
watch(kind, () => load(true, true));
watch([tablePage, tablePageSize], () => load());
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">{{ meta.title }}</span>
      <em v-if="kind === 'alert' && data" class="hdr-note">今日 {{ fmt(data.today) }} 分 · 历史日均 {{ fmt(data.avg) }} 分</em>
      <em v-else-if="kind === 'point' && data" class="hdr-note">{{ data.summary?.month }} 月底清零 · 逐会员拆分</em>
      <em v-else-if="kind === 'coin' && data" class="hdr-note">真实负债 · 逐会员拆分</em>
      <em v-else-if="kind === 'card' && data" class="hdr-note">{{ data.summary?.total }} 张待核销 · 按卡型与会员拆分</em>
      <button class="btn sm ghost hdr-back" @click="back">‹ 返回看板</button>
    </div>

    <AppAsyncPage
      :loading="loading"
      :data="data"
      :err="err"
      :skeleton="{
        showFilter: false,
        tableCols: kind === 'card' ? 6 : 7,
        showChart: kind === 'alert',
        showNote: true,
      }"
      @retry="load()"
    >
      <template v-if="kind === 'coin'">
        <div class="cards">
          <div class="mtr"><div class="k">负债总额</div><div class="v" style="color:#A32D2D">¥{{ fmt(data.summary.total) }}</div><div class="tiny">{{ data.summary.members }} 位会员持有</div></div>
          <div class="mtr"><div class="k">其中本金</div><div class="v">¥{{ fmt(data.summary.principal) }}</div><div class="tiny">未消费可退部分</div></div>
          <div class="mtr"><div class="k">其中赠送</div><div class="v" style="color:#BA7517">¥{{ fmt(data.summary.bonus) }}</div><div class="tiny">不可退不可提现</div></div>
          <div class="mtr"><div class="k">前 5 名占比</div><div class="v">{{ data.summary.top5Pct }}%</div><div class="tiny">集中度风险</div></div>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <table class="tb2 tb-even tb-even-7" data-cols="lcccccc">
            <thead><tr><th>会员</th><th>会员号</th><th>本金余额</th><th>赠送余额</th><th>合计</th><th>占比</th><th class="col-op">操作</th></tr></thead>
            <tbody>
              <tr v-for="r in liabRows" :key="r.uid">
                <td><b>{{ r.nick }}</b></td><td class="tiny">{{ r.no }}</td>
                <td>¥{{ fmt(r.principal) }}</td><td style="color:#BA7517">¥{{ fmt(r.bonus) }}</td>
                <td><b>¥{{ fmt(r.total) }}</b></td><td class="tiny">{{ r.pct }}%</td>
                <td class="col-op"><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="7" class="tiny" style="text-align:center;padding:26px">暂无持有金币的会员</td></tr>
            </tbody>
            <tfoot v-if="data.rows.length">
              <tr class="tb-foot">
                <td><b>合计</b></td>
                <td class="tiny">{{ data.summary.members }} 人</td>
                <td>¥{{ fmt(data.summary.principal) }}</td>
                <td style="color:#BA7517">¥{{ fmt(data.summary.bonus) }}</td>
                <td><b>¥{{ fmt(data.summary.total) }}</b></td>
                <td class="tiny">100%</td>
                <td class="tiny">—</td>
              </tr>
            </tfoot>
          </table>
          <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>
        <div class="note rd">这是负债不是利润。未消费金币是顾客已付但尚未享受服务的钱。赠送部分不可退不可提现。</div>
      </template>

      <template v-else-if="kind === 'point'">
        <div class="cards">
          <div class="mtr"><div class="k">可用积分总量</div><div class="v" style="color:#185FA5">{{ fmt(data.summary.av) }}</div><div class="tiny">{{ data.summary.members }} 位会员持有</div></div>
          <div class="mtr"><div class="k">冻结中</div><div class="v">{{ fmt(data.summary.fz) }}</div><div class="tiny">提分单待确认</div></div>
          <div class="mtr"><div class="k">理论最大兑券量</div><div class="v">{{ data.summary.maxRedeem }} 张</div><div class="tiny">按最低 {{ fmt(data.summary.minCost) }} 分/张估算</div></div>
          <div class="mtr"><div class="k">负余额会员</div><div class="v" :style="data.summary.negCount ? 'color:#A32D2D' : ''">{{ data.summary.negCount }}</div><div class="tiny">对局作废导致</div></div>
        </div>
        <div class="card" v-if="data.neg?.length" style="background:#FCEBEB;border-color:#E24B4A">
          <div class="st" style="color:#A32D2D">负余额会员</div>
          <div v-for="r in data.neg" :key="r.uid" class="li"><div class="gr"><b>{{ r.nick }}</b><span class="tiny">{{ r.no }}</span></div><b style="color:#A32D2D">−{{ fmt(-r.av) }}</b></div>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <table class="tb2 tb-even tb-even-7" data-cols="lcccccc">
            <thead><tr><th>会员</th><th>会员号</th><th>可用积分</th><th>冻结中</th><th>本月获得</th><th>累计已提</th><th class="col-op">操作</th></tr></thead>
            <tbody>
              <tr v-for="r in liabRows" :key="r.uid">
                <td><b>{{ r.nick }}</b></td><td class="tiny">{{ r.no }}</td>
                <td><b style="color:#185FA5">{{ fmt(r.av) }}</b></td>
                <td>{{ r.fz ? fmt(r.fz) : "—" }}</td>
                <td class="tiny">{{ fmt(r.mg) }}</td><td class="tiny">{{ fmt(r.wd) }}</td>
                <td class="col-op"><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="7" class="tiny" style="text-align:center;padding:26px">暂无持有积分的会员</td></tr>
            </tbody>
          </table>
          <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>
        <div class="note"><b>清零规则：</b>每月最后一日 24:00 清零可用积分（<b>不清冻结额</b>——冻结的是用户已发起提取待兑付的部分，属用户资产，系统单方面清掉等于没收）。负余额一并归零。<b>月末会出现兑券挤兑</b>，卡券库存与每人上限须提前配置到位。</div>
      </template>

      <template v-else-if="kind === 'card'">
        <div class="cards">
          <div class="mtr"><div class="k">未核销总量</div><div class="v">{{ data.summary.total }}</div><div class="tiny">张</div></div>
          <div class="mtr"><div class="k">3 天内到期</div><div class="v" :style="data.summary.soon ? 'color:#A32D2D' : ''">{{ data.summary.soon }}</div><div class="tiny">需推送提醒</div></div>
          <div class="mtr"><div class="k">宝箱卡</div><div class="v" style="color:#534AB7">{{ data.summary.treasure }}</div><div class="tiny">7 天有效期</div></div>
          <div class="mtr"><div class="k">涉及会员</div><div class="v">{{ data.summary.members }}</div><div class="tiny">持券人数</div></div>
        </div>
        <div class="card">
          <div class="st">按卡型汇总 <em>{{ data.byTpl?.length || 0 }} 种</em></div>
          <table class="tb2" data-cols="lccc">
            <thead><tr><th>卡券名称</th><th>类别</th><th>未核销</th><th>3 天内到期</th></tr></thead>
            <tbody>
              <tr v-for="t in data.byTpl" :key="t.name">
                <td><b>{{ t.name }}</b></td><td class="tiny">{{ catLabel(t.cat) }}</td>
                <td><b>{{ t.n }} 张</b></td>
                <td><b v-if="t.soon" style="color:#A32D2D">{{ t.soon }}</b><span v-else class="tiny">0</span></td>
              </tr>
              <tr v-if="!data.byTpl?.length"><td colspan="4" class="table-empty">暂无卡券汇总数据</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <table class="tb2" data-cols="llllcc">
            <thead><tr><th>卡号</th><th>卡券名称</th><th>持有会员</th><th>来源</th><th>剩余有效期</th><th class="col-op">操作</th></tr></thead>
            <tbody>
              <tr v-for="r in liabRows" :key="r.id" :style="r.daysLeft <= 3 ? 'background:#FDF0F0' : ''">
                <td class="tiny">{{ r.no }}</td><td><b>{{ r.tplName }}</b></td>
                <td>{{ r.nick }} {{ r.tail }}</td><td class="tiny">{{ r.srcDesc || r.src || "—" }}</td>
                <td><b v-if="r.daysLeft <= 3" style="color:#A32D2D">{{ r.daysLeft }} 天</b><span v-else>{{ r.daysLeft }} 天</span></td>
                <td class="col-op"><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="6" class="tiny" style="text-align:center;padding:26px">暂无未核销卡券</td></tr>
            </tbody>
          </table>
          <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>
        <div class="note"><b>宝箱卡内容 C 端不展示</b>，仅店员核销页可见——否则同一张钻石宝箱不同店员给的东西会不一样。7 天有效期叠加订阅消息一次性授权，部分顾客会错过，对策为卡包角标 + 首页副标题 + 临期红标，并持续监控核销率。</div>
      </template>

      <template v-else>
        <div class="card" :style="data.over ? 'background:#FCEBEB;border-color:#E24B4A' : 'background:#EAF3DE;border-color:#97C459'">
          <div class="row">
            <div><div class="tiny" :style="data.over ? 'color:#A32D2D' : 'color:#3B6D11'">当前倍数</div><b :style="'font-size:26px;color:' + (data.over ? '#A32D2D' : '#3B6D11')">{{ data.ratio }} 倍</b></div>
            <div style="margin-left:20px"><div class="tiny">告警阈值</div><b style="font-size:18px">{{ data.threshold }} 倍</b></div>
            <div style="margin-left:auto;text-align:right">
              <span class="pill" :style="data.over ? 'background:#A32D2D;color:#fff' : 'background:#3B6D11;color:#fff'">{{ data.over ? "已触发告警" : "正常范围" }}</span>
              <div class="tiny" style="margin-top:4px">阈值可在「风控参数」调整</div>
            </div>
          </div>
        </div>
        <div class="card trend-card">
          <div class="st">近 10 日积分发放趋势 <em>红柱为今日</em></div>
          <PointTrendChart :rows="pointTrend" />
        </div>
        <div class="card">
          <div class="st">今日按录入人归集 <em>判断是个人异常还是全店普涨</em></div>
          <table class="tb2 tb-even tb-even-5" data-cols="lcccc">
            <thead><tr><th>录入店员</th><th>录入局数</th><th>发出积分</th><th>发出碎片</th><th class="col-op">操作</th></tr></thead>
            <tbody>
              <tr v-for="o in data.byOp" :key="o.opUid">
                <td><b>{{ o.op || "未指定" }}</b></td><td>{{ o.n }}</td>
                <td><b style="color:#BA7517">{{ fmt(o.pts) }}</b></td><td style="color:#534AB7">{{ fmt(o.sh) }}</td>
                <td class="col-op"><button v-if="o.opUid" class="btn sm ghost" @click="jobs(o.opUid)">查看作业流水</button><span v-else class="tiny">—</span></td>
              </tr>
              <tr v-if="!data.byOp?.length"><td colspan="5" class="tiny" style="text-align:center;padding:22px">今日暂无对局录入</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card alert-games-card">
          <div class="st">今日对局逐条 <em>{{ data.games?.length || 0 }} 局 · 可直接作废异常记录</em></div>
          <table class="tb2 tb-even tb-even-7" data-cols="clclccc">
            <thead><tr><th>时间</th><th>项目</th><th>桌台</th><th>玩家与得分</th><th>积分</th><th>录入人</th><th class="col-op">操作</th></tr></thead>
            <tbody>
              <tr v-for="g in alertGames" :key="g.id">
                <td class="tiny">{{ String(g.time || "").slice(11) || "—" }}</td>
                <td><b>{{ g.pname }}</b></td><td class="tiny">{{ g.table || "—" }}</td>
                <td class="tiny">{{ gamePlayers(g) }}</td>
                <td><b style="color:#BA7517">{{ fmt(gamePts(g)) }}</b></td>
                <td class="tiny">{{ g.op || "—" }}</td>
                <td class="col-op"><button class="btn sm void-btn" @click="openVoid(g)">作废</button></td>
              </tr>
              <tr v-if="!data.games?.length"><td colspan="7" class="tiny" style="text-align:center;padding:22px">今日暂无对局录入</td></tr>
            </tbody>
          </table>
          <AppPagination v-model:page="tablePage" v-model:page-size="tablePageSize" :total="rowTotal" />
        </div>
        <div class="note"><b>倍数为实算值</b>（今日发放量 ÷ 历史有记录日的日均），不是写死的演示数字。倍数偏高不等于作弊——周末大场次、赛事日天然会高，故此页提供按录入人归集与逐条明细，供人工判断而非自动处置。<b>作废会产生负余额</b>（分已被消费时），处理前请阅读作废影响预览。</div>
      </template>
    </AppAsyncPage>

    <div v-if="voidPreview" class="void-mask" @click.self="closeVoid">
      <div class="void-dialog">
        <div class="st">作废影响预览 <em>{{ voidPreview.pname }}</em></div>
        <table v-if="!voidPreview._err" class="tb2 void-table" data-cols="lccc">
          <thead><tr><th>玩家</th><th>应扣积分</th><th>当前余额</th><th>处理结果</th></tr></thead>
          <tbody>
            <tr v-for="r in voidPreview.rows" :key="r.uid">
              <td><b>{{ r.nick }}</b></td>
              <td>{{ fmt(r.pts) }}</td>
              <td>{{ fmt(r.balance) }}</td>
              <td>
                <span v-if="r.skipPts" class="pill">跨月作废 · 不扣积分</span>
                <span v-else-if="!r.pts" class="pill">无积分变动</span>
                <template v-else-if="r.neg">
                  <span class="pill void-pill-warn">将产生负余额</span>
                  <label v-if="r.relCards" class="tiny void-card-opt">
                    <input v-model="voidCards" type="checkbox" /> 同时作废未核销卡券 {{ r.relCards }} 张（推荐）
                  </label>
                </template>
                <span v-else class="pill void-pill-ok">直接扣减</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="tiny" style="margin:10px 0 6px">作废原因（必填，至少 2 个字）</div>
        <textarea v-model="voidReason" class="inp void-reason" maxlength="100" placeholder="例如：玩家身份录错"></textarea>
        <div v-if="voidMsg" class="void-err">{{ voidMsg }}</div>
        <div class="void-actions">
          <button class="btn ghost" :disabled="voiding" @click="closeVoid">取消</button>
          <button class="btn void-submit" :disabled="voiding || voidPreview._err" @click="submitVoid">{{ voiding ? "处理中…" : "确认作废" }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trend-card {
  padding-bottom: 10px;
}
.alert-games-card {
  padding: 14px;
  overflow: auto;
}
.tb-even {
  table-layout: fixed;
  width: 100%;
}
.tb-even th,
.tb-even td {
  overflow: hidden;
  text-overflow: ellipsis;
}
.tb-even-5 th {
  width: 20%;
}
.tb-even-7 th {
  width: 14.2857%;
}
.tb-even-7 th:nth-child(4),
.tb-even-7 td:nth-child(4) {
  white-space: normal;
  word-break: break-word;
}
.void-btn {
  color: #a32d2d;
  border: 1px solid #e9c4c4;
  background: #fff;
}
.void-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(28, 27, 25, 0.42);
}
.void-dialog {
  width: min(560px, 100%);
  max-height: min(90vh, 640px);
  overflow: auto;
  padding: 18px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(28, 27, 25, 0.24);
}
.void-table td { vertical-align: top; }
.void-pill-warn { background: #fcebeb; color: #a32d2d; }
.void-pill-ok { background: #eaf3de; color: #3b6d11; }
.void-card-opt { display: block; margin-top: 6px; line-height: 1.5; }
.void-reason { min-height: 72px; resize: vertical; }
.void-err { margin-top: 8px; font-size: 12px; color: #a32d2d; }
.void-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.void-actions .btn { margin: 0; }
.void-submit { background: #a32d2d; color: #fff; }
</style>

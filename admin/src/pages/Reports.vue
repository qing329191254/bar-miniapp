<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api, savedUser } from "../api";
import AppDateInput from "../components/AppDateInput.vue";

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

const ALL_TABS: [string, string][] = [
  ["biz", "营业"],
  ["recharge", "充值"],
  ["point", "积分"],
  ["card", "卡券"],
  ["game", "对局"],
  ["member", "会员"],
  ["staff", "员工"],
  ["liab", "负债"],
  ["recon", "对账"],
];

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };
const CAT: Record<string, string> = { GAME: "游戏", FOOD: "酒水小食", OTHER: "宝箱" };

const preset = ref("7d");
const dateFrom = ref("");
const dateTo = ref("");
const tab = ref("biz");
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");

const isBoss = computed(() => savedUser()?.role === "BOSS");
const tabs = computed(() => ALL_TABS.filter(([k]) => isBoss.value || k !== "liab"));
const body = computed(() => data.value?.body || {});
const today = computed(() => data.value?.today || "");

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function weekName(d: string) {
  const w = new Date(`${d}T00:00:00`).getDay();
  return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][w];
}
function avText(nick: string) {
  return (nick || "?").trim().slice(0, 2);
}
function diffCell(v: number) {
  if (!v) return "0";
  return `${v > 0 ? "+" : "−"}¥${fmt(Math.abs(v))}`;
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
function setTab(k: string) {
  tab.value = k;
}
function exportDemo() {
  window.alert("已导出当前报表（演示）");
}
function openJob(uid: number) {
  router.push({ path: `/jobs/${uid}`, query: { preset: preset.value } });
}
function drill(path: string) {
  router.push(path);
}

const hdrSub = computed(() => {
  if (!data.value) return "";
  return `${data.value.rangeLabel} · ${isBoss.value ? "老板视角 · 含负债" : "店长视角 · 不含负债"}`;
});

const idRows = computed(() => {
  const c = body.value.identity;
  if (!c) return [];
  return [
    ["期初余额", c.opening, "上期结转 · 账面起点"],
    ["本期获得", c.gain, "对局 + 签到发放"],
    ["本期消耗", -c.cost, `兑换卡券 ${fmt(c.costExch)} + 提分发放 ${fmt(c.costWdr)}`],
    ["本期清零", -c.cleared, "月末 24:00 清零"],
    ["期末余额", c.end, `可用 ${fmt(c.endAv)} + 冻结 ${fmt(c.endFz)}`],
  ];
});

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const params = new URLSearchParams({ preset: preset.value, tab: tab.value });
    if (preset.value === "custom") {
      if (dateFrom.value) params.set("from", dateFrom.value);
      if (dateTo.value) params.set("to", dateTo.value);
    }
    data.value = await api(`/admin/reports-page?${params}`);
    if (data.value?.tab) tab.value = data.value.tab;
  } catch (e: any) {
    err.value = e?.message || "加载失败";
    data.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(tab, () => load());
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">报表与对账</span>
      <em v-if="data" class="hdr-note">{{ hdrSub }}</em>
      <button class="btn sm ghost hdr-back" @click="exportDemo">导出当前表</button>
    </div>

    <div v-if="loading && !data" class="card"><p class="tiny loading-hint">加载中…</p></div>
    <div v-else-if="err" class="card err-card"><p>{{ err }}</p><button class="btn sm ghost" @click="load">重试</button></div>

    <template v-else-if="data">
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
      </div>

      <div class="card">
        <div class="st">报表 <em>共 {{ tabs.length }} 张 · 全部沿用上方时间范围</em></div>
        <div class="flt-chips">
          <span v-for="[k, label] in tabs" :key="k" class="chip" :class="{ on: tab === k }" @click="setTab(k)">{{ label }}</span>
        </div>
      </div>

      <!-- 营业 -->
      <template v-if="tab === 'biz'">
        <div class="cards">
          <div class="mtr"><div class="k">营业额</div><div class="v">¥{{ fmt(body.summary?.biz) }}</div><div class="tiny">{{ body.summary?.days }} 天 · 不含充值</div></div>
          <div class="mtr"><div class="k">日均</div><div class="v">¥{{ fmt(body.summary?.avg) }}</div><div class="tiny">区间平均</div></div>
          <div class="mtr"><div class="k">到店人次</div><div class="v">{{ fmt(body.summary?.guests) }}</div><div class="tiny warn">系统性偏小 · 仅供趋势</div></div>
          <div class="mtr"><div class="k">单均</div><div class="v">¥{{ fmt(body.summary?.avgOrder) }}</div><div class="tiny">{{ fmt(body.summary?.orders) }} 单 · 营业额÷订单数</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>日期</th><th>星期</th><th>金币消费</th><th>现场收款</th><th>营业额</th><th>充值额</th><th>订单</th><th>人次</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.d" :class="{ 'row-today': r.d === today }">
                <td><b>{{ r.d }}</b></td><td class="tiny">{{ weekName(r.d) }}</td>
                <td>¥{{ fmt(r.coin) }}</td><td>¥{{ fmt(r.offline) }}</td><td><b>¥{{ fmt(r.coin + r.offline) }}</b></td>
                <td class="blue">¥{{ fmt(r.recharge) }}</td><td>{{ r.orders }}</td><td class="tiny">{{ r.guests }}</td>
              </tr>
              <tr v-if="body.totals" class="total-row">
                <td>合计</td><td class="tiny">{{ body.summary?.days }} 天</td>
                <td>¥{{ fmt(body.totals.coin) }}</td><td>¥{{ fmt(body.totals.offline) }}</td>
                <td><b>¥{{ fmt(body.totals.biz) }}</b></td><td class="blue">¥{{ fmt(body.totals.recharge) }}</td>
                <td>{{ body.totals.orders }}</td><td>{{ body.totals.guests }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note"><b>口径：</b>全店营业额 = 金币消费 + 现场收款，<b>不含充值</b>。到店人次仅统计当营业日有消费的注册会员去重数，<b>未注册顾客与纯现金客不计入</b>；本页不提供「客单价」，人均类指标一律用「单均」。</div>
      </template>

      <!-- 充值 -->
      <template v-else-if="tab === 'recharge'">
        <div class="cards">
          <div class="mtr"><div class="k">实收金额</div><div class="v">¥{{ fmt(body.summary?.amt) }}</div><div class="tiny">{{ body.summary?.paidCount }} 笔已到账</div></div>
          <div class="mtr"><div class="k">赠送金币</div><div class="v gold">{{ fmt(body.summary?.bns) }}</div><div class="tiny">平台负债 · 不计收入</div></div>
          <div class="mtr"><div class="k">赠送率</div><div class="v">{{ body.summary?.bonusRate }}%</div><div class="tiny">赠送 ÷ 实收</div></div>
          <div class="mtr"><div class="k">笔均</div><div class="v">¥{{ fmt(body.summary?.avg) }}</div><div class="tiny">未完成 {{ body.summary?.incomplete }} 笔</div></div>
        </div>
        <div v-if="body.byTier?.length" class="card">
          <div class="st">档位分布 <em>判断哪个档位最受欢迎</em></div>
          <div class="tier-grid">
            <div v-for="t in body.byTier" :key="t.amount" class="tier-cell">
              <div class="tiny">¥{{ fmt(t.amount) }} 档</div>
              <b>{{ t.n }} 笔</b>
              <div class="tiny">占 {{ body.summary?.paidCount ? Math.round(t.n / body.summary.paidCount * 100) : 0 }}%</div>
            </div>
          </div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>日期</th><th>星期</th><th>笔数</th><th>实收</th><th>赠送</th><th>笔均</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.d">
                <td><b>{{ r.d }}</b></td><td class="tiny">{{ weekName(r.d) }}</td><td>{{ r.n }}</td>
                <td><b>¥{{ fmt(r.amt) }}</b></td><td class="gold">{{ fmt(r.bns) }}</td><td class="tiny">¥{{ fmt(Math.round(r.amt / r.n)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 积分 -->
      <template v-else-if="tab === 'point'">
        <div v-if="body.identity" class="card id-card" :class="body.identity.ok ? 'id-ok' : 'id-bad'">
          <div class="st id-title">积分恒等式校验 <em>期初 + 本期获得 − 本期消耗 − 清零 = 期末</em>
            <span class="pill id-pill">{{ body.identity.ok ? "账平" : `不平 · 差额 ${body.identity.diff > 0 ? "+" : ""}${fmt(body.identity.diff)}` }}</span>
          </div>
          <table class="tb2 tb-even">
            <thead><tr><th>项目</th><th>积分</th><th>说明</th></tr></thead>
            <tbody>
              <tr v-for="(row, i) in idRows" :key="i">
                <td><b>{{ row[0] }}</b></td>
                <td><b :class="{ neg: row[1] < 0 }">{{ row[1] < 0 ? "−" + fmt(-row[1]) : fmt(row[1]) }}</b></td>
                <td class="tiny">{{ row[2] }}</td>
              </tr>
              <tr class="total-row">
                <td>理论期末</td><td><b>{{ fmt(body.identity.expect) }}</b></td>
                <td class="tiny">实际期末 {{ fmt(body.identity.end) }}{{ body.identity.ok ? " · 一致" : "" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="cards">
          <div class="mtr"><div class="k">区间发放</div><div class="v">{{ fmt(body.summary?.issued) }}</div><div class="tiny">{{ body.summary?.gameCount }} 局对局</div></div>
          <div class="mtr"><div class="k">区间提分发放</div><div class="v">{{ fmt(body.summary?.wdrPts) }}</div><div class="tiny">{{ body.summary?.wdrCount }} 张已发放</div></div>
          <div class="mtr"><div class="k">冻结中</div><div class="v gold">{{ fmt(body.summary?.endFz) }}</div><div class="tiny">提分单待确认</div></div>
          <div class="mtr"><div class="k">兑券消耗</div><div class="v">{{ fmt(body.summary?.costExch) }}</div><div class="tiny">累计口径</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>日期</th><th>星期</th><th>对局数</th><th>发放积分</th><th>占区间比</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.d">
                <td><b>{{ r.d }}</b></td><td class="tiny">{{ weekName(r.d) }}</td><td>{{ r.games }}</td>
                <td><b class="gold">{{ fmt(r.pts) }}</b></td><td class="tiny">{{ r.pct }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 卡券 -->
      <template v-else-if="tab === 'card'">
        <div class="cards">
          <div class="mtr"><div class="k">累计发放</div><div class="v">{{ fmt(body.summary?.n) }}</div><div class="tiny">张 · 全部来源</div></div>
          <div class="mtr"><div class="k">已核销</div><div class="v green">{{ fmt(body.summary?.used) }}</div><div class="tiny">核销率 {{ body.summary?.rate }}%</div></div>
          <div class="mtr"><div class="k">未核销</div><div class="v red">{{ fmt(body.summary?.unused) }}</div><div class="tiny">待兑付负债</div></div>
          <div class="mtr"><div class="k">区间核销</div><div class="v">{{ fmt(body.summary?.rangeVerifies) }}</div><div class="tiny">{{ data.rangeLabel }}</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>卡券模板</th><th>类别</th><th>发放</th><th>已核销</th><th>未核销</th><th>已失效</th><th>核销率</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.id">
                <td><b>{{ r.name }}</b><div class="tiny">{{ r.cost > 0 ? "需 " + fmt(r.cost) + " 分" : "奖励发放" }}</div></td>
                <td class="tiny">{{ CAT[r.cat] || r.cat }}</td><td>{{ r.n }}</td>
                <td class="green">{{ r.used }}</td><td class="red">{{ r.unused }}</td><td class="tiny">{{ r.dead }}</td>
                <td><b>{{ r.rate }}%</b><div class="rate-bar"><div class="rate-fill" :style="{ width: r.rate + '%' }" /></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 对局 -->
      <template v-else-if="tab === 'game'">
        <div class="cards">
          <div class="mtr"><div class="k">有效对局</div><div class="v">{{ fmt(body.summary?.n) }}</div><div class="tiny">已排除 {{ body.summary?.voided }} 局作废</div></div>
          <div class="mtr"><div class="k">参与人次</div><div class="v">{{ fmt(body.summary?.heads) }}</div><div class="tiny">局均 {{ body.summary?.avgHeads }} 人</div></div>
          <div class="mtr"><div class="k">发出积分</div><div class="v gold">{{ fmt(body.summary?.pts) }}</div></div>
          <div class="mtr"><div class="k">发出碎片</div><div class="v purple">{{ fmt(body.summary?.sh) }}</div><div class="tiny">仅用于榜单评定</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>对局项目</th><th>局数</th><th>人次</th><th>局均人数</th><th>发出积分</th><th>发出碎片</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.name">
                <td><b>{{ r.name }}</b></td><td>{{ r.n }}</td><td>{{ r.heads }}</td>
                <td class="tiny">{{ r.n ? (r.heads / r.n).toFixed(1) : 0 }}</td>
                <td class="gold">{{ fmt(r.pts) }}</td><td class="purple">{{ fmt(r.sh) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 会员 -->
      <template v-else-if="tab === 'member'">
        <div class="cards">
          <div class="mtr"><div class="k">在册会员</div><div class="v">{{ body.summary?.total }}</div><div class="tiny">不含已注销</div></div>
          <div class="mtr"><div class="k">区间活跃</div><div class="v">{{ body.summary?.active }}</div><div class="tiny">活跃率 {{ body.summary?.total ? Math.round(body.summary.active / body.summary.total * 100) : 0 }}%</div></div>
          <div class="mtr"><div class="k">待注销</div><div class="v" :class="{ red: body.summary?.pending }">{{ body.summary?.pending }}</div></div>
          <div class="mtr"><div class="k">已注销</div><div class="v tiny">{{ body.summary?.gone }}</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>会员</th><th>区间消费</th><th>单数</th><th>金币余额</th><th>积分</th><th>本周碎片</th><th>未核销卡</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.id">
                <td><div class="staff-cell"><div class="av">{{ avText(r.nick) }}</div><div><b>{{ r.nick }}</b><div class="tiny">{{ r.no }}</div></div></div></td>
                <td><b>¥{{ fmt(r.spend) }}</b></td><td class="tiny">{{ r.orders }}</td>
                <td class="gold">{{ fmt(r.coin) }}</td><td :class="{ red: r.pt < 0 }">{{ r.pt < 0 ? "−" + fmt(-r.pt) : fmt(r.pt) }}</td>
                <td class="purple">{{ fmt(r.sh) }}</td><td class="tiny">{{ r.cards }}</td>
                <td><button class="btn sm" @click="drill('/members')">详情</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 员工 -->
      <template v-else-if="tab === 'staff'">
        <div class="cards">
          <div class="mtr"><div class="k">作业条目</div><div class="v">{{ fmt(body.summary?.acts) }}</div></div>
          <div class="mtr"><div class="k">经手金额</div><div class="v">¥{{ fmt(body.summary?.amount) }}</div></div>
          <div class="mtr"><div class="k">核销卡券</div><div class="v">{{ fmt(body.summary?.verifies) }}</div></div>
          <div class="mtr"><div class="k">发放提分</div><div class="v">{{ fmt(body.summary?.wds) }}</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>员工</th><th>角色</th><th>接单</th><th>经手金额</th><th>核销</th><th>对局</th><th>发分</th><th>作业量</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.user.id">
                <td><b>{{ r.user.nick }}</b><div class="tiny">{{ r.user.phone }}</div></td>
                <td><span class="pill role-pill">{{ ROLE[r.user.role] || r.user.role }}</span></td>
                <td>{{ r.orders }}</td><td><b>¥{{ fmt(r.amount) }}</b></td>
                <td>{{ r.verifies }}</td><td>{{ r.games }}<div class="tiny">{{ r.heads }} 人次</div></td>
                <td>{{ r.wds }}</td><td><b>{{ r.acts }}</b></td>
                <td><button class="btn sm" @click="openJob(r.user.id)">查看流水</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 负债 -->
      <template v-else-if="tab === 'liab'">
        <div class="cards">
          <div class="mtr"><div class="k">金币负债合计</div><div class="v red">¥{{ fmt(body.summary?.coinTotal) }}</div></div>
          <div class="mtr"><div class="k">其中可退部分</div><div class="v">¥{{ fmt(body.summary?.coinP) }}</div></div>
          <div class="mtr"><div class="k">积分负债</div><div class="v blue">{{ fmt(body.summary?.ptEnd) }}</div></div>
          <div class="mtr"><div class="k">卡券负债</div><div class="v purple">{{ body.summary?.cardCount }} 张</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even">
            <thead><tr><th>负债科目</th><th>余额</th><th>性质与释放条件</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.key">
                <td><b>{{ r.label }}</b></td>
                <td><b :style="{ color: r.color }">{{ r.display }}</b></td>
                <td class="tiny">{{ r.desc }}</td>
                <td><button class="btn sm" @click="drill(r.link)">逐户下钻</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note rd"><b>这是负债不是利润。</b>未消费金币是顾客已付但尚未享受服务的钱。积分与卡券是兑付义务而非现金负债。</div>
      </template>

      <!-- 对账 -->
      <template v-else-if="tab === 'recon'">
        <div class="cards">
          <div class="mtr"><div class="k">对账天数</div><div class="v">{{ body.summary?.days }}</div></div>
          <div class="mtr"><div class="k">有差异天数</div><div class="v" :class="body.summary?.bad ? 'red' : 'green'">{{ body.summary?.bad }}</div></div>
          <div class="mtr"><div class="k">日结营业额</div><div class="v">¥{{ fmt(body.summary?.sumBiz) }}</div></div>
          <div class="mtr"><div class="k">流水营业额</div><div class="v">¥{{ fmt(body.summary?.flowBiz) }}</div></div>
        </div>
        <div class="card table-card">
          <table class="tb2 tb-even recon-table">
            <thead><tr><th>日期</th><th>日结金币</th><th>流水金币</th><th>金币差额</th><th>日结现场</th><th>流水现场</th><th>现场差额</th><th>充值差额</th><th>状态</th></tr></thead>
            <tbody>
              <tr v-for="r in body.rows || []" :key="r.d" :class="{ 'row-bad': !r.ok }">
                <td><b>{{ r.d }}</b><div class="tiny">{{ weekName(r.d) }}</div></td>
                <td>¥{{ fmt(r.sumCoin) }}</td><td class="tiny">¥{{ fmt(r.flowCoin) }}</td>
                <td><b :class="{ red: r.dCoin }">{{ diffCell(r.dCoin) }}</b></td>
                <td>¥{{ fmt(r.sumOffline) }}</td><td class="tiny">¥{{ fmt(r.flowOffline) }}</td>
                <td><b :class="{ red: r.dOffline }">{{ diffCell(r.dOffline) }}</b></td>
                <td><b :class="{ red: r.dRc }">{{ diffCell(r.dRc) }}</b></td>
                <td><span class="pill" :class="r.ok ? 'pill-ok' : 'pill-bad'">{{ r.ok ? "账平" : "有差异" }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="note"><b>对账在比什么：</b>左侧「日结」是每日营业汇总表，右侧「流水」是订单与充值单逐笔实算值。对不上说明有单没录、或录了没进汇总。</div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.hdr-back { margin-left: auto; }
.loading-hint { padding: 24px; text-align: center; }
.err-card { background: #fcebeb; border-color: #e24b4a; }
.err-card p { color: #a32d2d; padding: 16px; }
.flt-card .st em { font-weight: normal; color: var(--ink2); }
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.flt-custom { display: flex; align-items: center; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.table-card { padding: 0; overflow: auto; margin-bottom: 12px; }
.total-row { background: #faf9f5; font-weight: 600; }
.row-today { background: #fdf4e3; }
.row-bad { background: #fdf3f3; }
.tiny.warn { color: #a32d2d; }
.blue { color: #185fa5; }
.gold { color: #ba7517; }
.green { color: #3b6d11; }
.red { color: #a32d2d; }
.purple { color: #534ab7; }
.neg { color: #a32d2d; }
.tier-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.tier-cell { background: #faf9f5; border-radius: 9px; padding: 10px 12px; }
.tier-cell b { font-size: 16px; }
.id-card { margin-bottom: 12px; }
.id-ok { background: #eaf3de; border-color: #97c459; }
.id-bad { background: #fcebeb; border-color: #e24b4a; }
.id-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.id-pill { margin-left: auto; background: #3b6d11; color: #fff; }
.id-bad .id-pill { background: #a32d2d; }
.rate-bar { height: 3px; background: var(--line); border-radius: 2px; margin-top: 3px; }
.rate-fill { height: 3px; background: #3b6d11; border-radius: 2px; }
.staff-cell { display: flex; align-items: center; gap: 7px; }
.av { width: 26px; height: 26px; border-radius: 50%; background: #e6f1fb; color: #185fa5; font-size: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.role-pill { background: #e6f1fb; color: #185fa5; }
.pill-ok { background: #eaf3de; color: #3b6d11; }
.pill-bad { background: #fcebeb; color: #a32d2d; }
.recon-table { font-size: 12px; }
@media (max-width: 960px) {
  .tier-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>

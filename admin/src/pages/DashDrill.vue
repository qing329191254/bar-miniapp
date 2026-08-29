<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";

const props = defineProps<{ kind?: "coin" | "point" | "card" | "alert" }>();
const route = useRoute();
const router = useRouter();
const data = ref<any>(null);
const loading = ref(true);
const err = ref("");

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
  router.push("/jobs?uid=" + uid);
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
function trendHeight(t: any, list: any[]) {
  const max = Math.max(...list.map((x) => Number(x.pts || 0)), 1);
  return Math.max(4, (Number(t.pts || 0) / max) * 88);
}

async function load() {
  loading.value = true;
  err.value = "";
  data.value = null;
  try {
    data.value = await api(meta.value.api);
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(kind, load);
</script>

<template>
  <div>
    <div class="hdr">
      {{ meta.title }}
      <em v-if="kind === 'alert' && data">今日 {{ fmt(data.today) }} 分 · 历史日均 {{ fmt(data.avg) }} 分</em>
      <em v-else-if="kind === 'point' && data">{{ data.summary?.month }} · {{ monthEnd(data.summary?.month) }}</em>
      <em v-else-if="kind === 'card' && data">{{ data.summary?.total }} 张待核销</em>
      <button class="btn sm ghost" style="margin-left:auto" @click="back">‹ 返回看板</button>
    </div>

    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else-if="err" class="card" style="background:#FCEBEB;border-color:#E24B4A">
      <p style="color:#A32D2D;padding:16px">{{ err }}</p>
      <button class="btn sm ghost" style="margin:0 16px 16px" @click="load">重试</button>
    </div>

    <template v-else-if="data">
      <template v-if="kind === 'coin'">
        <div class="cards">
          <div class="mtr"><div class="k">负债总额</div><div class="v" style="color:#A32D2D">¥{{ fmt(data.summary.total) }}</div><div class="tiny">{{ data.summary.members }} 位会员持有</div></div>
          <div class="mtr"><div class="k">其中本金</div><div class="v">¥{{ fmt(data.summary.principal) }}</div><div class="tiny">未消费可退部分</div></div>
          <div class="mtr"><div class="k">其中赠送</div><div class="v" style="color:#BA7517">¥{{ fmt(data.summary.bonus) }}</div><div class="tiny">不可退不可提现</div></div>
          <div class="mtr"><div class="k">前 5 名占比</div><div class="v">{{ data.summary.top5Pct }}%</div><div class="tiny">集中度风险</div></div>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <table class="tb2">
            <thead><tr><th>会员</th><th>会员号</th><th>本金余额</th><th>赠送余额</th><th>合计</th><th>占比</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in data.rows" :key="r.uid">
                <td><b>{{ r.nick }}</b></td><td class="tiny">{{ r.no }}</td>
                <td>¥{{ fmt(r.principal) }}</td><td style="color:#BA7517">¥{{ fmt(r.bonus) }}</td>
                <td><b>¥{{ fmt(r.total) }}</b></td><td class="tiny">{{ r.pct }}%</td>
                <td><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="7" class="tiny" style="text-align:center;padding:26px">暂无持有金币的会员</td></tr>
            </tbody>
          </table>
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
          <table class="tb2">
            <thead><tr><th>会员</th><th>会员号</th><th>可用积分</th><th>冻结中</th><th>本月获得</th><th>累计已提</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in data.rows" :key="r.uid">
                <td><b>{{ r.nick }}</b></td><td class="tiny">{{ r.no }}</td>
                <td><b style="color:#185FA5">{{ fmt(r.av) }}</b></td>
                <td>{{ r.fz ? fmt(r.fz) : "—" }}</td>
                <td class="tiny">{{ fmt(r.mg) }}</td><td class="tiny">{{ fmt(r.wd) }}</td>
                <td><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="7" class="tiny" style="text-align:center;padding:26px">暂无持有积分的会员</td></tr>
            </tbody>
          </table>
        </div>
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
          <table class="tb2">
            <thead><tr><th>卡券名称</th><th>类别</th><th>未核销</th><th>3 天内到期</th></tr></thead>
            <tbody>
              <tr v-for="t in data.byTpl" :key="t.name">
                <td><b>{{ t.name }}</b></td><td class="tiny">{{ catLabel(t.cat) }}</td>
                <td><b>{{ t.n }} 张</b></td>
                <td><b v-if="t.soon" style="color:#A32D2D">{{ t.soon }}</b><span v-else class="tiny">0</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <table class="tb2">
            <thead><tr><th>卡号</th><th>卡券名称</th><th>持有会员</th><th>来源</th><th>剩余有效期</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in data.rows" :key="r.id" :style="r.daysLeft <= 3 ? 'background:#FDF0F0' : ''">
                <td class="tiny">{{ r.no }}</td><td><b>{{ r.tplName }}</b></td>
                <td>{{ r.nick }} {{ r.tail }}</td><td class="tiny">{{ r.srcDesc || r.src || "—" }}</td>
                <td><b v-if="r.daysLeft <= 3" style="color:#A32D2D">{{ r.daysLeft }} 天</b><span v-else>{{ r.daysLeft }} 天</span></td>
                <td><button class="btn sm ghost" @click="member(r.uid)">会员详情</button></td>
              </tr>
              <tr v-if="!data.rows.length"><td colspan="6" class="tiny" style="text-align:center;padding:26px">暂无未核销卡券</td></tr>
            </tbody>
          </table>
        </div>
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
        <div class="card">
          <div class="st">近 10 日积分发放趋势 <em>红柱为今日</em></div>
          <div class="trend-bars">
            <div v-for="t in [...(data.trend || [])].reverse()" :key="t.d" class="trend-col">
              <div class="trend-bar" :style="{ height: trendHeight(t, data.trend || []) + 'px', background: t.today ? '#E24B4A' : '#B5D4F4' }" />
              <span class="tiny">{{ String(t.d).slice(5) }}</span>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="st">今日按录入人归集</div>
          <table class="tb2">
            <thead><tr><th>录入店员</th><th>录入局数</th><th>发出积分</th><th>发出碎片</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="o in data.byOp" :key="o.opUid">
                <td><b>{{ o.op || "未指定" }}</b></td><td>{{ o.n }}</td>
                <td><b style="color:#BA7517">{{ fmt(o.pts) }}</b></td><td style="color:#534AB7">{{ fmt(o.sh) }}</td>
                <td><button v-if="o.opUid" class="btn sm ghost" @click="jobs(o.opUid)">查看作业流水</button><span v-else class="tiny">—</span></td>
              </tr>
              <tr v-if="!data.byOp?.length"><td colspan="5" class="tiny" style="text-align:center;padding:22px">今日暂无对局录入</td></tr>
            </tbody>
          </table>
        </div>
        <div class="card" style="padding:0;overflow:auto">
          <div class="st" style="padding:14px 14px 0">今日对局逐条 <em>{{ data.games?.length || 0 }} 局</em></div>
          <table class="tb2">
            <thead><tr><th>时间</th><th>项目</th><th>桌台</th><th>玩家与得分</th><th>积分</th><th>录入人</th></tr></thead>
            <tbody>
              <tr v-for="g in data.games" :key="g.id">
                <td class="tiny">{{ String(g.time || "").slice(11) || "—" }}</td>
                <td><b>{{ g.pname }}</b></td><td class="tiny">{{ g.table || "—" }}</td>
                <td class="tiny">{{ gamePlayers(g) }}</td>
                <td><b style="color:#BA7517">{{ fmt(gamePts(g)) }}</b></td>
                <td class="tiny">{{ g.op || "—" }}</td>
              </tr>
              <tr v-if="!data.games?.length"><td colspan="6" class="tiny" style="text-align:center;padding:22px">今日暂无对局录入</td></tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 110px;
  padding: 0 4px 4px;
  border-bottom: 1px solid rgba(28, 27, 25, 0.12);
}
.trend-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-width: 0;
}
.trend-bar {
  width: 100%;
  max-width: 34px;
  border-radius: 3px 3px 0 0;
}
</style>

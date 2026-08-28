<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, savedUser } from "../api";

type Col = { k: string; h: string; kind?: string };

const titles: Record<string, string> = {
  dailyBiz: "营业一览",
  reports: "报表与对账",
  settle: "榜单与结算",
  rankHistory: "榜单历史记录",
  settlecfg: "榜单与奖励规则",
  push: "消息推送",
  shopinfo: "门店信息",
  cardTpls: "卡券配置",
  cards: "已发卡券",
  tiers: "充值档位配置",
  champs: "冠军记录",
  deactivations: "注销申请处理",
  teams: "战队管理",
  content: "店铺相册与玩法",
  config: "风控参数",
  staff: "员工与权限",
  logs: "操作日志",
  coinAdjusts: "金币调账审批",
  cats: "商品分类",
  projects: "对局项目配置",
  settleLogs: "结算记录",
  signRules: "签到奖励配置",
  verifyLogs: "核销记录",
};

const COLS: Record<string, Col[]> = {
  dailyBiz: [
    { k: "d", h: "日期" }, { k: "coin", h: "金币消费" }, { k: "offline", h: "现场收款" },
    { k: "recharge", h: "充值额" }, { k: "orders", h: "订单数" }, { k: "guests", h: "到店人次" },
  ],
  deactivations: [
    { k: "no", h: "申请单号" },
    { k: "uid", h: "会员", kind: "user" },
    { k: "status", h: "状态", kind: "deact" },
    { k: "created", h: "提交时间" },
    { k: "reason", h: "原因" },
  ],
  coinAdjusts: [
    { k: "uid", h: "会员", kind: "user" },
    { k: "delta", h: "调整额", kind: "delta" },
    { k: "type", h: "类型", kind: "adjType" },
    { k: "reason", h: "原因" },
    { k: "by", h: "申请人", kind: "user" },
    { k: "at", h: "时间" },
    { k: "status", h: "状态", kind: "adj" },
  ],
  logs: [
    { k: "t", h: "时间" },
    { k: "op", h: "操作人" },
    { k: "role", h: "角色" },
    { k: "action", h: "动作" },
    { k: "detail", h: "详情" },
  ],
  cardTpls: [
    { k: "name", h: "名称" },
    { k: "cat", h: "分类", kind: "cardCat" },
    { k: "cost", h: "积分价", kind: "cost" },
    { k: "days", h: "有效期", kind: "days" },
    { k: "exch", h: "兑换页", kind: "exch" },
    { k: "perLimit", h: "每人上限", kind: "limit" },
    { k: "stock", h: "库存", kind: "limit" },
  ],
  cards: [
    { k: "no", h: "卡号" },
    { k: "uid", h: "会员", kind: "user" },
    { k: "tpl", h: "卡券", kind: "tpl" },
    { k: "srcDesc", h: "来源" },
    { k: "daysLeft", h: "剩余天数", kind: "days" },
    { k: "status", h: "状态", kind: "card" },
  ],
  tiers: [
    { k: "amount", h: "充值金额", kind: "yen" },
    { k: "bonus", h: "赠送金币" },
    { k: "rec", h: "推荐档", kind: "bool" },
  ],
  champs: [
    { k: "uid", h: "会员", kind: "user" },
    { k: "event", h: "赛事" },
    { k: "date", h: "日期" },
    { k: "n", h: "参赛人数" },
    { k: "teamName", h: "获奖时战队" },
    { k: "op", h: "录入人" },
  ],
  teams: [{ k: "name", h: "战队名称" }],
  staff: [
    { k: "nick", h: "姓名" },
    { k: "role", h: "角色", kind: "role" },
    { k: "no", h: "工号" },
    { k: "phone", h: "手机" },
  ],
  cats: [
    { k: "name", h: "分类名称" },
    { k: "sort", h: "排序" },
    { k: "disabled", h: "状态", kind: "disabled" },
  ],
  projects: [
    { k: "name", h: "项目" },
    { k: "min", h: "最少人数" },
    { k: "max", h: "最多人数" },
    { k: "shard", h: "默认碎片" },
    { k: "disabled", h: "状态", kind: "disabled" },
  ],
  settleLogs: [
    { k: "week", h: "周期" },
    { k: "nick", h: "会员" },
    { k: "target", h: "对象" },
    { k: "desc", h: "奖励" },
    { k: "sh", h: "碎片" },
    { k: "status", h: "状态", kind: "settle" },
  ],
  signRules: [
    { k: "days", h: "连续天数" },
    { k: "pts", h: "奖励积分" },
    { k: "enabled", h: "启用", kind: "bool" },
  ],
  verifyLogs: [
    { k: "at", h: "时间" },
    { k: "tplName", h: "卡券" },
    { k: "cardNo", h: "卡号" },
    { k: "uid", h: "会员", kind: "user" },
    { k: "opUid", h: "核销人", kind: "user" },
  ],
};

const CONFIG_LABELS: Record<string, string> = {
  pointLimit: "积分单笔上限开关",
  pointVal: "积分单笔上限",
  shardLimit: "碎片单笔上限开关",
  shardVal: "碎片单笔上限",
  signPoints: "每日签到积分",
  singleLimit: "单笔消费上限",
  offlineTimeout: "到店付超时（分钟）",
  rechargeTimeout: "充值待付超时（分钟）",
  verifyTtl: "核销码有效期（分钟）",
  alertRatio: "积分录入异常倍数",
};
const CONTENT_LABELS: Record<string, string> = {
  gallery: "店铺相册",
  howToPlay: "店铺玩法",
  shopInfo: "门店信息",
  faq: "常见问题",
};

const DEACT: Record<string, string> = { PENDING: "待处理", REJECTED: "已驳回", DONE: "已注销" };
const ADJ: Record<string, string> = { PENDING: "待审批", APPROVED: "已通过", REJECTED: "已驳回" };
const CARD: Record<string, string> = { UNUSED: "未使用", USED: "已核销", LOCKED: "核销中", VOID: "已作废", EXPIRED: "已过期" };
const SETTLE: Record<string, string> = { GRANTED: "已发放", SKIPPED: "跳过", REVOKED: "已撤回" };
const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板", CUSTOMER: "会员" };
const CAT: Record<string, string> = { GAME: "游戏卡", FOOD: "酒水小食卡", OTHER: "其他卡" };

const route = useRoute();
const rows = ref<any>(null);
const members = ref<any[]>([]);
const tpls = ref<any[]>([]);
const msg = ref("");
const coll = () => String(route.params.coll || route.path.replace("/", ""));
const sourceColl = () => ({
  reports: "dailyBiz",
  settle: "settleLogs",
  rankHistory: "settleLogs",
  settlecfg: "cfg",
  shopinfo: "content",
}[coll()] || coll());
const title = computed(() => titles[coll()] || coll());
const FALLBACK_H: Record<string, string> = {
  id: "编号", no: "单号", uid: "会员", status: "状态", created: "创建时间", reason: "原因",
  name: "名称", nick: "昵称", phone: "手机", role: "角色", at: "时间", op: "操作人",
  amount: "金额", bonus: "赠送", pts: "积分", event: "赛事", date: "日期",
};
const cols = computed(() => {
  const defined = COLS[coll()] || COLS[sourceColl()];
  if (defined) return defined;
  const first = Array.isArray(rows.value) && rows.value[0];
  if (!first) return [];
  return Object.keys(first)
    .filter((k) => !["items", "snap", "players", "specs", "combo"].includes(k))
    .slice(0, 8)
    .map((k) => ({ k, h: FALLBACK_H[k] || k, kind: k === "uid" ? "user" : k === "status" ? "card" : undefined }));
});
const isObj = computed(() => rows.value && !Array.isArray(rows.value));

async function load() {
  const c = coll();
  rows.value = await api("/admin/" + sourceColl());
  msg.value = "";
  if (!members.value.length) {
    try {
      members.value = await api("/admin/members");
    } catch (e) {}
  }
  if (c === "cards" && !tpls.value.length) {
    try {
      tpls.value = await api("/admin/cardTpls");
    } catch (e) {}
  }
}
onMounted(load);
watch(() => route.fullPath, load);

function nick(uid: number) {
  const u = members.value.find((x) => x.id === uid);
  return u ? u.nick : uid ? String(uid) : "—";
}
function cell(row: any, col: Col) {
  const v = row[col.k];
  switch (col.kind) {
    case "user":
      return nick(Number(v));
    case "deact":
      return DEACT[v] || v;
    case "adj":
      return ADJ[v] || v;
    case "card":
      return CARD[v] || v;
    case "settle":
      return SETTLE[v] || v;
    case "role":
      return ROLE[v] || v;
    case "cardCat":
      return CAT[v] || v;
    case "adjType":
      return v === "PRINCIPAL" ? "本金" : v === "BONUS" ? "赠送" : v || "—";
    case "yen":
      return "¥" + v;
    case "delta":
      return (Number(v) > 0 ? "+" : "") + v;
    case "days":
      return v == null ? "—" : v + " 天";
    case "cost":
      return v ? v : "仅奖励发放";
    case "limit":
      return v == null || v < 0 ? "不限" : v;
    case "exch":
      return row.cost > 0 && row.exch !== false ? "是" : "否";
    case "bool":
      return v ? "是" : "否";
    case "disabled":
      return v ? "已停用" : "启用中";
    case "tpl": {
      const t = tpls.value.find((x) => x.id === v);
      return t ? t.name : "卡券 #" + v;
    }
    default:
      if (v == null || v === "") return "—";
      if (typeof v === "object") return "—";
      return String(v);
  }
}

const kv = computed(() => {
  if (!isObj.value) return [];
  const c = coll();
  const obj = rows.value as Record<string, unknown>;
  const labels = c === "config" ? CONFIG_LABELS : c === "content" ? CONTENT_LABELS : {};
  return Object.keys(obj).map((k) => ({
    k,
    h: labels[k] || k,
    v: typeof obj[k] === "object" ? JSON.stringify(obj[k], null, 2) : String(obj[k]),
  }));
});

async function approve(id: number, action: string) {
  try {
    await api(`/admin/coin-adjust/${id}/${action}`, { method: "POST" });
    await load();
  } catch (e: any) {
    msg.value = e.message;
  }
}
async function deact(id: number, action: string) {
  try {
    await api(`/admin/deactivations/${id}/${action}`, { method: "POST", body: { reason: action === "reject" ? "驳回" : "核对通过" } });
    await load();
  } catch (e: any) {
    msg.value = e.message;
  }
}

function hasOp(r: any) {
  const c = coll();
  if (c === "coinAdjusts") return r.status === "PENDING" && savedUser()?.role === "BOSS";
  if (c === "deactivations") return r.status === "PENDING";
  return false;
}
</script>

<template>
  <div>
    <div class="hdr">{{ title }}</div>
    <p class="tiny" v-if="msg">{{ msg }}</p>

    <div class="card" v-if="isObj">
      <table class="tb2">
        <thead>
          <tr><th style="width:28%">配置项</th><th>内容</th></tr>
        </thead>
        <tbody>
        <tr v-for="it in kv" :key="it.k">
          <td>{{ it.h }}</td>
          <td style="white-space:pre-wrap;font-size:12px">{{ it.v }}</td>
        </tr>
        </tbody>
      </table>
    </div>

    <div class="card" style="padding:0;overflow-x:auto" v-else-if="Array.isArray(rows) && rows.length">
      <table class="tb2">
        <thead>
        <tr>
          <th v-for="col in cols" :key="col.k">{{ col.h }}</th>
          <th v-if="coll()==='coinAdjusts' || coll()==='deactivations'">操作</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="(r,i) in rows.slice(0,80)" :key="r.id || i">
          <td v-for="col in cols" :key="col.k">{{ cell(r, col) }}</td>
          <td v-if="coll()==='coinAdjusts' && hasOp(r)">
            <button class="btn gold" @click="approve(r.id,'approve')">通过</button>
            <button class="btn ghost" @click="approve(r.id,'reject')">驳回</button>
          </td>
          <td v-else-if="coll()==='deactivations' && hasOp(r)">
            <button class="btn gold" @click="deact(r.id,'exec')">退本金并注销</button>
            <button class="btn ghost" @click="deact(r.id,'reject')">驳回</button>
          </td>
          <td v-else-if="coll()==='coinAdjusts' || coll()==='deactivations'">—</td>
        </tr>
        </tbody>
      </table>
    </div>
    <p class="tiny" v-else>暂无数据</p>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, savedUser } from "@/utils/api";

const WDST = {
  PENDING_CONFIRM: ["待确认", "gold"],
  GRANTED: ["已发放", "green"],
  REJECTED: ["已驳回", "red"],
  CANCELLED: ["已取消", "grey"],
  CLOSED_TIMEOUT: ["超时关闭", "red"],
};

const data = ref(null);
const pts = ref("");
const msg = ref("");

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const me = computed(() => savedUser());
const pw = computed(() => data.value?.pending);
const av = computed(() => data.value?.point?.av || 0);
const negative = computed(() => av.value < 0);
const history = computed(() =>
  (data.value?.history || []).filter((w) => w.status !== "PENDING_CONFIRM").slice(0, 5)
);

function stLabel(s) {
  return (WDST[s] || [s, "grey"])[0];
}

async function load() {
  data.value = await api("/points");
}
onShow(load);

function setAmt(v) {
  pts.value = String(v);
}

async function submit() {
  msg.value = "";
  const v = Math.floor(Number(pts.value || 0));
  if (!v || v <= 0) {
    msg.value = "请输入有效数量";
    return;
  }
  try {
    await api("/withdrawals", { method: "POST", body: { pts: v } });
    uni.showToast({ title: "提分单已生成", icon: "success" });
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}

async function cancel() {
  try {
    await api("/withdrawals/cancel", { method: "POST" });
    uni.showToast({ title: "已取消，积分已退回", icon: "success" });
    await load();
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="data">
    <template v-if="pw">
      <view class="card pend">
        <view class="between" style="margin-bottom:9px">
          <text class="pill pill-gold">待店员确认</text>
          <text class="tiny">{{ data.remain ? "剩 " + data.remain + " 自动关闭" : "可随时取消" }}</text>
        </view>
        <view class="pend-center">
          <view class="tiny gold-t">提取积分</view>
          <view class="pend-num">{{ fmt(pw.pts) }}</view>
          <view class="tiny" style="color:#e24b4a;margin-top:2px">该额度已从可用积分冻结，确认后正式发放</view>
        </view>
        <view class="pend-box">
          <view class="between row-line">
            <text class="tiny">单号</text>
            <text style="font-weight:600;font-size:15px;letter-spacing:1px">
              <text style="color:#e24b4a;font-size:18px">{{ pw.no }}</text>
            </text>
          </view>
          <view class="between row-line">
            <text class="tiny">会员</text>
            <text class="tiny">{{ me?.nick }} · {{ me?.no }}</text>
          </view>
          <view class="between row-line">
            <text class="tiny">提交时间</text>
            <text class="tiny">{{ pw.created }}</text>
          </view>
          <view class="between row-line">
            <text class="tiny">冻结后可用</text>
            <text style="font-weight:600" :style="negative ? 'color:#e24b4a' : ''">
              {{ negative ? "−" + fmt(-av) : fmt(av) }} 分
            </text>
          </view>
        </view>
      </view>
      <view class="card guide">
        <view style="font-weight:600;margin-bottom:6px">到吧台出示此单号</view>
        <view class="tiny guide-t">
          1. 向店员报单号后四位 <text style="font-weight:600">{{ pw.no.slice(-4) }}</text>
          <br />2. 店员在待办中核对数量
          <br />3. <text style="font-weight:600">店员确认后当面发放，冻结额度结清</text>
          <br />4. 若店员驳回，冻结积分原额退回可用
          <br />5. <text style="font-weight:600">超过 30 分钟未确认自动关闭</text>，冻结积分全额退回可用，不会没收
        </view>
      </view>
      <view class="row g2-btns">
        <button class="btn ghost block" @tap="cancel">取消此单</button>
        <button class="btn block" @tap="load">刷新状态</button>
      </view>
    </template>

    <template v-else>
      <view class="pt-card">
        <view class="tiny pt-label">可提取积分</view>
        <view class="pt-num" :class="{ neg: negative }">{{ negative ? "−" + fmt(-av) : fmt(av) }}</view>
        <view v-if="data.point.fz > 0" class="tiny" style="color:#ffe9b8;margin-top:4px">
          另有 {{ fmt(data.point.fz) }} 分冻结中
        </view>
      </view>

      <view class="st">提取数量</view>
      <view class="card">
        <view class="inp-box">
          <view class="tiny">提取数量</view>
          <view class="row" style="margin-top:3px">
            <input class="inp" type="number" v-model="pts" placeholder="0" />
            <text class="mut">分</text>
          </view>
        </view>
        <view class="row quick">
          <button class="btn ghost q" @tap="setAmt(1000)">{{ fmt(1000) }}</button>
          <button class="btn ghost q" @tap="setAmt(5000)">{{ fmt(5000) }}</button>
          <button class="btn ghost q" @tap="setAmt(10000)">{{ fmt(10000) }}</button>
          <button class="btn ghost q" @tap="setAmt(Math.max(0, av))">全部</button>
        </view>
        <button class="btn block gold" :disabled="negative || av <= 0" @tap="submit">生成提分单</button>
        <view v-if="negative" class="tiny err-t">当前积分为负（待抵扣 {{ fmt(data.point.pd || -av) }} 分），暂不可提分</view>
        <view v-else-if="av <= 0" class="tiny err-t">可用积分为 0，暂不可提分</view>
      </view>

      <view v-if="history.length">
        <view class="st">近期提分记录</view>
        <view class="card">
          <view class="li" v-for="w in history" :key="w.id">
            <view class="gr">
              <view style="font-weight:600">{{ fmt(w.pts) }} 分</view>
              <view class="tiny">{{ w.no }} · {{ w.created }}</view>
            </view>
            <text class="pill">{{ stLabel(w.status) }}</text>
          </view>
        </view>
      </view>

      <view class="note">
        提交即冻结：生成提分单时积分立即从可用扣除转入冻结，店员确认后正式发放。同时只能有 1 张待确认单。
        <text style="font-weight:600">超过 30 分钟未确认自动关闭</text>；取消、驳回与超时关闭三种情形
        <text style="font-weight:600">一律把冻结积分全额退回可用，不会没收</text>。
      </view>
    </template>

    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

<style scoped>
.pt-card {
  background: linear-gradient(135deg, #185FA5, #2E7CC4);
  border: none;
  color: #fff;
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
}
.pt-label { color: rgba(255, 255, 255, 0.8); }
.pt-num { font-size: 32px; font-weight: 700; margin-top: 2px; }
.pt-num.neg { color: #ffc9c9; }
.st { font-size: 13px; font-weight: 600; margin: 4px 0 8px; }
.pend { border: 2px solid #ba7517; background: #fdf4e3; }
.pill-gold { background: #ba7517; color: #fff; }
.pend-center { text-align: center; padding: 6px 0 10px; }
.gold-t { color: #ba7517; }
.pend-num { font-size: 33px; font-weight: 600; color: #633806; }
.pend-box { background: #fff; border-radius: 9px; padding: 11px 12px; }
.row-line { padding: 3px 0; }
.guide { background: #f5f4f0; }
.guide-t { line-height: 1.75; }
.g2-btns { gap: 8px; }
.g2-btns .btn { flex: 1; }
.inp-box {
  border: 1px solid rgba(28, 27, 25, 0.18);
  border-radius: 9px;
  padding: 12px 13px;
  margin-bottom: 9px;
}
.inp { flex: 1; font-size: 20px; font-weight: 600; border: none; }
.mut { color: #9c9a93; margin-left: auto; }
.quick { gap: 6px; margin-bottom: 9px; flex-wrap: wrap; }
.q { flex: 1; font-size: 12px; padding: 8px 2px; min-width: calc(25% - 6px); }
.err-t { color: #e24b4a; margin-top: 7px; }
</style>

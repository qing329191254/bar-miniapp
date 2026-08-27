<script setup>
import { computed, onMounted, ref } from "vue";
import { api, clearSession, go, relaunch } from "@/utils/api";

const me = ref(null);
const champs = ref({ list: [], total: 0, month: 0 });
const team = ref(null);
const reason = ref("");
const msg = ref("");

onMounted(async () => {
  me.value = await api("/me");
  try {
    champs.value = await api("/champions");
  } catch (e) {}
  if (me.value?.user?.teamId) {
    try {
      team.value = await api("/teams/" + me.value.user.teamId);
    } catch (e) {}
  }
});

function fmt(n) {
  const x = Number(n) || 0;
  return x.toLocaleString("en-US");
}
function logout() {
  clearSession();
  relaunch("/pages/login/login");
}
function gender(g) {
  return g === 1 ? "男" : g === 2 ? "女" : "未知";
}
const pending = computed(() => me.value?.user?.deact === "DEACTIVATE_PENDING");
const lastChamp = computed(() => {
  const d = champs.value.list?.[0]?.date;
  return d ? String(d).slice(5) : "—";
});

async function deact() {
  try {
    await api("/deactivate", { method: "POST", body: { reason: reason.value } });
    msg.value = "注销申请已提交，请到店由店长核对资产结清";
    me.value = await api("/me");
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="me">
    <view class="profile-hd">
      <view class="row">
        <view class="ph-lg">{{ me.user.av }}</view>
        <view style="margin-left:12px;flex:1">
          <view style="font-size:17px;font-weight:600;letter-spacing:.5px">{{ me.user.nick }}</view>
          <view class="tiny" style="color:rgba(255,255,255,.72);margin-top:2px">{{ me.user.phone }} · {{ gender(me.user.gender) }}</view>
          <view class="row" style="margin-top:6px">
            <text class="pill-w">会员 {{ me.user.no }}</text>
            <text class="pill-w" v-if="me.user.teamName" style="color:#CECBF6">{{ me.user.teamName }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="asset-card">
      <view class="asset-grid">
        <view class="asset" @tap="go('/pages/c/recharge')">
          <view class="ab gold">{{ fmt(me.user.coin.total) }}</view>
          <text>金币</text>
        </view>
        <view class="asset" @tap="go('/pages/c/points')">
          <view class="ab" :style="{ color: me.user.point.av < 0 ? '#A32D2D' : '#185FA5' }">{{ fmt(me.user.point.av) }}</view>
          <text>积分</text>
        </view>
        <view class="asset" @tap="go('/pages/c/cards')">
          <view class="ab" style="color:#534AB7">{{ me.usableCards }} 张</view>
          <text>卡包</text>
        </view>
        <view class="asset" @tap="go('/pages/c/shard')">
          <view class="ab" style="color:#3B6D11">{{ fmt(me.user.shard.w) }}</view>
          <text>碎片</text>
        </view>
      </view>
    </view>

    <view class="honor-grid">
      <view class="honor g">
        <view>我的冠军</view>
        <view class="hv">{{ champs.total }}</view>
        <view class="hl">累计夺冠 · 本月 {{ champs.month }} · 最近 {{ lastChamp }}</view>
      </view>
      <view class="honor gn">
        <view>{{ me.user.teamName || "（暂无战队）" }}</view>
        <view class="hv">{{ team ? team.champs + " 冠" : "—" }}</view>
        <view class="hl">{{ team ? (team.members?.length || 0) + " 名成员" : "可联系店员加入" }}</view>
      </view>
    </view>

    <view class="card">
      <view class="h2">我的订单</view>
      <view class="g3">
        <button class="btn ghost" @tap="go('/pages/c/orders')">金币订单</button>
        <button class="btn ghost" @tap="go('/pages/c/cards')">卡包订单</button>
        <button class="btn ghost" @tap="go('/pages/c/points')">积分订单</button>
      </view>
    </view>

    <view class="card">
      <view class="h2">帮助与联系</view>
      <view class="li" @tap="go('/pages/c/content?type=SHOP_INFO')">
        <view class="av">店</view>
        <view class="gr"><view style="font-weight:500">联系店员</view><view class="tiny">{{ me.shop?.tel ? "地址、电话与营业时间" : "商家尚未配置门店信息" }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="go('/pages/c/content?type=FAQ')">
        <view class="av">问</view>
        <view class="gr"><view style="font-weight:500">常见问题</view><view class="tiny">金币、积分与卡券规则</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="go('/pages/c/content?type=TERMS')">
        <view class="av">议</view>
        <view class="gr"><view style="font-weight:500">用户协议</view><view class="tiny">当前生效 v{{ me.agreements?.terms?.ver }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="go('/pages/c/content?type=PRIVACY')">
        <view class="av">隐</view>
        <view class="gr"><view style="font-weight:500">隐私政策</view><view class="tiny">信息收集与使用说明</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" style="border-bottom:none">
        <view class="av" style="background:#FCEBEB;color:#A32D2D">注</view>
        <view class="gr">
          <view style="font-weight:500" :style="{ color: pending ? '#BA7517' : '#A32D2D' }">注销账号</view>
          <view class="tiny">{{ pending ? "申请已提交 · 待店长核对资产结清" : "清空资产并注销会员，操作不可恢复" }}</view>
        </view>
      </view>
      <view v-if="!pending" style="margin-top:8px">
        <input class="field" v-model="reason" placeholder="注销原因" />
        <button class="btn danger block" @tap="deact">提交注销申请</button>
      </view>
      <view class="tiny" style="margin-top:7px">协议为常驻入口，可随时查看当前生效版本。</view>
    </view>

    <view class="err" v-if="msg">{{ msg }}</view>
    <button class="btn ghost block" @tap="logout">切换账号</button>
    <tab-bar current="mine" />
  </view>
</template>

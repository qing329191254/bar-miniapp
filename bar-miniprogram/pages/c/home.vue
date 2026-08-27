<script setup>
import { computed, onMounted, ref } from "vue";
import { api, go, media } from "@/utils/api";

const data = ref(null);
const bannerIdx = ref(0);
const msg = ref("");
const grads = [
  "linear-gradient(120deg,#231A0C 0%,#4A3B1E 48%,#8A6A2F 100%)",
  "linear-gradient(120deg,#141B33 0%,#2A3E6B 55%,#4E6BB8 100%)",
  "linear-gradient(120deg,#3A2310 0%,#7A4A1D 55%,#C07A2B 100%)",
  "linear-gradient(120deg,#1B2A24 0%,#2E5347 55%,#4E8A75 100%)",
];

onMounted(async () => {
  data.value = await api("/home");
});

const gallery = computed(() => {
  const g = data.value?.gallery;
  const items = Array.isArray(g) ? g : g?.items || [];
  return items.map((it, i) => ({
    t: it.name || "店铺相册",
    s: it.desc || "玩咖桌游酒吧",
    g: grads[i % grads.length],
    url: it.url ? media(it.url) : "",
  }));
});
const play = computed(() => {
  const h = data.value?.howToPlay;
  if (!h) return { title: "店铺玩法", sub: "桌游规则与场地" };
  if (Array.isArray(h)) return { title: "店铺玩法", sub: h[0] || "桌游规则与场地" };
  return { title: h.title || "店铺玩法", sub: h.sub || "桌游规则与场地" };
});

async function sign() {
  msg.value = "";
  try {
    const r = await api("/signin", { method: "POST" });
    msg.value = `签到 +${r.points} 分` + (r.extraPts ? `，连签奖励 +${r.extraPts}` : "");
    data.value = await api("/home");
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view
      class="home-b"
      :class="{ 'has-img': !!gallery[bannerIdx].url }"
      v-if="gallery.length"
      :style="gallery[bannerIdx].url
        ? { backgroundImage: 'url(' + gallery[bannerIdx].url + ')' }
        : { background: gallery[bannerIdx].g }"
      @tap="bannerIdx = (bannerIdx + 1) % gallery.length"
    >
      <view class="home-b-in">
        <view class="home-bt">{{ gallery[bannerIdx].t }}</view>
        <view class="home-bs">{{ gallery[bannerIdx].s }}</view>
      </view>
      <view class="home-b-page">{{ bannerIdx + 1 }} / {{ gallery.length }}</view>
    </view>
    <view class="home-b empty-b" v-else>
      <view style="text-align:center">
        <view style="font-size:13px;color:#6B6A65">商家尚未上传相册</view>
        <view class="tiny">Web 端「店铺相册」上传后此处即时展示</view>
      </view>
    </view>

    <view class="home-kg">
      <view class="kg-i" @tap="go('/pages/c/order')">
        <view class="ic" style="background:linear-gradient(135deg,#3EAF8E,#9FE1CB)">点</view>
        <text>点单</text>
      </view>
      <view class="kg-i" @tap="go('/pages/c/cards')">
        <view class="ic" style="background:linear-gradient(135deg,#4E8ED9,#B5D4F4)">卡</view>
        <text>用卡</text>
      </view>
      <view class="kg-i" @tap="go('/pages/c/points')">
        <view class="ic" style="background:linear-gradient(135deg,#D96A96,#F4C0D1)">分</view>
        <text>积分</text>
      </view>
      <view class="kg-i" @tap="sign">
        <view class="ic" style="background:linear-gradient(135deg,#7FA94F,#C0DD97)">签</view>
        <text>{{ data.signedToday ? "已签" : "签到" }}</text>
      </view>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>

    <view class="home-op" @tap="go('/pages/c/content?type=HOW_TO_PLAY')">
      <view class="home-ic" style="background:linear-gradient(135deg,#8F87E0,#CECBF6)">玩</view>
      <view class="home-txt">
        <view class="ht">{{ play.title }}</view>
        <view class="hs">{{ play.sub }}</view>
      </view>
      <text class="home-arr">›</text>
    </view>
    <view class="home-op" @tap="go('/pages/c/recharge')">
      <view class="home-ic" style="background:linear-gradient(135deg,#E89A3C,#FAC775)">充</view>
      <view class="home-txt">
        <view class="ht">充值有奖</view>
        <view class="hs">充多送多</view>
      </view>
      <text class="home-arr">›</text>
    </view>
    <view class="note">联动演示：到「商家移动端」确认充值 / 接单 / 录对局，回到本页即可看到资产与订单变化。</view>
    <tab-bar current="home" />
  </view>
</template>

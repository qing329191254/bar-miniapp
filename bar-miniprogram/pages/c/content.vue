<script setup>
import { computed, onMounted, ref } from "vue";
import { api, media } from "@/utils/api";

const type = ref("SHOP_INFO");
const data = ref(null);

onMounted(async () => {
  const pages = getCurrentPages();
  const q = pages[pages.length - 1]?.options || {};
  type.value = q.type || "SHOP_INFO";
  data.value = await api("/content");
  const titles = {
    HOW_TO_PLAY: "店铺玩法",
    SHOP_INFO: "门店信息",
    FAQ: "常见问题",
    TERMS: "用户协议",
    PRIVACY: "隐私政策",
    GALLERY: "店铺相册",
  };
  uni.setNavigationBarTitle({ title: titles[type.value] || "店铺信息" });
});

const shop = computed(() => data.value?.shopInfo || {});
const play = computed(() => data.value?.howToPlay || {});
const faq = computed(() => data.value?.faq || {});
const gallery = computed(() => {
  const g = data.value?.gallery;
  return Array.isArray(g) ? g : g?.items || [];
});
function isImg(v) {
  return v && (/^\/uploads\//.test(v) || /^https?:/.test(v));
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view v-if="type === 'SHOP_INFO'" class="card">
      <view class="h2">{{ shop.name }}</view>
      <view class="li"><view class="gr"><view class="tiny">地址</view><view>{{ shop.addr }}</view></view></view>
      <view class="li"><view class="gr"><view class="tiny">电话</view><view>{{ shop.tel }}</view></view></view>
      <view class="li"><view class="gr"><view class="tiny">营业时间</view><view>{{ shop.hours }}</view></view></view>
      <view class="tiny" style="margin-top:8px">{{ shop.notice }}</view>
    </view>
    <view v-else-if="type === 'HOW_TO_PLAY'" class="card">
      <view class="h2">{{ play.title || "店铺玩法" }}</view>
      <view class="tiny" style="margin-bottom:8px">{{ play.sub }}</view>
      <view v-for="(it, i) in (play.items || [])" :key="i" class="li">{{ it }}</view>
      <image v-if="isImg(play.pic)" class="play-pic" :src="media(play.pic)" mode="widthFix" />
    </view>
    <view v-else-if="type === 'GALLERY'">
      <view v-if="!gallery.length" class="card" style="text-align:center">商家尚未上传相册</view>
      <view v-else class="g2">
        <view v-for="(it, i) in gallery" :key="it.id || i" class="card" style="padding:0;overflow:hidden">
          <image v-if="it.url" class="gal" :src="media(it.url)" mode="aspectFill" />
          <view v-else class="gal ph">{{ it.name }}</view>
          <view style="padding:8px 10px">
            <view style="font-weight:600;font-size:13px">{{ it.name }}</view>
            <view class="tiny">{{ it.desc }}</view>
          </view>
        </view>
      </view>
    </view>
    <view v-else-if="type === 'FAQ'">
      <view class="card" v-for="(it, i) in (faq.items || [])" :key="i">
        <view style="font-weight:600">{{ it.q }}</view>
        <view class="tiny" style="margin-top:6px;line-height:1.7">{{ it.a }}</view>
      </view>
    </view>
    <view v-else class="card">
      <view class="h2">{{ type === "PRIVACY" ? "隐私政策" : "用户协议" }}</view>
      <view class="tiny" style="line-height:1.8">本店会员服务协议与隐私政策可随时查阅。正式版将展示当前生效全文与你的同意记录。金币本金未消费可到店退还；赠送金币、积分、卡券不折现。</view>
    </view>
  </view>
</template>

<style scoped>
.gal {
  width: 100%;
  height: 100px;
  display: block;
  background: #EDEBE4;
}
.gal.ph {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #9C9A93;
}
.play-pic {
  width: 100%;
  margin-top: 10px;
  border-radius: 8px;
}
</style>

<script setup>
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { api, media } from "@/utils/api";

const type = ref("SHOP_INFO");
const data = ref(null);
const agreements = ref(null);
const err = ref("");

const titles = {
  HOW_TO_PLAY: "店铺玩法",
  SHOP_INFO: "门店信息",
  FAQ: "常见问题",
  TERMS: "用户协议",
  PRIVACY: "隐私政策",
  GALLERY: "店铺相册",
};

onLoad(async (q) => {
  type.value = (q && q.type) || "SHOP_INFO";
  uni.setNavigationBarTitle({ title: titles[type.value] || "店铺信息" });
  try {
    const needAgree = type.value === "TERMS" || type.value === "PRIVACY";
    const tasks = [api("/content")];
    if (needAgree) tasks.push(api("/agreements"));
    const results = await Promise.all(tasks);
    data.value = results[0];
    if (needAgree) agreements.value = results[1];
  } catch (e) {
    err.value = e.message || "加载失败";
  }
});

const shop = computed(() => data.value?.shopInfo || {});
const play = computed(() => {
  const h = data.value?.howToPlay;
  if (!h || Array.isArray(h)) {
    return {
      title: "店铺玩法",
      sub: "",
      items: Array.isArray(h) ? h : [],
      pic: "",
    };
  }
  return {
    title: String(h.title || "").trim() || "店铺玩法",
    sub: String(h.sub || "").trim(),
    items: (h.items || [])
      .map((x) => (typeof x === "string" ? x : x.title || x.name || x.desc || ""))
      .filter(Boolean),
    pic: h.pic || "",
  };
});
const faq = computed(() => {
  const f = data.value?.faq;
  if (f == null) return { title: "常见问题", sub: "", items: [] };
  if (Array.isArray(f)) return { title: "常见问题", sub: "", items: f };
  return {
    title: String(f.title || "").trim() || "常见问题",
    sub: String(f.sub || "").trim(),
    items: Array.isArray(f.items) ? f.items : [],
  };
});
const gallery = computed(() => {
  const g = data.value?.gallery;
  return Array.isArray(g) ? g : g?.items || [];
});
const legalDoc = computed(() => {
  const key = type.value === "PRIVACY" ? "privacy" : "terms";
  const doc = agreements.value?.[key] || {};
  return {
    title: doc.title || (type.value === "PRIVACY" ? "隐私政策" : "用户协议"),
    ver: doc.ver || 1,
    pub: doc.pub || "",
    text: String(doc.text || "").trim(),
  };
});
function isImg(v) {
  return v && (/^\/uploads\//.test(v) || /^https?:/.test(v));
}
function preview(i) {
  const urls = gallery.value.map((x) => x.url && media(x.url)).filter(Boolean);
  if (!urls.length) return;
  const current = gallery.value[i]?.url ? media(gallery.value[i].url) : urls[0];
  uni.previewImage({ urls, current });
}
</script>

<template>
  <view class="pbody" v-if="err">
    <view class="card">{{ err }}</view>
  </view>
  <view class="pbody" v-else-if="data || agreements">
    <view v-if="type === 'SHOP_INFO'" class="card">
      <view class="h2">{{ shop.name || "商家尚未配置门店名称" }}</view>
      <view class="li"><view class="gr"><view class="tiny">地址</view><view>{{ shop.addr || "未配置" }}</view></view></view>
      <view class="li"><view class="gr"><view class="tiny">电话</view><view>{{ shop.tel || "未配置" }}</view></view></view>
      <view class="li"><view class="gr"><view class="tiny">营业时间</view><view>{{ shop.hours || "未配置" }}</view></view></view>
      <view v-if="shop.notice" class="tiny" style="margin-top:8px">{{ shop.notice }}</view>
    </view>
    <view v-else-if="type === 'HOW_TO_PLAY'">
      <view class="card">
        <view class="h2">{{ play.title }}</view>
        <view v-if="play.sub" style="font-size:13px;font-weight:600;margin-bottom:8px">{{ play.sub }}</view>
        <view v-if="play.items.length" class="play-list">
          <view v-for="(it, i) in play.items" :key="i" class="play-line">· {{ it }}</view>
        </view>
        <view v-else class="tiny">商家尚未配置玩法说明</view>
      </view>
      <view v-if="isImg(play.pic)" class="card" style="padding:0;overflow:hidden">
        <image class="play-pic" :src="media(play.pic)" mode="widthFix" />
        <view class="tiny" style="padding:8px 12px">场地示意图</view>
      </view>
    </view>
    <view v-else-if="type === 'GALLERY'">
      <view v-if="!gallery.length" class="card" style="text-align:center">商家尚未上传相册</view>
      <view v-else class="g2">
        <view
          v-for="(it, i) in gallery"
          :key="it.id || i"
          class="card"
          style="padding:0;overflow:hidden"
          @tap="preview(i)"
        >
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
      <view v-if="!(faq.items || []).length" class="card tiny">暂无常见问题</view>
    </view>
    <view v-else class="card">
      <view class="h2">{{ legalDoc.title }}{{ legalDoc.ver ? ` v${legalDoc.ver}` : "" }}</view>
      <view v-if="legalDoc.pub" class="tiny" style="margin-top:4px">{{ legalDoc.pub }} 发布</view>
      <view v-if="legalDoc.text" class="tiny" style="margin-top:10px;line-height:1.8;white-space:pre-wrap">{{ legalDoc.text }}</view>
      <view v-else class="tiny" style="margin-top:10px">商家尚未配置正文</view>
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
.play-list { color: #6B6A65; font-size: 13px; line-height: 1.85; }
.play-line { margin-bottom: 2px; }
.play-pic {
  width: 100%;
  display: block;
}
</style>

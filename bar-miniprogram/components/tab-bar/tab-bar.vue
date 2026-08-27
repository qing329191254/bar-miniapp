<script setup>
import { onMounted } from "vue";
import { savedUser, hideWxHomeButton } from "@/utils/api";

const props = defineProps({ current: { type: String, default: "" } });
const user = savedUser();
const isStaff = user && user.role !== "CUSTOMER";
const tabs = isStaff
  ? [
      { key: "todo", url: "/pages/s/todo", label: "待办", icon: "todo" },
      { key: "game", url: "/pages/s/game", label: "录对局", icon: "game" },
      { key: "mine", url: "/pages/s/mine", label: "我的", icon: "mine" },
    ]
  : [
      { key: "home", url: "/pages/c/home", label: "首页", icon: "home" },
      { key: "rank", url: "/pages/c/rank", label: "榜单", icon: "rank" },
      { key: "mine", url: "/pages/c/mine", label: "我的", icon: "mine" },
    ];

function iconSrc(t) {
  const on = t.key === props.current;
  return `/static/tab/${t.icon}${on ? "-on" : ""}.png`;
}

function tap(t) {
  if (t.key === props.current) return;
  uni.redirectTo({ url: t.url });
}
function scan() {
  uni.navigateTo({ url: "/pages/s/scan" });
}

onMounted(() => {
  hideWxHomeButton();
});
</script>

<template>
  <view>
    <view v-if="isStaff && current !== 'scan'" class="fab" @tap="scan">扫码<br />核销</view>
    <view class="ptabs">
      <view
        v-for="t in tabs"
        :key="t.key"
        class="ptab"
        :class="{ on: current === t.key }"
        @tap="tap(t)"
      >
        <image class="ptab-i" :src="iconSrc(t)" mode="aspectFit" />
        {{ t.label }}
      </view>
    </view>
  </view>
</template>

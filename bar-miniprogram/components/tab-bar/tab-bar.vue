<script setup>
import { savedUser } from "@/utils/api";

const props = defineProps({ current: { type: String, default: "" } });
const user = savedUser();
const isStaff = user && user.role !== "CUSTOMER";
const tabs = isStaff
  ? [
      { key: "todo", url: "/pages/s/todo", label: "待办" },
      { key: "game", url: "/pages/s/game", label: "录对局" },
      { key: "mine", url: "/pages/s/mine", label: "我的" },
    ]
  : [
      { key: "home", url: "/pages/c/home", label: "首页" },
      { key: "rank", url: "/pages/c/rank", label: "榜单" },
      { key: "mine", url: "/pages/c/mine", label: "我的" },
    ];

function tap(t) {
  if (t.key === props.current) return;
  uni.redirectTo({ url: t.url });
}
function scan() {
  uni.navigateTo({ url: "/pages/s/scan" });
}
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
        <view class="ptab-i" />
        {{ t.label }}
      </view>
    </view>
  </view>
</template>

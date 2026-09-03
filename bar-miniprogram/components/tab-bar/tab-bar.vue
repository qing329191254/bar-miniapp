<script setup>
import { onMounted } from "vue";
import { isStaffPortal, hideWxHomeButton } from "@/utils/api";
import { iconSrc as svgIcon } from "@/utils/icons";
import { reminderState } from "@/utils/staff-reminder";

const scanSrc = svgIcon("scan");

const props = defineProps({ current: { type: String, default: "" } });
const isStaff = isStaffPortal();
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
    <view v-if="isStaff && current !== 'scan'" class="fab" @tap="scan">
      <image class="fab-ic" :src="scanSrc" mode="aspectFit" />
      <text class="fab-txt">核销</text>
    </view>
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
        <text v-if="t.key === 'todo' && reminderState.total" class="ptab-badge">{{ reminderState.total > 99 ? '99+' : reminderState.total }}</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.fab-ic {
  width: 22px;
  height: 22px;
  display: block;
}
.fab-txt {
  font-size: 10px;
  font-weight: 600;
  margin-top: 2px;
  line-height: 1;
}
.ptab{position:relative}
.ptab-badge{position:absolute;top:3px;left:calc(50% + 8px);min-width:16px;height:16px;padding:0 4px;border-radius:99px;background:#b93a34;color:#fff;font-size:9px;line-height:16px;text-align:center;font-weight:700;box-sizing:border-box}
</style>

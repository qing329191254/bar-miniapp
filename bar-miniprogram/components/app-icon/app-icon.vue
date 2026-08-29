<script setup>
import { computed } from "vue";
import { GRAD, iconSrc } from "@/utils/icons";

const props = defineProps({
  name: { type: String, required: true },
  tone: { type: String, default: "teal" },
  size: { type: String, default: "md" },
  shape: { type: String, default: "round" },
  plain: { type: Boolean, default: false },
});

const src = computed(() => iconSrc(props.name));
const bg = computed(() => GRAD[props.tone] || props.tone);
</script>

<template>
  <view
    v-if="!plain"
    class="app-icon"
    :class="['sz-' + size, 'sh-' + shape]"
    :style="{ background: bg }"
  >
    <image v-if="src" class="app-icon-img" :src="src" mode="aspectFit" />
  </view>
  <image v-else-if="src" class="app-icon-plain" :class="'sz-' + size" :src="src" mode="aspectFit" />
</template>

<style scoped>
.app-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 3px 10px rgba(28, 27, 25, 0.14);
}
.sh-round { border-radius: 50%; }
.sh-sq { border-radius: 12px; }
.sh-soft { border-radius: 10px; }
.sz-sm { width: 32px; height: 32px; }
.sz-md { width: 40px; height: 40px; }
.sz-lg { width: 46px; height: 46px; }
.sz-xl { width: 52px; height: 52px; }
.app-icon-img {
  width: 58%;
  height: 58%;
  display: block;
}
.app-icon-plain {
  display: block;
  flex-shrink: 0;
}
.app-icon-plain.sz-sm { width: 16px; height: 16px; }
.app-icon-plain.sz-md { width: 18px; height: 18px; }
</style>

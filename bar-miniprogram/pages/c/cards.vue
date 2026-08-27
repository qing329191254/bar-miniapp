<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "@/utils/api";

const list = ref([]);
const sel = ref([]);
const code = ref(null);
const msg = ref("");

onMounted(async () => {
  list.value = await api("/cards");
});

const unused = computed(() => list.value.filter((c) => c.status === "UNUSED"));
function selected(id) {
  return sel.value.includes(id);
}
function toggle(id) {
  sel.value = selected(id) ? sel.value.filter((x) => x !== id) : [...sel.value, id];
}

async function gen() {
  msg.value = "";
  try {
    code.value = await api("/cards/verify-code", { method: "POST", body: { cardIds: sel.value } });
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody">
    <view class="empty" v-if="!unused.length">暂无可用卡券</view>
    <view
      class="card"
      v-for="c in unused"
      :key="c.id"
      :style="selected(c.id) ? 'border-color:#BA7517;background:#FAEEDA' : ''"
      @tap="toggle(c.id)"
    >
      <view class="between">
        <view>
          <view style="font-weight:600">{{ c.tplInfo?.name }}</view>
          <view class="tiny">{{ c.no }} · 剩 {{ c.daysLeft }} 天</view>
        </view>
        <text class="pill">{{ c.src }}</text>
      </view>
    </view>
    <button class="btn block gold" :disabled="!sel.length" @tap="gen">生成核销码给店员扫</button>
    <view class="card" v-if="code" style="text-align:center;margin-top:12px">
      <view class="tiny">请向店员出示</view>
      <view style="font-size:22px;letter-spacing:2px;font-weight:700">{{ code.code }}</view>
      <view class="tiny">{{ code.remain }} 内有效</view>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

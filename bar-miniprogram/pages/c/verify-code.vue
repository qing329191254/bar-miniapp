<script setup>
import { computed, onUnmounted, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const data = ref(null);
const loading = ref(true);
const error = ref("");
const now = ref(Date.now());
let timer = null;

function maskCode(code = "") {
  return code.length > 10 ? `${code.slice(0, 6)}****${code.slice(-4)}` : code;
}
function formatRemain() {
  const ms = Math.max(0, Number(data.value?.expireAt || 0) - now.value);
  const total = Math.ceil(ms / 1000);
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${min} 分 ${String(sec).padStart(2, "0")} 秒`;
}
const expired = computed(() => data.value && Number(data.value.expireAt || 0) <= now.value);

function finderCell(x, y, left, top) {
  const dx = x - left;
  const dy = y - top;
  if (dx < 0 || dx > 6 || dy < 0 || dy > 6) return null;
  return dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4);
}
const qrCells = computed(() => {
  let seed = 0;
  for (const char of String(data.value?.code || "")) seed = (seed * 31 + char.charCodeAt(0)) >>> 0;
  const cells = [];
  for (let y = 0; y < 21; y += 1) {
    for (let x = 0; x < 21; x += 1) {
      const finder = finderCell(x, y, 0, 0) ?? finderCell(x, y, 14, 0) ?? finderCell(x, y, 0, 14);
      seed = (seed * 1103515245 + 12345) >>> 0;
      cells.push({ key: `${x}-${y}`, on: finder === null ? ((seed >>> 16) % 100 < 48) : finder });
    }
  }
  return cells;
});

async function load(code) {
  loading.value = true;
  error.value = "";
  try {
    data.value = await api(`/cards/verify-code/${encodeURIComponent(code)}`);
  } catch (e) {
    error.value = e.message || "核销码加载失败";
  } finally {
    loading.value = false;
  }
}
function backToCards() {
  uni.navigateBack({
    fail: () => uni.redirectTo({ url: "/pages/c/cards" }),
  });
}

onLoad((options) => {
  const code = options?.code;
  if (!code) {
    error.value = "核销码不存在";
    loading.value = false;
    return;
  }
  load(code);
  timer = setInterval(() => { now.value = Date.now(); }, 1000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <view class="verify-page">
    <view v-if="loading" class="tiny loading-text">正在加载核销码</view>
    <view v-else-if="error" class="state-card">
      <view class="state-title">核销码无法使用</view>
      <view class="tiny">{{ error }}</view>
      <button class="btn ghost" @tap="backToCards">返回卡包</button>
    </view>

    <template v-else>
      <view class="valid-line" :class="{ expired }">
        <text>有效期 </text><text class="remain">{{ expired ? "已过期" : formatRemain() }}</text><text> · 请出示给店员扫码</text>
      </view>
      <view class="qr-wrap">
        <view v-for="cell in qrCells" :key="cell.key" class="qr-cell" :class="{ on: cell.on }"></view>
      </view>
      <view class="masked-code">核销码 {{ maskCode(data.code) }}</view>

      <view class="card verify-card">
        <view class="verify-title">本次核销 {{ data.cards?.length || 0 }} 张</view>
        <view v-for="card in data.cards" :key="card?.id" class="card-row">
          <view class="card-name">{{ card?.tplInfo?.name || "卡券" }}</view>
          <view class="tiny">{{ card?.srcDesc || "" }} · {{ card?.expire || "有效期内" }}</view>
          <view v-for="(rule, ri) in card?.tplInfo?.ruleText || []" :key="ri" class="tiny rule-text">{{ rule }}</view>
        </view>
      </view>
      <button class="btn ghost return-btn" @tap="backToCards">返回卡包</button>
    </template>
  </view>
</template>

<style scoped>
.verify-page { min-height: 100vh; padding: 20px 15px 36px; box-sizing: border-box; text-align: center; }
.loading-text { padding-top: 40px; }
.valid-line { color: #9C9A93; font-size: 15px; margin: 0 0 12px; }
.valid-line.expired .remain { color: #A32D2D; }
.remain { color: #B92C2C; font-size: 21px; font-weight: 700; }
.qr-wrap { width: 150px; height: 150px; padding: 10px; margin: 0 auto; display: grid; grid-template-columns: repeat(21, 1fr); gap: 1px; background: #fff; border: 1px solid rgba(28,27,25,.14); border-radius: 12px; box-sizing: border-box; }
.qr-cell { background: transparent; }
.qr-cell.on { background: #1C1B19; }
.masked-code { margin: 12px 0 22px; color: #9C9A93; font-size: 15px; }
.verify-card { padding: 18px 14px; text-align: left; }
.verify-title { font-size: 19px; font-weight: 700; margin-bottom: 17px; }
.card-row + .card-row { border-top: 1px solid rgba(28,27,25,.1); margin-top: 14px; padding-top: 14px; }
.card-name { font-size: 16px; font-weight: 600; margin-bottom: 7px; }
.rule-text { color: #BA7517; margin-top: 4px; }
.return-btn { margin-top: 18px; }
.state-card { margin-top: 48px; padding: 28px 18px; background: #fff; border: 1px solid rgba(28,27,25,.12); border-radius: 18px; }
.state-title { font-size: 19px; font-weight: 700; margin-bottom: 10px; }
.state-card .btn { margin-top: 20px; }
</style>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { api } from "@/utils/api";
import UQRCode from "@/utils/uqrcode-es.js";

const data = ref(null);
const loading = ref(true);
const error = ref("");
const now = ref(Date.now());
const qrSize = 150;
const showFullCode = ref(false);
let timer = null;
let revealTimer = null;

const REVEAL_SEC = 60;
const revealLeft = ref(0);

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
const showQr = computed(() => data.value?.status === "VALID" && !expired.value);

async function drawQr(code) {
  if (!code) return;
  await nextTick();
  const qr = new UQRCode();
  qr.data = String(code);
  qr.size = qrSize;
  qr.margin = 8;
  qr.backgroundColor = "#ffffff";
  qr.foregroundColor = "#1C1B19";
  qr.errorCorrectLevel = UQRCode.errorCorrectLevel.M;
  qr.make();
  const ctx = uni.createCanvasContext("verifyQr");
  qr.canvasContext = ctx;
  await qr.drawCanvas();
}

async function load(code) {
  loading.value = true;
  error.value = "";
  try {
    data.value = await api(`/cards/verify-code/${encodeURIComponent(code)}`);
    if (data.value?.status === "VALID" && Number(data.value.expireAt || 0) > Date.now()) {
      await drawQr(data.value.code);
    }
  } catch (e) {
    error.value = e.message || "核销码加载失败";
  } finally {
    loading.value = false;
  }
}

watch(showQr, async (ok) => {
  if (ok && data.value?.code) await drawQr(data.value.code);
});

function clearRevealTimer() {
  if (revealTimer) {
    clearInterval(revealTimer);
    revealTimer = null;
  }
}

function hideFullCode() {
  showFullCode.value = false;
  revealLeft.value = 0;
  clearRevealTimer();
}

function revealFullCode() {
  showFullCode.value = true;
  revealLeft.value = REVEAL_SEC;
  clearRevealTimer();
  revealTimer = setInterval(() => {
    revealLeft.value -= 1;
    if (revealLeft.value <= 0) hideFullCode();
  }, 1000);
}

function backToCards() {
  hideFullCode();
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
onUnmounted(() => {
  clearInterval(timer);
  clearRevealTimer();
});
</script>

<template>
  <view class="verify-page">
    <view v-if="loading" class="tiny loading-text">正在加载核销码</view>
    <view v-else-if="error" class="state-card">
      <view class="state-title">核销码无法使用</view>
      <view class="tiny">{{ error }}</view>
      <button class="btn ghost" @tap="backToCards">返回卡包</button>
    </view>

    <view v-else-if="data?.status === 'USED'" class="state-card success-card">
      <view class="success-ring">✓</view>
      <view class="state-title">核销成功</view>
      <view class="tiny">已核销 {{ data.cards?.length || 0 }} 张卡券</view>
      <button class="btn block" @tap="backToCards">返回卡包</button>
    </view>

    <view v-else-if="data?.status === 'EXPIRED' || expired" class="state-card">
      <view class="state-title expired-title">核销码已过期</view>
      <view class="tiny">卡券已自动解锁，可重新生成</view>
      <button class="btn block gold" @tap="backToCards">重新生成</button>
    </view>

    <template v-else>
      <view class="valid-line">
        <text>有效期 </text><text class="remain">{{ formatRemain() }}</text><text> · 请出示给店员扫码</text>
      </view>
      <view class="qr-box">
        <canvas
          canvas-id="verifyQr"
          id="verifyQr"
          class="qr-canvas"
          :style="{ width: qrSize + 'px', height: qrSize + 'px' }"
        />
      </view>
      <view class="masked-code" :class="{ 'is-full': showFullCode }">
        核销码 {{ showFullCode ? data.code : maskCode(data.code) }}
      </view>
      <view v-if="showFullCode" class="full-code-tip">请让顾客报码或店员输入 · {{ revealLeft }} 秒后自动隐藏</view>
      <view v-else class="reveal-link" @tap="revealFullCode">扫不出来？点此显示完整码</view>

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
.remain { color: #B92C2C; font-size: 21px; font-weight: 700; }
.qr-box {
  width: 150px;
  margin: 0 auto;
  padding: 10px;
  background: #fff;
  border: 1px solid rgba(28,27,25,.14);
  border-radius: 12px;
  box-sizing: border-box;
}
.qr-canvas {
  display: block;
  margin: 0 auto;
}
.masked-code {
  margin: 12px 0 6px;
  color: #9C9A93;
  font-size: 15px;
  letter-spacing: 0.5px;
}
.masked-code.is-full {
  color: #1C1B19;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 2px;
}
.full-code-tip {
  margin: 0 0 16px;
  color: #BA7517;
  font-size: 12px;
  line-height: 1.5;
}
.reveal-link {
  margin: 0 0 22px;
  color: #185FA5;
  font-size: 13px;
  text-decoration: underline;
}
.verify-card { padding: 18px 14px; text-align: left; }
.verify-title { font-size: 19px; font-weight: 700; margin-bottom: 17px; }
.card-row + .card-row { border-top: 1px solid rgba(28,27,25,.1); margin-top: 14px; padding-top: 14px; }
.card-name { font-size: 16px; font-weight: 600; margin-bottom: 7px; }
.rule-text { color: #BA7517; margin-top: 4px; }
.return-btn { margin-top: 18px; }
.state-card { margin-top: 48px; padding: 28px 18px; background: #fff; border: 1px solid rgba(28,27,25,.12); border-radius: 18px; }
.state-title { font-size: 19px; font-weight: 700; margin-bottom: 10px; }
.expired-title { color: #A32D2D; }
.state-card .btn { margin-top: 20px; }
.success-card { padding-top: 22px; }
.success-ring {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #EAF3DE;
  border: 2px solid #3B6D11;
  color: #3B6D11;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
}
</style>

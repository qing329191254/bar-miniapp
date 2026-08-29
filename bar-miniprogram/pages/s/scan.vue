<script setup>
import { computed, ref } from "vue";
import { onBackPress, onLoad } from "@dcloudio/uni-app";
import { api, toastText } from "@/utils/api";

const step = ref("scan");
const code = ref("");
const preview = ref(null);
const msg = ref("");
const scanning = ref(false);
const nav = ref({ paddingTop: 20, height: 44, paddingRight: 16, paddingLeft: 16 });

const cardCount = computed(() => preview.value?.cards?.length || 0);

function initNav() {
  try {
    const sys = uni.getSystemInfoSync();
    const sb = sys.statusBarHeight || 20;
    let navH = 44;
    let padR = 16;
    // #ifdef MP-WEIXIN
    const menu = uni.getMenuButtonBoundingClientRect();
    if (menu?.width) {
      navH = (menu.top - sb) * 2 + menu.height;
      padR = sys.windowWidth - menu.left + 10;
    }
    // #endif
    nav.value = { paddingTop: sb, height: navH, paddingRight: padR, paddingLeft: 16 };
  } catch (_) {}
}

const navStyle = computed(() => ({
  paddingTop: nav.value.paddingTop + "px",
}));

const navRowStyle = computed(() => ({
  height: nav.value.height + "px",
  paddingRight: nav.value.paddingRight + "px",
  paddingLeft: nav.value.paddingLeft + "px",
}));

onLoad(() => {
  initNav();
  setTimeout(scan, 350);
});

onBackPress(() => {
  if (step.value === "verify") {
    backToScan();
    return true;
  }
  return false;
});

function closePage() {
  uni.navigateBack();
}

function backToScan() {
  step.value = "scan";
  preview.value = null;
  msg.value = "";
  code.value = "";
}

async function look(inputCode) {
  msg.value = "";
  const c = (inputCode ?? code.value).trim();
  if (!c) {
    msg.value = "请输入核销码";
    return;
  }
  code.value = c;
  try {
    preview.value = await api("/staff/verify/" + c);
    step.value = "verify";
    msg.value = "";
  } catch (e) {
    msg.value = e.message;
    preview.value = null;
  }
}

async function confirm() {
  try {
    await api("/staff/verify/" + (preview.value.code || code.value) + "/confirm", { method: "POST" });
    toastText(`核销成功 ${cardCount.value} 张`);
    uni.navigateBack();
  } catch (e) {
    msg.value = e.message;
  }
}

function scan() {
  if (scanning.value) return;
  scanning.value = true;
  uni.scanCode({
    onlyFromCamera: true,
    success(res) {
      look(res.result || "");
    },
    fail(res) {
      if (!String(res?.errMsg || "").includes("cancel")) {
        msg.value = "未识别到核销码，请重试";
      }
    },
    complete() {
      scanning.value = false;
    },
  });
}

function cardTypeLabel(tpl) {
  if (!tpl) return "";
  if (tpl.cat === "OTHER") return "宝箱";
  if (tpl.cat === "GAME") return "游戏卡";
  return "酒水";
}

function isTreasure(tpl) {
  return tpl?.cat === "OTHER";
}
</script>

<template>
  <view v-if="step === 'scan'" class="scan-page">
    <view class="scan-hd" :style="navStyle">
      <view class="scan-hd-row" :style="navRowStyle">
        <text class="scan-hd-title">扫码核销</text>
        <view class="scan-close-btn" @tap="closePage">
          <text class="scan-close-icon">✕</text>
        </view>
      </view>
    </view>
    <view class="scan-view" @tap="scan">
      <view class="scan-bg" />
      <view class="scan-frame" />
      <view class="scan-frame-inner">
        <view class="scan-line" />
      </view>
      <text class="scan-hint">将核销码对准取景框</text>
      <text class="scan-tap">点击取景框开始扫码</text>
    </view>
    <view class="scan-foot">
      <view class="scan-input-row">
        <input
          class="scan-input"
          v-model="code"
          placeholder="扫码失败时输入顾客完整码"
          placeholder-class="scan-ph"
          confirm-type="done"
          maxlength="20"
          @confirm="look()"
        />
        <button class="scan-btn" @tap="look()">识别</button>
      </view>
      <view class="scan-manual-tip">请让顾客在核销码页点击「显示完整码」</view>
      <view class="scan-err" v-if="msg">{{ msg }}</view>
    </view>
  </view>

  <view v-else class="verify-page">
    <view class="verify-nav" :style="navStyle">
      <view class="scan-hd-row" :style="navRowStyle">
        <text class="verify-nav-title">核销确认</text>
        <view class="scan-close-btn verify-back-btn" @tap="backToScan">
          <text class="verify-back-icon">‹</text>
        </view>
      </view>
    </view>
    <view v-if="preview" class="verify-body">
      <view class="verify-ok card">
        <view class="verify-ring">✓</view>
        <view class="verify-ok-title">扫码成功 · 共 {{ cardCount }} 张待核销</view>
        <view class="tiny verify-ok-user">用户：{{ preview.user?.nick }} · {{ preview.user?.no }}</view>
      </view>
      <view
        v-for="(c, i) in preview.cards"
        :key="i"
        class="card verify-card"
        :class="{ treasure: isTreasure(c.tpl) }"
        :style="{ borderLeftColor: isTreasure(c.tpl) ? '#534AB7' : (c.tpl?.cat === 'GAME' ? '#534AB7' : '#1D9E75') }"
      >
        <view class="between">
          <text class="verify-name" :class="{ purple: isTreasure(c.tpl) }">{{ c.tpl?.name }}</text>
          <text class="verify-pill" :class="{ treasure: isTreasure(c.tpl) }">{{ cardTypeLabel(c.tpl) }}</text>
        </view>
        <view class="tiny verify-meta" :class="{ purple: isTreasure(c.tpl) }">
          {{ c.card?.srcDesc }} · {{ c.card?.expire || (c.tpl?.days ? c.tpl.days + ' 天' : '') }} 到期
        </view>
        <view v-if="isTreasure(c.tpl) && c.tpl?.prize" class="verify-prize">
          <view class="tiny">奖品说明</view>
          <text class="verify-prize-text">{{ c.tpl.prize }}</text>
        </view>
        <view v-else-if="c.tpl?.ruleText?.length" class="verify-rules">
          <view v-for="(rule, ri) in c.tpl.ruleText" :key="ri" class="tiny">{{ rule }}</view>
        </view>
      </view>
      <view class="verify-actions">
        <button class="btn ghost verify-cancel" @tap="backToScan">取消</button>
        <button class="btn verify-confirm" @tap="confirm">确认核销 {{ cardCount }} 张</button>
      </view>
      <view class="err" v-if="msg">{{ msg }}</view>
    </view>
    <view class="verify-body" v-else-if="msg">
      <view class="err">{{ msg }}</view>
    </view>
    <app-toast />
  </view>
</template>

<style scoped>
.scan-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #000;
  z-index: 10;
}
.scan-hd {
  flex-shrink: 0;
}
.scan-hd-row {
  position: relative;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}
.scan-close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.scan-close-icon {
  font-size: 14px;
  color: #fff;
  line-height: 1;
}
.scan-hd-title {
  position: absolute;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  pointer-events: none;
}
.scan-view {
  position: relative;
  flex: 1;
  overflow: hidden;
  background: #000;
}
.scan-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 40%, #141414, #000);
}
.scan-frame {
  position: absolute;
  left: 50%;
  top: 40%;
  transform: translate(-50%, -50%);
  width: 196px;
  height: 196px;
  border: 3px solid rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.42);
}
.scan-frame-inner {
  position: absolute;
  left: 50%;
  top: 40%;
  transform: translate(-50%, -50%);
  width: 196px;
  height: 196px;
  overflow: hidden;
  border-radius: 16px;
  pointer-events: none;
}
.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 6%;
  height: 3px;
  background: linear-gradient(90deg, transparent, #7cfc9a, transparent);
  box-shadow: 0 0 12px #7cfc9a;
  animation: scanMove 2.4s ease-in-out infinite;
}
@keyframes scanMove {
  0% { top: 6%; }
  50% { top: 90%; }
  100% { top: 6%; }
}
.scan-hint {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(40% + 112px);
  text-align: center;
  color: #fff;
  font-size: 12px;
}
.scan-tap {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(40% + 134px);
  text-align: center;
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
}
.scan-foot {
  background: #101010;
  padding: 12px 16px 24px;
}
.scan-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.scan-input {
  flex: 1;
  height: 44px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #444;
  background: #222;
  color: #fff;
  font-size: 14px;
  line-height: 44px;
  box-sizing: border-box;
}
.scan-btn {
  height: 44px;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 10px;
  border: 1px solid #555;
  background: #333;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  line-height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.scan-err {
  margin-top: 10px;
  color: #ff8a8a;
  font-size: 12px;
}
.scan-manual-tip {
  margin-top: 10px;
  color: #777;
  font-size: 11px;
  line-height: 1.5;
}

.verify-page {
  min-height: 100vh;
  box-sizing: border-box;
  background: #f5f4f0;
}
.verify-nav {
  background: #f5f4f0;
  flex-shrink: 0;
}
.verify-back-btn {
  background: rgba(28, 27, 25, 0.06);
}
.verify-back-icon {
  font-size: 22px;
  line-height: 1;
  color: #1c1b19;
  margin-top: -2px;
}
.verify-nav-title {
  position: absolute;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #1c1b19;
  pointer-events: none;
}
.verify-body {
  padding: 0 14px 36px;
}
.verify-ok {
  text-align: center;
  padding: 16px;
  background: #eaf3de;
  border-color: #97c459;
}
.verify-ring {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #97c459;
  color: #fff;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px;
}
.verify-ok-title {
  font-size: 15px;
  font-weight: 700;
  color: #04342c;
}
.verify-ok-user {
  margin-top: 3px;
  color: #3b6d11;
}
.verify-card {
  border-left-width: 3px;
  border-left-style: solid;
}
.verify-card.treasure {
  background: #eeedfe;
  border-color: #534ab7;
}
.verify-name {
  font-size: 14px;
  font-weight: 700;
  color: #1c1b19;
}
.verify-name.purple {
  color: #26215c;
}
.verify-pill {
  display: inline-block;
  border-radius: 99px;
  padding: 1px 8px;
  font-size: 11px;
  background: #f5f4f0;
  color: #6b6a65;
}
.verify-pill.treasure {
  background: #cecbf6;
  color: #26215c;
}
.verify-meta {
  margin-top: 3px;
}
.verify-meta.purple {
  color: #534ab7;
}
.verify-prize {
  background: #fff;
  border-radius: 8px;
  padding: 9px 10px;
  margin-top: 8px;
}
.verify-prize-text {
  font-size: 13px;
  font-weight: 700;
  color: #1c1b19;
}
.verify-rules {
  margin-top: 6px;
}
.verify-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.verify-cancel {
  flex: 1;
}
.verify-confirm {
  flex: 2;
}
</style>

<style>
.scan-ph {
  color: #888;
  font-size: 14px;
  line-height: 44px;
}
</style>

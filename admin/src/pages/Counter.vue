<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, token } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

defineOptions({ name: "Counter" });

type Scene = "order" | "pay" | "recharge" | "withdrawal";
type Bucket = { count: number; ids: number[] };
type Summary = {
  accept: Bucket;
  payOrder: Bucket;
  recharge: Bucket;
  withdrawal: Bucket;
  making: Bucket;
  total: number;
  serverTime: number;
  reminder: Record<string, any>;
};

const ALERT_EVENTS = new Set(["order.created", "recharge.created", "withdrawal.created"]);

/** Pre-recorded lines with original business wording（待接单/待收款…）. */
const SPEECH_SRC: Record<Scene, string> = {
  order: "/audio/speak-order.wav",
  pay: "/audio/speak-pay.wav",
  recharge: "/audio/speak-recharge.wav",
  withdrawal: "/audio/speak-withdrawal.wav",
};

const SPEECH_LABEL: Record<Scene, string> = {
  order: "接单",
  pay: "收款",
  recharge: "充值",
  withdrawal: "提分",
};

const summary = ref<Summary | null>(null);
const router = useRouter();
const loading = ref(true);
const running = ref(false);
const connected = ref(false);
const fallback = ref(false);
const soundReady = ref(false);
const lastSync = ref<Date | null>(null);
const clock = ref(new Date());
const err = ref("");
const lastAcceptIds = ref<Set<number> | null>(null);
const lastPayOrderIds = ref<Set<number> | null>(null);
const lastRechargeIds = ref<Set<number> | null>(null);
const lastWithdrawalIds = ref<Set<number> | null>(null);
let socket: WebSocket | null = null;
let reconnectTimer = 0;
let pollTimer = 0;
let heartbeatTimer = 0;
let clockTimer = 0;
let repeatTimer = 0;
let speakTimer = 0;
let reconnectAttempt = 0;
let lastAlertAt = 0;
let repeatedTimes = 0;
let audio: HTMLAudioElement | null = null;
let weakAudio: HTMLAudioElement | null = null;
let speechAudio: HTMLAudioElement | null = null;

const statusText = computed(() => {
  if (!running.value) return "值守未启动";
  if (connected.value) return "实时提醒已连接";
  if (fallback.value) return "实时连接中断 · 轮询兜底中";
  return "正在连接实时提醒";
});
const timeText = computed(() => clock.value.toLocaleTimeString("zh-CN", { hour12: false }));
const syncText = computed(() => lastSync.value ? lastSync.value.toLocaleTimeString("zh-CN", { hour12: false }) : "—");

function wsUrl() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}/ws/staff-reminders?token=${encodeURIComponent(token())}`;
}

function hasNewIds(nextIds: Set<number>, lastIds: Set<number> | null) {
  return Boolean(lastIds && [...nextIds].some((id) => !lastIds.has(id)));
}

function playChime(volume: number) {
  const player = volume >= 0.9 ? audio : weakAudio;
  if (!player) return;
  player.volume = volume;
  player.currentTime = 0;
  player.play().catch(() => undefined);
}

function stopSpeech() {
  window.clearTimeout(speakTimer);
  if (!speechAudio) return;
  try {
    speechAudio.pause();
    speechAudio.currentTime = 0;
  } catch { /* ignore */ }
}

function speakAfterChime(scene: Scene) {
  window.clearTimeout(speakTimer);
  speakTimer = window.setTimeout(() => {
    try {
      if (speechAudio) {
        speechAudio.pause();
        speechAudio.src = "";
      }
      speechAudio = new Audio(SPEECH_SRC[scene]);
      speechAudio.volume = 1;
      speechAudio.play().catch(() => undefined);
    } catch { /* chime remains the audible fallback */ }
  }, 420);
}

function speakScene(scene: Scene, opts: { force?: boolean } = {}) {
  const cfg = summary.value?.reminder || {};
  if (!opts.force) {
    if (!soundReady.value || cfg.enabled === false || cfg.pcVoice === false) return;
    if (cfg[scene] === false) return;
  } else if (!soundReady.value) {
    return;
  }
  const strong = scene === "order";
  playChime(strong ? 1 : 0.55);
  speakAfterChime(scene);
  if (strong) lastAlertAt = Date.now();
}

function speakNewOrder() {
  speakScene("order");
}

function checkRepeatReminder() {
  const cfg = summary.value?.reminder || {};
  if (!running.value || !summary.value?.accept.count || cfg.enabled === false || cfg.order === false || cfg.pcVoice === false || cfg.repeatEnabled === false) {
    if (!summary.value?.accept.count) repeatedTimes = 0;
    return;
  }
  const seconds = Math.max(10, Number(cfg.repeatSeconds || 30));
  const times = Math.max(0, Number(cfg.repeatTimes ?? 5));
  if (repeatedTimes >= times || Date.now() - lastAlertAt < seconds * 1000) return;
  repeatedTimes += 1;
  speakNewOrder();
}

function processAlerts(next: Summary) {
  const warmed =
    lastAcceptIds.value || lastPayOrderIds.value || lastRechargeIds.value || lastWithdrawalIds.value;
  if (!warmed) return;

  const nextAccept = new Set(next.accept.ids || []);
  const nextPay = new Set(next.payOrder.ids || []);
  const nextRecharge = new Set(next.recharge.ids || []);
  const nextWithdrawal = new Set(next.withdrawal.ids || []);

  if (hasNewIds(nextAccept, lastAcceptIds.value)) {
    repeatedTimes = 0;
    speakScene("order");
  } else if (hasNewIds(nextPay, lastPayOrderIds.value)) {
    speakScene("pay");
  } else if (hasNewIds(nextRecharge, lastRechargeIds.value)) {
    speakScene("recharge");
  } else if (hasNewIds(nextWithdrawal, lastWithdrawalIds.value)) {
    speakScene("withdrawal");
  }
}

async function syncSummary(allowAlert = true) {
  try {
    const next = await api<Summary>("/staff/todo-summary");
    if (allowAlert) processAlerts(next);
    lastAcceptIds.value = new Set(next.accept.ids || []);
    lastPayOrderIds.value = new Set(next.payOrder.ids || []);
    lastRechargeIds.value = new Set(next.recharge.ids || []);
    lastWithdrawalIds.value = new Set(next.withdrawal.ids || []);
    summary.value = next;
    lastSync.value = new Date();
    err.value = "";
    await nextTick();
    return next;
  } catch (e: any) {
    err.value = e?.message || "同步失败";
    return null;
  }
}

async function loadInitial() {
  loading.value = true;
  await syncSummary(false);
  loading.value = false;
}

function beginFallback() {
  fallback.value = true;
  window.clearInterval(pollTimer);
  pollTimer = window.setInterval(() => syncSummary(true), 5000);
}

function stopFallback() {
  fallback.value = false;
  window.clearInterval(pollTimer);
  pollTimer = 0;
}

function scheduleReconnect() {
  if (!running.value) return;
  beginFallback();
  const delay = Math.min(30000, 1000 * 2 ** Math.min(reconnectAttempt++, 5));
  window.clearTimeout(reconnectTimer);
  reconnectTimer = window.setTimeout(connectSocket, delay);
}

function connectSocket() {
  if (!running.value) return;
  const previous = socket;
  if (previous) {
    previous.onclose = null;
    previous.close();
  }
  const current = new WebSocket(wsUrl());
  socket = current;
  current.onopen = () => {
    if (socket !== current) return;
    connected.value = true;
    reconnectAttempt = 0;
    stopFallback();
    syncSummary(true);
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = window.setInterval(() => {
      if (current.readyState === WebSocket.OPEN) current.send("ping");
    }, 25000);
  };
  current.onmessage = async (event) => {
    if (socket !== current) return;
    try {
      const message = JSON.parse(event.data);
      await syncSummary(ALERT_EVENTS.has(message.event));
    } catch { /* ignore malformed event */ }
  };
  current.onerror = () => current.close();
  current.onclose = () => {
    if (socket !== current) return;
    socket = null;
    connected.value = false;
    window.clearInterval(heartbeatTimer);
    scheduleReconnect();
  };
}

async function start() {
  audio ||= new Audio("/audio/new-order.wav");
  weakAudio ||= new Audio("/audio/new-order.wav");
  audio.volume = 1;
  await audio.play().catch(() => undefined);
  audio.pause();
  audio.currentTime = 0;
  soundReady.value = true;
  running.value = true;
  await syncSummary(false);
  lastAlertAt = Date.now();
  repeatedTimes = 0;
  window.clearInterval(repeatTimer);
  repeatTimer = window.setInterval(checkRepeatReminder, 1000);
  connectSocket();
}

function stop() {
  running.value = false;
  connected.value = false;
  fallback.value = false;
  socket?.close();
  socket = null;
  window.clearTimeout(reconnectTimer);
  stopSpeech();
  window.clearInterval(pollTimer);
  window.clearInterval(heartbeatTimer);
  window.clearInterval(repeatTimer);
}

async function ensureSoundReady() {
  if (soundReady.value) return true;
  await start();
  return soundReady.value;
}

async function testScene(scene: Scene) {
  const ok = await ensureSoundReady();
  if (!ok) return;
  speakScene(scene, { force: true });
}

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen?.();
}

function openQueue(kind: "accept" | "pay" | "recharge" | "withdrawal") {
  const targets = {
    accept: { path: "/orders", query: { status: "PENDING_ACCEPT" } },
    pay: { path: "/orders", query: { status: "PENDING_PAY" } },
    recharge: { path: "/recharges" },
    withdrawal: { path: "/withdrawals", query: { status: "PENDING_CONFIRM" } },
  };
  router.push(targets[kind]);
}

onMounted(() => {
  clockTimer = window.setInterval(() => (clock.value = new Date()), 1000);
  loadInitial();
});
onBeforeUnmount(() => {
  stop();
  window.clearInterval(clockTimer);
});
</script>

<template>
  <AppAsyncPage
    :loading="loading"
    :data="summary"
    :err="err"
    :skeleton="{ variant: 'dashboard', metrics: 4, showFilter: false, showNote: true, showExtraCard: true, showChart: false }"
    @retry="loadInitial"
  >
  <div class="counter-page">
    <div class="counter-head">
      <div>
        <div class="counter-title">吧台值守</div>
        <div class="counter-status" :class="{ ok: connected, warn: fallback }"><i />{{ statusText }}</div>
      </div>
      <div class="counter-clock"><b>{{ timeText }}</b><span>上次同步 {{ syncText }}</span></div>
    </div>

    <div v-if="err" class="counter-alert">{{ err }}</div>

    <div class="counter-metrics">
      <button type="button" class="counter-metric primary" @click="openQueue('accept')"><span>待接单</span><b>{{ summary?.accept.count || 0 }}</b><small>强提醒：提示音 + 语音，可重复催单</small></button>
      <button type="button" class="counter-metric" @click="openQueue('pay')"><span>待收款</span><b>{{ summary?.payOrder.count || 0 }}</b><small>提示音 + 「待收款」语音</small></button>
      <button type="button" class="counter-metric" @click="openQueue('recharge')"><span>待确认充值</span><b>{{ summary?.recharge.count || 0 }}</b><small>提示音 + 「待确认」语音</small></button>
      <button type="button" class="counter-metric" @click="openQueue('withdrawal')"><span>待确认提分</span><b>{{ summary?.withdrawal.count || 0 }}</b><small>提示音 + 「待确认」语音</small></button>
    </div>

    <div class="counter-panel">
      <div class="counter-panel-copy">
        <b>{{ running ? "值守运行中" : "点击开始值守，启用电脑语音" }}</b>
        <span>营业期间请保持此页面打开，并确认电脑未静音、音响为默认输出设备。语音为预录音频，不依赖本机朗读引擎。</span>
      </div>
      <div class="counter-actions">
        <button v-if="!running" class="btn gold counter-main-btn" @click="start">开始值守</button>
        <button v-else class="btn ghost counter-main-btn" @click="stop">暂停值守</button>
        <button class="btn ghost" @click="toggleFullscreen">全屏显示</button>
      </div>
    </div>

    <div class="counter-test">
      <div class="counter-test-label">试听提醒</div>
      <div class="counter-test-actions">
        <button class="btn ghost" @click="testScene('order')">测试{{ SPEECH_LABEL.order }}</button>
        <button class="btn ghost" @click="testScene('pay')">测试{{ SPEECH_LABEL.pay }}</button>
        <button class="btn ghost" @click="testScene('recharge')">测试{{ SPEECH_LABEL.recharge }}</button>
        <button class="btn ghost" @click="testScene('withdrawal')">测试{{ SPEECH_LABEL.withdrawal }}</button>
      </div>
    </div>

    <div class="counter-footnote">
      <span>实时通道</span><b>{{ connected ? "正常" : "未连接" }}</b>
      <span>语音权限</span><b>{{ soundReady ? "已启用" : "待启用" }}</b>
      <span>兜底刷新</span><b>{{ fallback ? "每 5 秒" : "待命" }}</b>
      <span>未接单复播</span><b>{{ summary?.reminder?.repeatEnabled === false ? "已关闭" : `${summary?.reminder?.repeatTimes ?? 5} 次` }}</b>
    </div>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.counter-page{min-height:calc(100vh - 78px);padding:4px;display:flex;flex-direction:column;gap:14px}
.counter-head{display:flex;justify-content:space-between;align-items:center;padding:18px 20px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:var(--shadow)}
.counter-title{font-size:26px;font-weight:700;letter-spacing:-.5px}
.counter-status{display:flex;align-items:center;gap:7px;margin-top:5px;color:var(--ink3);font-size:12px}.counter-status i{width:8px;height:8px;border-radius:50%;background:#9c9a93}.counter-status.ok{color:#3b6d11}.counter-status.ok i{background:#61a72b;box-shadow:0 0 0 4px rgba(97,167,43,.12)}.counter-status.warn{color:#ba7517}.counter-status.warn i{background:#d7932e}
.counter-clock{text-align:right}.counter-clock b{display:block;font-size:28px;font-variant-numeric:tabular-nums}.counter-clock span{display:block;color:var(--ink3);font-size:11px}
.counter-alert{padding:10px 13px;border-radius:10px;background:#fcebeb;color:#a32d2d;font-size:12px}
.counter-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.counter-metric{min-height:190px;padding:22px;border:1px solid var(--line);border-radius:18px;background:#fff;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;box-shadow:var(--shadow);font:inherit;text-align:left;color:inherit;cursor:pointer;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}.counter-metric:hover{transform:translateY(-2px);border-color:rgba(185,120,34,.38);box-shadow:0 12px 28px rgba(74,52,28,.1)}.counter-metric:focus-visible{outline:2px solid rgba(185,120,34,.5);outline-offset:2px}.counter-metric.primary{background:linear-gradient(145deg,#fff7e9,#fae3bd);border-color:rgba(185,120,34,.3)}.counter-metric span{font-size:14px;color:var(--ink2)}.counter-metric b{margin:6px 0;font-size:64px;line-height:1;font-variant-numeric:tabular-nums}.counter-metric.primary b{color:#9d6118}.counter-metric small{color:var(--ink3);font-size:11px}
.counter-panel{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px;border:1px solid var(--line);border-radius:18px;background:#fff}.counter-panel-copy b,.counter-panel-copy span{display:block}.counter-panel-copy b{font-size:15px}.counter-panel-copy span{margin-top:4px;color:var(--ink3);font-size:12px}.counter-actions{display:flex;align-items:center;gap:8px;flex:none}.counter-actions .btn{margin:0}.counter-main-btn{min-width:118px}
.counter-test{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 18px;border:1px solid var(--line);border-radius:14px;background:#fff}.counter-test-label{flex:none;font-size:13px;font-weight:600;color:var(--ink2)}.counter-test-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}.counter-test-actions .btn{margin:0}
.counter-footnote{display:flex;gap:10px;align-items:center;padding:13px 16px;border-radius:12px;background:#f6f3ed;color:var(--ink3);font-size:11px}.counter-footnote b{margin-right:16px;color:var(--ink2)}
@media(max-width:900px){.counter-metrics{grid-template-columns:repeat(2,1fr)}.counter-metric{min-height:145px}.counter-panel,.counter-test{align-items:flex-start;flex-direction:column}.counter-actions,.counter-test-actions{width:100%;flex-wrap:wrap;justify-content:flex-start}}
</style>

import { reactive } from "vue";
import { api, BASE, canUseCloudContainer, CLOUD_MAX_TIMEOUT_MS, savedUser, token } from "@/utils/api";

const PREF_KEY = "wanka_staff_reminder_pref";
const ALERT_EVENTS = new Set(["order.created", "recharge.created", "withdrawal.created"]);
const LONG_POLL_TIMEOUT = 12;
const CONNECTED_POLL_MS = 30000;
const FALLBACK_POLL_MS = 5000;
const CONNECT_TIMEOUT_MS = 8000;

export const reminderState = reactive({
  running: false,
  connected: false,
  fallback: false,
  total: 0,
  accept: 0,
  lastSync: 0,
  syncSeq: 0,
  prefs: {
    voice: true,
    badge: true,
  },
});

let socketTask = null;
let pollTimer = null;
let heartbeatTimer = null;
let reconnectTimer = null;
let connectTimeoutTimer = null;
let reconnectAttempt = 0;
let longPollToken = 0;
let lastAcceptIds = null;
let lastRechargeIds = null;
let lastWithdrawalIds = null;
let currentSummary = null;
let audio = null;
const handledEvents = new Set();
const todoRefreshHandlers = new Set();

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function loadPrefs() {
  const saved = uni.getStorageSync(PREF_KEY);
  if (saved && typeof saved === "object") Object.assign(reminderState.prefs, saved);
}

export function registerTodoRefresh(fn) {
  if (typeof fn === "function") todoRefreshHandlers.add(fn);
}

export function unregisterTodoRefresh(fn) {
  todoRefreshHandlers.delete(fn);
}

function notifyTodoRefresh() {
  todoRefreshHandlers.forEach((fn) => {
    try {
      fn();
    } catch { /* keep badge/alerts working */ }
  });
}

export function saveReminderPrefs(patch) {
  Object.assign(reminderState.prefs, patch || {});
  uni.setStorageSync(PREF_KEY, { ...reminderState.prefs });
  if (patch && patch.badge === false) reminderState.total = 0;
  if (patch && patch.badge === true) syncReminderSummary(false);
}

function isStaff() {
  const user = savedUser();
  return user && user.role && user.role !== "CUSTOMER" && token();
}

function allow(summary, key) {
  const cfg = summary && summary.reminder;
  return !cfg || (cfg.enabled !== false && cfg[key] !== false);
}

function hasNewIds(nextIds, lastIds) {
  if (!lastIds) return false;
  return [...nextIds].some((id) => !lastIds.has(id));
}

function pruneHandledEvents() {
  if (handledEvents.size <= 200) return;
  const keep = [...handledEvents].slice(-100);
  handledEvents.clear();
  keep.forEach((id) => handledEvents.add(id));
}

function noteEvent(message) {
  const eventId = `${message.event}:${message.id}`;
  if (handledEvents.has(eventId)) return false;
  handledEvents.add(eventId);
  pruneHandledEvents();
  return true;
}

function ensureAudio() {
  if (audio) return audio;
  audio = uni.createInnerAudioContext();
  audio.src = "/static/audio/new-order.wav";
  audio.obeyMuteSwitch = false;
  return audio;
}

function playChime(volume = 1) {
  const player = ensureAudio();
  try {
    if (typeof player.volume === "number") player.volume = volume;
    player.stop();
    player.seek(0);
    player.play();
  } catch { /* badge remains available */ }
}

function alertStrong(summary) {
  if (!allow(summary, "order")) return;
  const cfg = summary && summary.reminder;
  if (reminderState.prefs.voice && (!cfg || cfg.miniVoice !== false)) {
    playChime(1);
  }
}

function alertWeak(summary, sceneKey) {
  if (!allow(summary, sceneKey)) return;
  const cfg = summary && summary.reminder;
  if (reminderState.prefs.voice && (!cfg || cfg.miniVoice !== false)) {
    playChime(0.45);
  }
}

function processAlerts(next) {
  if (!lastAcceptIds && !lastRechargeIds && !lastWithdrawalIds) return;

  const acceptIds = new Set((next.accept && next.accept.ids) || []);
  const rechargeIds = new Set((next.recharge && next.recharge.ids) || []);
  const withdrawalIds = new Set((next.withdrawal && next.withdrawal.ids) || []);

  if (hasNewIds(acceptIds, lastAcceptIds)) {
    alertStrong(next);
  } else if (hasNewIds(rechargeIds, lastRechargeIds)) {
    alertWeak(next, "recharge");
  } else if (hasNewIds(withdrawalIds, lastWithdrawalIds)) {
    alertWeak(next, "withdrawal");
  }
}

function updateIdSnapshots(next) {
  lastAcceptIds = new Set((next.accept && next.accept.ids) || []);
  lastRechargeIds = new Set((next.recharge && next.recharge.ids) || []);
  lastWithdrawalIds = new Set((next.withdrawal && next.withdrawal.ids) || []);
}

function markSynced() {
  reminderState.lastSync = Date.now();
  reminderState.syncSeq = (reminderState.syncSeq || 0) + 1;
  notifyTodoRefresh();
}

export async function syncReminderSummary(alert = true) {
  if (!isStaff()) return null;
  try {
    const next = await api("/staff/todo-summary", { loading: false, silent: true });
    currentSummary = next;
    if (alert) processAlerts(next);
    updateIdSnapshots(next);
    reminderState.total = next.reminder?.enabled === false || next.reminder?.miniBadge === false || !reminderState.prefs.badge ? 0 : Number(next.total || 0);
    reminderState.accept = Number(next.accept?.count || 0);
    markSynced();
    reminderState.connected = true;
    reminderState.fallback = false;
    return next;
  } catch {
    return null;
  }
}

function startPoll(ms) {
  clearInterval(pollTimer);
  pollTimer = setInterval(() => syncReminderSummary(true), ms);
}

function clearConnectTimeout() {
  if (connectTimeoutTimer) {
    clearTimeout(connectTimeoutTimer);
    connectTimeoutTimer = null;
  }
}

function enterFallbackPoll() {
  reminderState.connected = false;
  reminderState.fallback = true;
  startPoll(FALLBACK_POLL_MS);
}

function scheduleReconnect() {
  if (!reminderState.running) return;
  clearConnectTimeout();
  enterFallbackPoll();
  const delay = Math.min(30000, 1000 * 2 ** Math.min(reconnectAttempt++, 5));
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectSocket, delay);
}

async function handleTodoChanged(message, alertDefault = true) {
  const alert = ALERT_EVENTS.has(message.event) && alertDefault;
  if (alert && !noteEvent(message)) return;
  await syncReminderSummary(alert);
}

function handleWsMessage(message) {
  if (message.type === "pong" || message.type === "connected") return;
  if (message.type === "todo.changed") {
    handleTodoChanged(message);
    return;
  }
  if (ALERT_EVENTS.has(message.event)) {
    if (noteEvent(message)) syncReminderSummary(true);
    return;
  }
  setTimeout(() => syncReminderSummary(false), 300);
}

function connectSocket() {
  if (!reminderState.running || !isStaff()) return;

  clearConnectTimeout();
  reminderState.connected = false;
  if (!pollTimer) startPoll(FALLBACK_POLL_MS);

  connectTimeoutTimer = setTimeout(() => {
    if (!reminderState.connected && reminderState.running) {
      reminderState.fallback = true;
      try {
        socketTask?.close({ code: 4000, reason: "connect timeout" });
      } catch { /* already closed */ }
    }
  }, CONNECT_TIMEOUT_MS);

  const wsUrl = `${BASE.replace(/^http/, "ws").replace(/\/$/, "")}/ws/staff-reminders?token=${encodeURIComponent(token())}`;

  let task;
  try {
    task = uni.connectSocket({ url: wsUrl, complete: () => undefined });
  } catch {
    scheduleReconnect();
    return;
  }
  if (!task || typeof task.onOpen !== "function") {
    task?.catch?.(() => undefined);
    scheduleReconnect();
    return;
  }
  socketTask = task;
  task.onOpen(() => {
    clearConnectTimeout();
    reminderState.connected = true;
    reminderState.fallback = false;
    reconnectAttempt = 0;
    startPoll(CONNECTED_POLL_MS);
    syncReminderSummary(true);
    clearInterval(heartbeatTimer);
    heartbeatTimer = setInterval(() => socketTask?.send({ data: "ping" }), 25000);
  });
  task.onMessage((event) => {
    try {
      handleWsMessage(JSON.parse(event.data));
    } catch { /* ignore malformed event */ }
  });
  task.onError(() => scheduleReconnect());
  task.onClose(() => {
    if (!reminderState.running) return;
    scheduleReconnect();
  });
}

async function runLongPollLoop() {
  const loopId = ++longPollToken;
  reminderState.connected = false;
  reminderState.fallback = false;

  while (reminderState.running && longPollToken === loopId) {
    try {
      const result = await api(`/staff/todo-wait?timeout=${LONG_POLL_TIMEOUT}`, {
        loading: false,
        silent: true,
        timeoutMs: CLOUD_MAX_TIMEOUT_MS,
      });
      if (!reminderState.running || longPollToken !== loopId) return;

      reminderState.connected = true;
      reminderState.fallback = false;

      if (result?.type === "todo.changed") {
        await handleTodoChanged(result);
      } else {
        await syncReminderSummary(false);
      }
    } catch {
      if (!reminderState.running || longPollToken !== loopId) return;
      reminderState.connected = false;
      reminderState.fallback = true;
      await sleep(3000);
    }
  }
}

export async function startStaffReminder() {
  if (!isStaff()) return;
  if (reminderState.running) {
    await syncReminderSummary(false);
    return;
  }
  loadPrefs();
  reminderState.running = true;
  reminderState.connected = false;
  reminderState.fallback = false;
  uni.setKeepScreenOn({ keepScreenOn: true, fail: () => undefined });
  await syncReminderSummary(false);

  if (canUseCloudContainer()) {
    runLongPollLoop();
  } else {
    connectSocket();
  }
}

export function stopStaffReminder() {
  longPollToken += 1;
  reminderState.running = false;
  reminderState.connected = false;
  reminderState.fallback = false;
  clearInterval(pollTimer);
  pollTimer = null;
  clearInterval(heartbeatTimer);
  clearTimeout(reconnectTimer);
  clearConnectTimeout();
  socketTask?.close({ code: 1000, reason: "app hidden" });
  socketTask = null;
  currentSummary = null;
}

export function testStaffReminder() {
  playChime(1);
}

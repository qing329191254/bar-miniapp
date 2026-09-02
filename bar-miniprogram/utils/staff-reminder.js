import { reactive } from "vue";
import { api, BASE, savedUser, token } from "@/utils/api";

const PREF_KEY = "wanka_staff_reminder_pref";
const ALERT_EVENTS = new Set(["order.created", "recharge.created", "withdrawal.created"]);

export const reminderState = reactive({
  running: false,
  connected: false,
  fallback: false,
  total: 0,
  accept: 0,
  lastSync: 0,
  prefs: {
    voice: true,
    vibrate: true,
    badge: true,
  },
});

let socketTask = null;
let pollTimer = null;
let heartbeatTimer = null;
let reconnectTimer = null;
let reconnectAttempt = 0;
let lastAcceptIds = null;
let lastRechargeIds = null;
let lastWithdrawalIds = null;
let currentSummary = null;
let audio = null;
const handledEvents = new Set();

function loadPrefs() {
  const saved = uni.getStorageSync(PREF_KEY);
  if (saved && typeof saved === "object") Object.assign(reminderState.prefs, saved);
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

function noteWsEvent(message) {
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
  } catch { /* vibration and badge remain available */ }
}

function alertStrong(summary) {
  if (!allow(summary, "order")) return;
  const cfg = summary && summary.reminder;
  if (reminderState.prefs.vibrate && (!cfg || cfg.miniVibrate !== false)) {
    uni.vibrateLong({ fail: () => undefined });
  }
  if (reminderState.prefs.voice && (!cfg || cfg.miniVoice !== false)) {
    playChime(1);
  }
}

function alertWeak(summary, sceneKey) {
  if (!allow(summary, sceneKey)) return;
  const cfg = summary && summary.reminder;
  if (reminderState.prefs.vibrate && (!cfg || cfg.miniVibrate !== false)) {
    uni.vibrateShort({ fail: () => undefined });
  }
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

export async function syncReminderSummary(alert = true) {
  if (!isStaff()) return null;
  try {
    const next = await api("/staff/todo-summary", { loading: false });
    currentSummary = next;
    if (alert) processAlerts(next);
    updateIdSnapshots(next);
    reminderState.total = next.reminder?.enabled === false || next.reminder?.miniBadge === false || !reminderState.prefs.badge ? 0 : Number(next.total || 0);
    reminderState.accept = Number(next.accept?.count || 0);
    reminderState.lastSync = Date.now();
    return next;
  } catch {
    return null;
  }
}

function startPoll(ms) {
  clearInterval(pollTimer);
  pollTimer = setInterval(() => syncReminderSummary(true), ms);
}

function scheduleReconnect() {
  if (!reminderState.running) return;
  reminderState.connected = false;
  reminderState.fallback = true;
  startPoll(5000);
  const delay = Math.min(30000, 1000 * 2 ** Math.min(reconnectAttempt++, 5));
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectSocket, delay);
}

function connectSocket() {
  if (!reminderState.running || !isStaff()) return;
  const url = `${BASE.replace(/^http/, "ws").replace(/\/$/, "")}/ws/staff-reminders?token=${encodeURIComponent(token())}`;
  let task;
  try {
    task = uni.connectSocket({ url, complete: () => undefined });
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
    reminderState.connected = true;
    reminderState.fallback = false;
    reconnectAttempt = 0;
    startPoll(60000);
    syncReminderSummary(true);
    clearInterval(heartbeatTimer);
    heartbeatTimer = setInterval(() => socketTask?.send({ data: "ping" }), 25000);
  });
  task.onMessage((event) => {
    try {
      const message = JSON.parse(event.data);
      if (ALERT_EVENTS.has(message.event)) {
        if (noteWsEvent(message)) syncReminderSummary(true);
        return;
      }
      setTimeout(() => syncReminderSummary(false), 300);
    } catch { /* ignore malformed event */ }
  });
  task.onError(() => undefined);
  task.onClose(scheduleReconnect);
}

export async function startStaffReminder() {
  if (!isStaff()) return;
  if (reminderState.running) {
    await syncReminderSummary(false);
    return;
  }
  loadPrefs();
  reminderState.running = true;
  uni.setKeepScreenOn({ keepScreenOn: true, fail: () => undefined });
  await syncReminderSummary(false);
  connectSocket();
}

export function stopStaffReminder() {
  reminderState.running = false;
  reminderState.connected = false;
  reminderState.fallback = false;
  clearInterval(pollTimer);
  clearInterval(heartbeatTimer);
  clearTimeout(reconnectTimer);
  socketTask?.close({ code: 1000, reason: "app hidden" });
  socketTask = null;
  currentSummary = null;
}

export function testStaffReminder() {
  playChime(1);
  uni.vibrateShort({ fail: () => undefined });
}

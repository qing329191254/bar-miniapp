import { reactive } from "vue";
import { api, BASE, savedUser, token } from "@/utils/api";

const PREF_KEY = "wanka_staff_reminder_pref";

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

function ensureAudio() {
  if (audio) return audio;
  audio = uni.createInnerAudioContext();
  audio.src = "/static/audio/new-order.wav";
  audio.obeyMuteSwitch = false;
  return audio;
}

function alertNewOrder(summary) {
  if (!allow(summary, "order")) return;
  const cfg = summary && summary.reminder;
  if (reminderState.prefs.vibrate && (!cfg || cfg.miniVibrate !== false)) {
    uni.vibrateLong({ fail: () => undefined });
  }
  if (reminderState.prefs.voice && (!cfg || cfg.miniVoice !== false)) {
    const player = ensureAudio();
    try {
      player.stop();
      player.seek(0);
      player.play();
    } catch { /* vibration and badge remain available */ }
  }
}

export async function syncReminderSummary(alert = true) {
  if (!isStaff()) return null;
  try {
    const next = await api("/staff/todo-summary", { loading: false });
    currentSummary = next;
    const nextIds = new Set((next.accept && next.accept.ids) || []);
    if (alert && lastAcceptIds) {
      const hasNew = [...nextIds].some((id) => !lastAcceptIds.has(id));
      if (hasNew) alertNewOrder(next);
    }
    lastAcceptIds = nextIds;
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
  socketTask = uni.connectSocket({ url });
  socketTask.onOpen(() => {
    reminderState.connected = true;
    reminderState.fallback = false;
    reconnectAttempt = 0;
    startPoll(60000);
    syncReminderSummary(true);
    clearInterval(heartbeatTimer);
    heartbeatTimer = setInterval(() => socketTask?.send({ data: "ping" }), 25000);
  });
  socketTask.onMessage((event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.event === "order.created") {
        const eventId = `${message.event}:${message.id}`;
        if (!handledEvents.has(eventId)) {
          handledEvents.add(eventId);
          alertNewOrder(currentSummary);
        }
      }
      setTimeout(() => syncReminderSummary(false), 300);
    } catch { /* ignore malformed event */ }
  });
  socketTask.onError(() => undefined);
  socketTask.onClose(scheduleReconnect);
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
  ensureAudio().play();
  uni.vibrateShort({ fail: () => undefined });
}

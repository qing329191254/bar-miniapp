<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { onBackPress } from "@dcloudio/uni-app";
import { api, clearGameDraft, go, hideWxHomeButton, loadGameDraft, saveGameDraft, toastText } from "@/utils/api";

const meta = ref({ projects: [], tables: [], busy: [], cardTpls: [] });
const members = ref([]);
const search = ref("");
const splitTotal = ref("");
const customShard = ref("");
const showCustomDlg = ref(false);
const msg = ref("");
const submitting = ref(false);
const confirmTime = ref("");
const showDraftDlg = ref(false);
const showExitDlg = ref(false);
const showZeroRewardDlg = ref(false);
const showGiftDlg = ref(false);
const giftUid = ref(null);
const giftDraft = ref({});

const dlgOpen = computed(() => showDraftDlg.value || showCustomDlg.value || showExitDlg.value || showZeroRewardDlg.value || showGiftDlg.value);

const wiz = reactive({
  step: 0,
  projectId: null,
  tableId: null,
  players: [],
  shr: {},
  pts: {},
  gifts: {},
  winners: {},
  event: "",
  eventTouched: false,
  round: "",
  last: null,
});

onMounted(async () => {
  hideWxHomeButton();
  meta.value = await api("/staff/projects");
  members.value = await api("/staff/members");
});

watch(
  wiz,
  () => {
    if (wiz.step >= 1 && wiz.step <= 4) saveGameDraft(JSON.parse(JSON.stringify(wiz)));
  },
  { deep: true },
);

const project = computed(() => meta.value.projects.find((p) => p.id === wiz.projectId));
const table = computed(() => meta.value.tables.find((t) => t.id === wiz.tableId));
const pickedUsers = computed(() => wiz.players.map((id) => members.value.find((m) => m.id === id)).filter(Boolean));
const found = computed(() => {
  const kw = search.value.trim();
  if (!kw) return [];
  return members.value.filter(
    (x) => !wiz.players.includes(x.id) && (x.nick.includes(kw) || String(x.tail).includes(kw) || String(x.no).includes(kw)),
  );
});
const quick = computed(() => {
  const s = Number(project.value?.shard) || 0;
  return [Math.round(s / 2), s, Math.round(s * 1.5)].filter((v) => v > 0);
});
const activeQuickShard = computed(() => {
  if (!wiz.players.length) return null;
  const vals = wiz.players.map((id) => Number(wiz.shr[id] || 0));
  const first = vals[0];
  if (first <= 0 || !vals.every((v) => v === first)) return null;
  return quick.value.includes(first) ? first : "custom";
});
const totalPts = computed(() => wiz.players.reduce((s, id) => s + Number(wiz.pts[id] || 0), 0));
const totalSh = computed(() => wiz.players.reduce((s, id) => s + Number(wiz.shr[id] || 0), 0));
const totalGifts = computed(() => wiz.players.reduce((s, id) => s + giftCount(id), 0));
const winCount = computed(() => wiz.players.filter((id) => wiz.winners[id]).length);
const giftTplGroups = computed(() => {
  const CAT = { GAME: "游戏卡", FOOD: "酒水小食卡", OTHER: "其他卡券" };
  const groups = {};
  for (const t of meta.value.cardTpls || []) {
    const key = t.cat || "OTHER";
    if (!groups[key]) groups[key] = { key, label: CAT[key] || key, items: [] };
    groups[key].items.push(t);
  }
  return Object.values(groups);
});
const giftTarget = computed(() => members.value.find((m) => m.id === giftUid.value) || null);
const peopleWarn = computed(() => {
  const pj = project.value;
  if (!pj || !pj.min) return "";
  if (wiz.players.length < pj.min || wiz.players.length > pj.max) {
    return `${pj.name} 通常 ${pj.min}-${pj.max} 人（提示不阻断）`;
  }
  return "";
});
const quickCombos = computed(() => {
  const { projects, tables } = meta.value;
  if (!projects.length) return [];
  const presets = [
    { pKey: "狼人", tKey: "A3" },
    { pKey: "德", tKey: "卡座1" },
  ];
  const out = [];
  for (const { pKey, tKey } of presets) {
    const p = projects.find((x) => x.name.includes(pKey));
    const t = tables.find((x) => x.name.includes(tKey));
    if (p && t) out.push({ pid: p.id, tid: t.id, label: `${p.name} · ${t.name}` });
  }
  return out;
});

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}
function busy(id) {
  return (meta.value.busy || []).includes(id);
}
function defaultEvent() {
  const p = project.value;
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mi = String(now.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${mi} ${p ? p.name : "对局"}`;
}
function nowTimeLabel() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}
function resetWiz(step = 0) {
  Object.assign(wiz, {
    step,
    projectId: null,
    tableId: null,
    players: [],
    shr: {},
    pts: {},
    gifts: {},
    winners: {},
    event: "",
    eventTouched: false,
    round: "",
    last: null,
  });
  search.value = "";
  splitTotal.value = "";
  customShard.value = "";
  showCustomDlg.value = false;
  showGiftDlg.value = false;
  giftUid.value = null;
  giftDraft.value = {};
  confirmTime.value = "";
  msg.value = "";
}

function startWiz() {
  if (hasDraft()) {
    showDraftDlg.value = true;
    return;
  }
  resetWiz(1);
}
function closeDraftDlg() {
  showDraftDlg.value = false;
}
function confirmDraftDlg() {
  showDraftDlg.value = false;
  restoreDraft();
}
function restoreDraft() {
  const d = loadGameDraft();
  if (!d) return;
  clearGameDraft();
  Object.assign(wiz, d);
  if (!wiz.gifts) wiz.gifts = {};
  if (wiz.step === 4 && !confirmTime.value) confirmTime.value = nowTimeLabel();
}
function combo(pid, tid) {
  Object.assign(wiz, {
    step: 2,
    projectId: pid,
    tableId: tid,
    players: [],
    shr: {},
    pts: {},
    gifts: {},
    winners: {},
    event: "",
    eventTouched: false,
    round: "",
    last: null,
  });
  msg.value = "";
}
function restoreEventDefault() {
  wiz.eventTouched = false;
  wiz.event = defaultEvent();
}
function next() {
  msg.value = "";
  if (wiz.step === 1 && !wiz.projectId) {
    msg.value = "请选择对局项目";
    return;
  }
  if (wiz.step === 2 && !wiz.players.length) {
    msg.value = "请至少选择 1 位玩家";
    return;
  }
  wiz.step += 1;
  if (wiz.step === 4) {
    confirmTime.value = nowTimeLabel();
    if (!wiz.eventTouched) wiz.event = defaultEvent();
  }
}
function prev() {
  msg.value = "";
  if (wiz.step <= 1) return;
  wiz.step -= 1;
}
function hasWizProgress() {
  return !!(wiz.projectId || wiz.tableId || (wiz.round || "").trim() || wiz.players.length);
}
function cancelWiz() {
  msg.value = "";
  if (hasWizProgress()) {
    showExitDlg.value = true;
    return;
  }
  clearGameDraft();
  resetWiz(0);
}
function closeExitDlg() {
  showExitDlg.value = false;
}
function confirmExitWiz() {
  showExitDlg.value = false;
  saveGameDraft(JSON.parse(JSON.stringify(wiz)));
  resetWiz(0);
}
function goBack() {
  if (wiz.step === 1) cancelWiz();
  else prev();
}

onBackPress(() => {
  if (dlgOpen.value) {
    showDraftDlg.value = false;
    showCustomDlg.value = false;
    showExitDlg.value = false;
    showZeroRewardDlg.value = false;
    showGiftDlg.value = false;
    return true;
  }
  if (wiz.step >= 1 && wiz.step <= 4) {
    goBack();
    return true;
  }
  return false;
});
function giftCount(uid) {
  const bag = wiz.gifts[uid] || {};
  return Object.values(bag).reduce((s, n) => s + Number(n || 0), 0);
}
function giftList(uid) {
  const bag = wiz.gifts[uid] || {};
  return Object.entries(bag)
    .filter(([, q]) => Number(q) > 0)
    .map(([tpl, qty]) => ({ tpl: Number(tpl), qty: Number(qty) }));
}
function toggle(id) {
  const i = wiz.players.indexOf(id);
  if (i >= 0) {
    wiz.players.splice(i, 1);
    delete wiz.shr[id];
    delete wiz.pts[id];
    delete wiz.gifts[id];
    delete wiz.winners[id];
  } else {
    wiz.players.push(id);
    wiz.shr[id] = 0;
    wiz.pts[id] = 0;
    wiz.gifts[id] = {};
  }
}
function openGiftDlg(user) {
  giftUid.value = user.id;
  giftDraft.value = { ...(wiz.gifts[user.id] || {}) };
  showGiftDlg.value = true;
}
function closeGiftDlg() {
  showGiftDlg.value = false;
  giftUid.value = null;
  giftDraft.value = {};
}
function draftQty(tplId) {
  return Number(giftDraft.value[tplId] || 0);
}
function setDraftQty(tplId, next) {
  const n = Math.max(0, Math.min(99, Number(next) || 0));
  if (n <= 0) {
    const copy = { ...giftDraft.value };
    delete copy[tplId];
    giftDraft.value = copy;
  } else {
    giftDraft.value = { ...giftDraft.value, [tplId]: n };
  }
}
function confirmGiftDlg() {
  if (giftUid.value == null) return;
  wiz.gifts[giftUid.value] = { ...giftDraft.value };
  closeGiftDlg();
}
function shardAll(v) {
  wiz.players.forEach((id) => {
    wiz.shr[id] = v;
  });
  showCustomDlg.value = false;
}
function openCustomDlg() {
  customShard.value = "";
  showCustomDlg.value = true;
}
function closeCustomDlg() {
  showCustomDlg.value = false;
}
function confirmCustomDlg() {
  const v = Number(customShard.value || 0);
  if (v > 0) shardAll(v);
}
function toggleWin(id) {
  if (wiz.winners[id]) {
    delete wiz.winners[id];
    wiz.pts[id] = 0;
  } else {
    wiz.winners[id] = true;
  }
}
function split() {
  const total = Number(splitTotal.value || 0);
  const wins = wiz.players.filter((id) => wiz.winners[id]);
  if (!total || !wins.length) {
    toastText("请先标记冠军并输入总分");
    return;
  }
  const each = Math.floor(total / wins.length);
  let rem = total - each * wins.length;
  wins.forEach((id, i) => {
    wiz.pts[id] = each + (i === 0 ? rem : 0);
  });
  toastText("已均分给 " + wins.length + " 位赢家");
}
async function submit() {
  msg.value = "";
  if (totalPts.value === 0 && totalSh.value === 0 && totalGifts.value === 0) {
    showZeroRewardDlg.value = true;
    return;
  }
  await doSubmit();
}
function closeZeroRewardDlg() {
  showZeroRewardDlg.value = false;
}
async function confirmZeroSubmit() {
  showZeroRewardDlg.value = false;
  await doSubmit();
}
async function doSubmit() {
  submitting.value = true;
  try {
    const rec = await api("/staff/games", {
      method: "POST",
      body: {
        projectId: wiz.projectId,
        tableId: wiz.tableId,
        players: wiz.players.map((id) => ({
          uid: id,
          pts: Number(wiz.pts[id] || 0),
          sh: Number(wiz.shr[id] || 0),
          cards: giftList(id),
        })),
        winners: wiz.players.filter((id) => wiz.winners[id]),
        event: wiz.event,
        round: (wiz.round || "").trim(),
      },
    });
    clearGameDraft();
    wiz.last = {
      pid: wiz.projectId,
      tid: wiz.tableId,
      players: [...wiz.players],
      n: wiz.players.length,
      tp: totalPts.value,
      ts: totalSh.value,
      tg: totalGifts.value,
      champ: !!(wiz.event && winCount.value),
      pname: rec.pname,
    };
    wiz.step = 5;
  } catch (e) {
    msg.value = e.message;
  } finally {
    submitting.value = false;
  }
}
function saveAndTodo() {
  saveGameDraft(JSON.parse(JSON.stringify(wiz)));
  resetWiz(0);
  go("/pages/s/todo", true);
}
function reuse() {
  const last = wiz.last;
  const players = [...(last?.players?.length ? last.players : wiz.players)];
  const shr = {};
  const pts = {};
  const gifts = {};
  players.forEach((id) => {
    shr[id] = 0;
    pts[id] = 0;
    gifts[id] = {};
  });
  Object.assign(wiz, {
    step: 3,
    projectId: last.pid,
    tableId: last.tid,
    players,
    shr,
    pts,
    gifts,
    winners: {},
    event: "",
    eventTouched: false,
    round: "",
    last: null,
  });
  splitTotal.value = "";
  customShard.value = "";
  msg.value = "";
}
function hasDraft() {
  const d = loadGameDraft();
  return d && d.step >= 1 && d.step <= 4;
}
</script>

<template>
  <page-meta :page-style="`overflow:${dlgOpen ? 'hidden' : 'visible'}`" />
  <app-toast />
  <view class="pbody">
    <!-- 开始 -->
    <view v-if="wiz.step === 0" class="card game-start">
      <view class="game-start-icon">
        <app-icon name="game" tone="slate" size="xl" shape="round" />
      </view>
      <view class="game-start-title">录入对局</view>
      <view class="tiny game-start-sub">选项目 → 选玩家 → 填分数 → 确认提交</view>
      <button class="btn block grad-dark" @tap="startWiz">开始录入</button>
    </view>

    <!-- 成功 -->
    <view v-else-if="wiz.step === 5">
      <view class="payok">
        <view class="ring">✓</view>
        <view style="font-size:17px;font-weight:600">提交成功，奖励已发放</view>
        <view class="tiny" style="margin-top:4px">{{ wiz.last.n }} 人 · 积分 {{ fmt(wiz.last.tp) }} · 碎片 {{ fmt(wiz.last.ts) }}<text v-if="wiz.last.tg"> · 赠卡 {{ fmt(wiz.last.tg) }}</text></view>
        <view class="tiny">会员立即可见<text v-if="wiz.last.champ"> · 冠军已记入荣誉</text></view>
      </view>
      <button class="btn block" style="margin-top:14px" @tap="reuse">再录一局（沿用项目、桌台与玩家）</button>
      <button class="btn ghost block" style="margin-top:8px" @tap="go('/pages/s/todo', true)">返回待办</button>
    </view>

    <view v-else>
      <view class="wiz-step">
        <template v-for="n in 4" :key="n">
          <view class="sdot" :class="{ on: wiz.step === n, done: wiz.step > n }">{{ wiz.step > n ? "✓" : n }}</view>
          <view v-if="n < 4" class="sln" />
        </template>
      </view>

      <!-- 1 项目桌台 -->
      <view v-if="wiz.step === 1">
        <view v-if="quickCombos.length" class="card" style="background:#EAF3DE;border-color:#97C459;padding:10px 12px">
          <view class="tiny" style="color:#3B6D11;margin-bottom:6px">常用组合 · 已选项目与桌台，跳到选玩家</view>
          <view class="row" style="flex-wrap:wrap">
            <button
              v-for="c in quickCombos"
              :key="c.pid + '-' + c.tid"
              class="pill"
              style="background:#fff;border:1px solid #97C459;color:#04342C"
              @tap="combo(c.pid, c.tid)"
            >{{ c.label }}</button>
          </view>
        </view>
        <view class="h2">选择项目</view>
        <view class="g3" style="flex-wrap:wrap;margin-bottom:14px">
          <view
            v-for="p in meta.projects"
            :key="p.id"
            class="icell"
            :class="{ on: wiz.projectId === p.id }"
            @tap="wiz.projectId = p.id"
          >
            <view class="icell-i" />
            {{ p.name }}
          </view>
        </view>
        <view class="sec-head">
          <text>选择桌台</text>
          <text class="hint">选填 · 可跳过</text>
        </view>
        <view class="g4">
          <view
            v-for="t in meta.tables"
            :key="t.id"
            class="icell"
            :class="{ on: wiz.tableId === t.id }"
            style="padding:9px 2px"
            @tap="wiz.tableId = wiz.tableId === t.id ? null : t.id"
          >
            <view style="font-size:13px;font-weight:600">{{ t.name }}</view>
            <view class="tiny" :style="{ color: busy(t.id) ? '#A32D2D' : '#9C9A93' }">{{ busy(t.id) ? "占用" : "空" }}</view>
          </view>
        </view>
        <view class="sec-head" style="margin-top:12px">
          <text>局次</text>
          <text class="hint">选填</text>
        </view>
        <input class="round-input" v-model="wiz.round" placeholder="第 3 局" />
        <view class="wiz-nav" style="margin-top:12px">
          <button class="btn ghost wiz-nav-back" @tap="goBack">取消</button>
          <button class="btn wiz-primary wiz-nav-next" :disabled="!wiz.projectId" @tap="next">下一步 · 选玩家</button>
        </view>
      </view>

      <!-- 2 选玩家 -->
      <view v-if="wiz.step === 2" class="step2-layout">
        <view class="step2-top">
          <view v-if="project" class="card" style="background:#FAF9F5;padding:10px 12px;margin-bottom:12px">
            <view class="tiny">已选 {{ project.name }}{{ table ? " · " + table.name : "" }}{{ wiz.round ? " · " + wiz.round : "" }}，请选择参与玩家</view>
          </view>
          <view class="card" style="border-color:#1C1B19;padding:11px 12px">
            <view class="pick-summary">
              <text class="pick-count">已选 {{ wiz.players.length }} 人</text>
              <text class="pick-warn" v-if="peopleWarn">{{ peopleWarn }}</text>
            </view>
            <view class="row" style="flex-wrap:wrap;gap:8px" v-if="pickedUsers.length">
              <view v-for="x in pickedUsers" :key="x.id" class="pick-chip">
                <view class="pick-chip-av">{{ x.av }}</view>
                <view class="tiny">{{ x.nick }} <text style="color:#A32D2D" @tap="toggle(x.id)">×</text></view>
              </view>
            </view>
            <view class="tiny" v-else>尚未选择玩家</view>
          </view>
          <view class="sec-head">
            <text>今日到店会员</text>
            <text class="hint">点选即添加</text>
          </view>
        </view>
        <scroll-view scroll-y class="member-scroll" :show-scrollbar="false">
          <view class="member-grid">
            <view
              v-for="x in members"
              :key="x.id"
              class="member-pick"
              :class="{ on: wiz.players.includes(x.id) }"
              @tap="toggle(x.id)"
            >
              <view class="member-av">{{ x.av }}</view>
              <text class="member-name">{{ x.nick }}</text>
            </view>
          </view>
        </scroll-view>
        <view class="step2-foot">
          <input class="wiz-search" v-model="search" placeholder="搜索昵称 / 手机后 4 位 / 会员号…" />
          <view class="card" v-if="search && found.length" style="padding:6px 12px;margin-bottom:8px">
            <view class="li" v-for="x in found" :key="x.id" @tap="toggle(x.id)">
              <view class="av" style="width:26px;height:26px">{{ x.av }}</view>
              <view class="gr"><view style="font-weight:500">{{ x.nick }}</view><view class="tiny">{{ x.no }}</view></view>
              <text class="tiny">添加</text>
            </view>
          </view>
          <view class="wiz-nav">
            <button class="btn ghost wiz-nav-back" @tap="goBack">上一步</button>
            <button class="btn wiz-primary wiz-nav-next" :disabled="!wiz.players.length" @tap="next">下一步 · 填分</button>
          </view>
        </view>
      </view>

      <!-- 3 填分 -->
      <view v-if="wiz.step === 3">
        <view class="card" style="background:#EEEDFE;border-color:#534AB7">
          <view class="sec-head" style="color:#26215C;margin-bottom:7px">
            <text>全员碎片</text>
            <text class="hint purple">一键铺满 · 快捷值由门店设置</text>
          </view>
          <view class="row shard-row">
            <button
              v-for="v in quick"
              :key="v"
              class="shard-btn"
              :class="{ on: activeQuickShard === v }"
              @tap="shardAll(v)"
            >{{ v }}</button>
            <button class="shard-btn custom" :class="{ on: activeQuickShard === 'custom' }" @tap="openCustomDlg">自定义</button>
          </view>
        </view>
        <view class="sec-head">
          <text>玩家奖励</text>
          <text class="hint">奖杯 = 标记冠军</text>
        </view>
        <view
          v-for="x in pickedUsers"
          :key="x.id"
          class="card player-score-card"
          :class="{ champ: wiz.winners[x.id] }"
        >
          <view class="player-score-top">
            <view class="av player-score-av" :class="{ champ: wiz.winners[x.id] }">{{ x.av }}</view>
            <view class="player-score-name">
              <view class="player-score-nick">{{ x.nick }}</view>
              <view class="tiny gold" v-if="wiz.winners[x.id]">冠军</view>
            </view>
            <view class="cup-btn" :class="{ on: wiz.winners[x.id] }" @tap="toggleWin(x.id)">🏆</view>
          </view>
          <view class="player-score-fields">
            <view class="player-score-field">
              <view class="tiny field-label">碎片</view>
              <input
                class="wiz-num-input"
                type="number"
                :value="wiz.shr[x.id] || 0"
                @input="wiz.shr[x.id] = Number($event.detail.value || 0)"
              />
            </view>
            <view class="player-score-field wide">
              <view class="tiny field-label">积分</view>
              <input
                class="wiz-num-input"
                type="number"
                :value="wiz.pts[x.id] || 0"
                @input="wiz.pts[x.id] = Number($event.detail.value || 0)"
              />
            </view>
            <button
              class="gift-btn"
              :class="{ on: giftCount(x.id) > 0 }"
              @tap="openGiftDlg(x)"
            >{{ giftCount(x.id) > 0 ? "卡 " + giftCount(x.id) : "赠卡" }}</button>
          </view>
        </view>
        <view class="card split-card">
          <view class="split-row">
            <text class="split-label">冠军总分均分</text>
            <input class="split-input" type="number" v-model="splitTotal" placeholder="输入总分" />
            <button class="btn ghost split-action" @tap="split">均分</button>
          </view>
        </view>
        <view class="wiz-nav">
          <button class="btn ghost wiz-nav-back" @tap="goBack">上一步</button>
          <button class="btn wiz-primary wiz-nav-next" :disabled="!wiz.players.length" @tap="next">下一步 · 确认</button>
        </view>
      </view>

      <!-- 4 确认 -->
      <view v-if="wiz.step === 4">
        <view class="card">
          <view class="h2">对局汇总</view>
          <view class="li"><view class="gr"><view style="font-weight:500">项目 / 桌台</view><view class="tiny">桌台为选填项</view></view><text style="font-weight:600">{{ project?.name }}{{ table ? " · " + table.name + " 桌" : "" }}{{ wiz.round ? " · " + wiz.round : "" }}</text></view>
          <view class="li"><view class="gr"><view style="font-weight:500">时间</view></view><text style="font-weight:600">{{ confirmTime || nowTimeLabel() }}</text></view>
          <view class="li"><view class="gr"><view style="font-weight:500">参与人数</view></view><text style="font-weight:600">{{ wiz.players.length }} 人</text></view>
          <view class="li"><view class="gr"><view style="font-weight:500">积分总额</view><view class="tiny">{{ winCount }} 名冠军</view></view><text style="font-weight:600;color:#185FA5">{{ fmt(totalPts) }}</text></view>
          <view class="li" style="border:none"><view class="gr"><view style="font-weight:500">碎片总额</view></view><text style="font-weight:600;color:#534AB7">{{ fmt(totalSh) }}</text></view>
        </view>
        <view class="card" style="background:#FAF9F5">
          <view class="event-label">
            <text class="tiny">赛事名称（已按录入时间自动取名，可直接修改）</text>
            <text v-if="wiz.eventTouched" class="event-reset" @tap="restoreEventDefault">恢复默认</text>
          </view>
          <input class="event-input" v-model="wiz.event" @input="wiz.eventTouched = true" />
        </view>
        <view class="card">
          <view class="h2">逐人明细</view>
          <view class="li" v-for="x in pickedUsers" :key="x.id">
            <view class="av" style="width:24px;height:24px;font-size:11px" :style="wiz.winners[x.id] ? 'background:#BA7517;color:#fff' : ''">{{ x.av }}</view>
            <view class="gr">
              <view style="font-weight:500">{{ x.nick }}</view>
              <view class="tiny">{{ wiz.winners[x.id] ? "冠军 · " : "" }}{{ x.teamName || "无战队" }}<text v-if="giftCount(x.id)"> · 赠卡 {{ giftCount(x.id) }} 张</text></view>
            </view>
            <view style="text-align:right">
              <view style="font-size:12px;font-weight:600">{{ wiz.pts[x.id] ? "+" + fmt(wiz.pts[x.id]) + " 分" : "0 分" }}</view>
              <view class="tiny" style="color:#534AB7">+{{ fmt(wiz.shr[x.id] || 0) }} 碎片</view>
            </view>
          </view>
        </view>
        <view class="card" style="background:#FCEBEB;border-color:#E24B4A;padding:10px 12px">
          <view class="tiny" style="color:#A32D2D;line-height:1.7"><text style="font-weight:600">提交后立即入账，用户可见。</text>录错需由店长在电脑端作废，作废记入日志（赠卡未使用部分一并回滚）。</view>
        </view>
        <button class="btn block wiz-primary" style="margin-bottom:8px" :disabled="submitting" @tap="submit">确认提交</button>
        <view class="wiz-nav">
          <button class="btn ghost wiz-nav-back" @tap="goBack">上一步</button>
          <button class="btn ghost wiz-nav-next" @tap="saveAndTodo">存草稿</button>
        </view>
      </view>
    </view>

    <view class="err" v-if="msg">{{ msg }}</view>
    <tab-bar current="game" />

    <view v-if="showDraftDlg" class="draft-mask" @tap="closeDraftDlg" @touchmove.stop.prevent>
      <view class="draft-dialog" @tap.stop>
        <view class="draft-title">恢复草稿</view>
        <view class="draft-body">检测到一局未提交的草稿（24 小时内有效），是否继续？</view>
        <view class="draft-actions">
          <button class="btn ghost draft-btn" @tap="closeDraftDlg">取消</button>
          <button class="btn draft-btn" @tap="confirmDraftDlg">继续录入</button>
        </view>
      </view>
    </view>

    <view v-if="showCustomDlg" class="draft-mask" @tap="closeCustomDlg" @touchmove.stop.prevent>
      <view class="draft-dialog" @tap.stop>
        <view class="draft-title">自定义碎片值</view>
        <input
          class="dlg-input"
          type="number"
          v-model="customShard"
          placeholder="输入碎片值"
          :focus="showCustomDlg"
        />
        <view class="draft-actions">
          <button class="btn ghost draft-btn" @tap="closeCustomDlg">取消</button>
          <button class="btn draft-btn" @tap="confirmCustomDlg">铺满全员</button>
        </view>
      </view>
    </view>

    <view v-if="showExitDlg" class="draft-mask" @tap="closeExitDlg" @touchmove.stop.prevent>
      <view class="draft-dialog" @tap.stop>
        <view class="draft-title">返回首页</view>
        <view class="draft-body">当前进度将保存为草稿，下次可继续录入。</view>
        <view class="draft-actions">
          <button class="btn ghost draft-btn" @tap="closeExitDlg">继续录入</button>
          <button class="btn draft-btn" @tap="confirmExitWiz">返回首页</button>
        </view>
      </view>
    </view>

    <view v-if="showGiftDlg" class="draft-mask" @tap="closeGiftDlg" @touchmove.stop.prevent>
      <view class="gift-dialog" @tap.stop>
        <view class="draft-title">赠送卡券{{ giftTarget ? " · " + giftTarget.nick : "" }}</view>
        <scroll-view scroll-y class="gift-scroll">
          <view v-if="!giftTplGroups.length" class="tiny" style="padding:20px 0;text-align:center">暂无可用卡券模板</view>
          <view v-for="g in giftTplGroups" :key="g.key" class="gift-group">
            <view class="gift-cat">{{ g.label }}</view>
            <view v-for="t in g.items" :key="t.id" class="gift-row">
              <view class="gr" style="min-width:0;flex:1">
                <view class="gift-name">{{ t.name }}</view>
                <view class="tiny">有效期 {{ t.days || 30 }} 天</view>
              </view>
              <view class="gift-stepper">
                <view class="gift-step" @tap="setDraftQty(t.id, draftQty(t.id) - 1)">−</view>
                <text class="gift-qty">{{ draftQty(t.id) }}</text>
                <view class="gift-step" @tap="setDraftQty(t.id, draftQty(t.id) + 1)">+</view>
              </view>
            </view>
          </view>
        </scroll-view>
        <view class="draft-actions">
          <button class="btn ghost draft-btn" @tap="closeGiftDlg">取消</button>
          <button class="btn draft-btn" @tap="confirmGiftDlg">确定</button>
        </view>
      </view>
    </view>

    <view v-if="showZeroRewardDlg" class="draft-mask" @tap="closeZeroRewardDlg" @touchmove.stop.prevent>
      <view class="draft-dialog" @tap.stop>
        <view class="draft-title">确认提交</view>
        <view class="draft-body">本局无任何奖励，确认提交？</view>
        <view class="draft-actions">
          <button class="btn ghost draft-btn" :disabled="submitting" @tap="closeZeroRewardDlg">再想想</button>
          <button class="btn draft-btn" :disabled="submitting" @tap="confirmZeroSubmit">
            {{ submitting ? "提交中…" : "确认提交" }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.game-start {
  text-align: center;
  padding: 28px 16px 22px;
  background: linear-gradient(180deg, #fff 0%, #f7f6f2 100%);
}
.game-start-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}
.game-start-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.game-start-sub {
  margin: 0 0 16px;
  line-height: 1.6;
}
.event-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.event-reset {
  color: #185FA5;
  font-size: 11px;
  flex-shrink: 0;
}
.event-input {
  width: 100%;
  height: 40px;
  min-height: 40px;
  line-height: 40px;
  padding: 0 10px;
  margin: 0;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 13px;
  color: #1c1b19;
}
.draft-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 30px;
  background: rgba(0, 0, 0, 0.35);
}
.draft-dialog {
  width: 84%;
  max-width: 320px;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
}
.draft-title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1b19;
  margin-bottom: 9px;
}
.draft-body {
  font-size: 12.5px;
  color: #6b6a65;
  line-height: 1.7;
  margin-bottom: 13px;
}
.draft-actions {
  display: flex;
  gap: 8px;
}
.draft-btn {
  flex: 1;
  margin: 0;
}
.draft-actions .btn + .btn {
  margin-left: 0;
}
.dlg-input {
  width: 100%;
  height: 40px;
  min-height: 40px;
  line-height: 40px;
  padding: 0 10px;
  margin: 0 0 13px;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 13px;
  color: #1c1b19;
}
.split-card {
  background: #faf9f5;
  padding: 10px 12px;
}
.split-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.split-label {
  flex-shrink: 0;
  font-size: 11px;
  color: #9c9a93;
}
.split-input {
  flex: 1;
  min-width: 0;
  width: auto;
  max-width: 120px;
  height: 36px;
  min-height: 36px;
  line-height: 36px;
  padding: 0 10px;
  margin: 0 0 0 auto;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 13px;
  color: #1c1b19;
}
.split-action {
  flex-shrink: 0;
  padding: 6px 11px;
  margin: 0;
  line-height: 1.2;
}
button.wiz-primary {
  background: #1c1b19;
  color: #fff;
  font-weight: 600;
}
button.wiz-primary[disabled] {
  opacity: 0.4;
}
.wiz-nav {
  display: flex;
  gap: 8px;
}
.wiz-nav .btn {
  flex: 1;
  margin: 0;
}
.wiz-nav-back {
  flex: 0 0 88px;
}
.wiz-nav-next {
  flex: 1;
}
.round-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
  color: #1c1b19;
  box-sizing: border-box;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1c1b19;
}
.sec-head .hint {
  margin-left: auto;
  font-size: 11px;
  color: #9c9a93;
  font-weight: 400;
}
.sec-head .hint.purple {
  color: #534ab7;
}
.pick-summary {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}
.pick-count {
  font-size: 13px;
  font-weight: 600;
  color: #1c1b19;
}
.pick-warn {
  margin-left: auto;
  font-size: 11px;
  color: #ba7517;
  text-align: right;
  line-height: 1.4;
}
.pick-chip {
  text-align: center;
}
.pick-chip-av {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #1c1b19;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  margin: 0 auto 2px;
}
.member-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding-bottom: 4px;
}
.step2-layout {
  display: flex;
  flex-direction: column;
}
.step2-top {
  flex-shrink: 0;
}
.member-scroll {
  height: 420rpx;
  margin-bottom: 8px;
}
.step2-foot {
  flex-shrink: 0;
}
.member-pick {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.member-av {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8e6df, #d8d5cc);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  letter-spacing: -0.5px;
  color: #6b6a65;
  margin-bottom: 3px;
}
.member-pick.on .member-av {
  background: #1c1b19;
  color: #fff;
}
.member-name {
  font-size: 11px;
  color: #6b6a65;
  line-height: 1.3;
}
.wiz-search {
  width: 100%;
  height: 40px;
  min-height: 40px;
  line-height: 40px;
  padding: 0 10px;
  margin: 0 0 8px;
  box-sizing: border-box;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 13px;
  color: #1c1b19;
}
.shard-row {
  gap: 6px;
}
button.shard-btn {
  flex: 1;
  margin: 0;
  padding: 10px 6px;
  border: 1px solid #534ab7;
  border-radius: 10px;
  background: transparent;
  color: #534ab7;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}
button.shard-btn.custom {
  flex: 1.2;
}
button.shard-btn.on {
  background: #534ab7;
  color: #fff;
  border-color: #534ab7;
}
.player-score-card {
  padding: 11px 12px;
  margin-bottom: 8px;
}
.player-score-card.champ {
  border-color: #ba7517;
  background: #faeeda;
}
.player-score-top {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 10px;
}
.player-score-av {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  font-size: 11px;
}
.player-score-av.champ {
  background: #ba7517;
  color: #fff;
}
.player-score-name {
  flex: 1;
  min-width: 0;
}
.player-score-nick {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
}
.player-score-fields {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.player-score-field {
  width: 58px;
  flex-shrink: 0;
}
.player-score-field.wide {
  width: 72px;
}
.field-label {
  display: block;
  width: 100%;
  text-align: center;
  line-height: 1.2;
  margin-bottom: 2px;
  color: #9c9a93;
  font-size: 11px;
}
.cup-btn {
  width: 28px;
  height: 28px;
  margin-left: auto;
  border-radius: 7px;
  background: #fff;
  border: 1px solid rgba(28, 27, 25, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 13px;
  line-height: 1;
  opacity: 0.55;
}
.cup-btn.on {
  background: #ba7517;
  border-color: #ba7517;
  opacity: 1;
}
.gift-btn {
  flex: 1;
  min-width: 64px;
  height: 34px;
  line-height: 34px;
  margin: 0;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.18);
  background: #fff;
  color: #1c1b19;
  font-size: 12px;
  font-weight: 500;
}
.gift-btn.on {
  border-color: #185fa5;
  color: #185fa5;
  background: #e6f1fb;
}
.gift-dialog {
  width: 88%;
  max-width: 360px;
  max-height: 78vh;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}
.gift-scroll {
  max-height: 52vh;
  margin: 10px 0 12px;
}
.gift-group {
  margin-bottom: 10px;
}
.gift-cat {
  font-size: 12px;
  font-weight: 600;
  color: #6b6a65;
  margin-bottom: 6px;
}
.gift-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(28, 27, 25, 0.06);
}
.gift-name {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
}
.gift-stepper {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.gift-step {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid rgba(28, 27, 25, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  background: #faf9f5;
}
.gift-qty {
  min-width: 22px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
}
.wiz-num-input {
  display: block;
  width: 100%;
  height: 32px;
  min-height: 32px;
  line-height: 32px;
  padding: 0 4px;
  margin: 0;
  box-sizing: border-box;
  border-radius: 6px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 13px;
  text-align: center;
  color: #1c1b19;
}
</style>

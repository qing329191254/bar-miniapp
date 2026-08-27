<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { api, clearGameDraft, go, loadGameDraft, saveGameDraft } from "@/utils/api";

const meta = ref({ projects: [], tables: [], busy: [] });
const members = ref([]);
const search = ref("");
const splitTotal = ref("");
const customShard = ref("");
const showCustom = ref(false);
const msg = ref("");
const submitting = ref(false);

const wiz = reactive({
  step: 0,
  projectId: null,
  tableId: null,
  players: [],
  shr: {},
  pts: {},
  winners: {},
  event: "",
  eventTouched: false,
  last: null,
});

onMounted(async () => {
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
const totalPts = computed(() => wiz.players.reduce((s, id) => s + Number(wiz.pts[id] || 0), 0));
const totalSh = computed(() => wiz.players.reduce((s, id) => s + Number(wiz.shr[id] || 0), 0));
const winCount = computed(() => wiz.players.filter((id) => wiz.winners[id]).length);
const peopleWarn = computed(() => {
  const pj = project.value;
  if (!pj || !pj.min) return "";
  if (wiz.players.length < pj.min || wiz.players.length > pj.max) {
    return `${pj.name} 通常 ${pj.min}-${pj.max} 人（提示不阻断）`;
  }
  return "";
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

function startWiz() {
  const d = loadGameDraft();
  if (d && d.step >= 1 && d.step <= 4) {
    Object.assign(wiz, d);
    msg.value = "";
    return;
  }
  Object.assign(wiz, {
    step: 1, projectId: null, tableId: null, players: [], shr: {}, pts: {}, winners: {}, event: "", eventTouched: false, last: null,
  });
}
function restoreDraft() {
  const d = loadGameDraft();
  if (!d) return;
  Object.assign(wiz, d);
}
function combo(pid, tid) {
  Object.assign(wiz, {
    step: 3, projectId: pid, tableId: tid, players: [], shr: {}, pts: {}, winners: {}, event: "", eventTouched: false, last: null,
  });
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
  if (wiz.step === 4 && !wiz.eventTouched) wiz.event = defaultEvent();
}
function toggle(id) {
  const i = wiz.players.indexOf(id);
  if (i >= 0) {
    wiz.players.splice(i, 1);
    delete wiz.shr[id];
    delete wiz.pts[id];
    delete wiz.winners[id];
  } else {
    wiz.players.push(id);
    wiz.shr[id] = 0;
    wiz.pts[id] = 0;
  }
}
function shardAll(v) {
  wiz.players.forEach((id) => {
    wiz.shr[id] = v;
  });
  showCustom.value = false;
}
function applyCustom() {
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
    msg.value = "请先标记冠军并输入总分";
    return;
  }
  const each = Math.floor(total / wins.length);
  let rem = total - each * wins.length;
  wins.forEach((id, i) => {
    wiz.pts[id] = each + (i === 0 ? rem : 0);
  });
  msg.value = "已均分给 " + wins.length + " 位赢家";
}
async function submit() {
  msg.value = "";
  if (totalPts.value === 0 && totalSh.value === 0) {
    const ok = await new Promise((resolve) => {
      uni.showModal({
        title: "确认提交",
        content: "本局无任何奖励，确认提交？",
        success: (r) => resolve(r.confirm),
      });
    });
    if (!ok) return;
  }
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
        })),
        winners: wiz.players.filter((id) => wiz.winners[id]),
        event: wiz.event,
      },
    });
    clearGameDraft();
    wiz.last = {
      pid: wiz.projectId,
      tid: wiz.tableId,
      n: wiz.players.length,
      tp: totalPts.value,
      ts: totalSh.value,
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
  go("/pages/s/todo", true);
}
function reuse() {
  const last = wiz.last;
  Object.assign(wiz, {
    step: 3, projectId: last.pid, tableId: last.tid, players: [], shr: {}, pts: {}, winners: {}, event: "", eventTouched: false, last: null,
  });
}
function hasDraft() {
  const d = loadGameDraft();
  return d && d.step >= 1 && d.step <= 4;
}
</script>

<template>
  <view class="pbody">
    <!-- 开始 -->
    <view v-if="wiz.step === 0" class="card" style="text-align:center;padding:34px 14px">
      <view style="font-size:15px;font-weight:600">录入对局</view>
      <view class="tiny" style="margin:6px 0 14px">目标：30 秒录完一局（2 次点击 + 1 次输入）</view>
      <view v-if="hasDraft()" class="card" style="background:#FAEEDA;border-color:#BA7517;text-align:left;margin-bottom:12px">
        <view class="between">
          <text style="font-size:13px;color:#BA7517;font-weight:600">有 1 局未提交</text>
          <button class="btn gold" style="padding:6px 12px;font-size:12px" @tap="restoreDraft">继续录入</button>
        </view>
      </view>
      <button class="btn block" @tap="startWiz">开始录入</button>
    </view>

    <!-- 成功 -->
    <view v-else-if="wiz.step === 5">
      <view class="payok">
        <view class="ring">✓</view>
        <view style="font-size:17px;font-weight:600">提交成功，已立即入账</view>
        <view class="tiny" style="margin-top:4px">{{ wiz.last.n }} 人 · 积分 {{ fmt(wiz.last.tp) }} · 碎片 {{ fmt(wiz.last.ts) }}</view>
        <view class="tiny">C 端用户立即可见{{ wiz.last.champ ? " · 冠军已记入荣誉" : "" }}</view>
      </view>
      <button class="btn block" style="margin-top:14px" @tap="reuse">再录一局（沿用项目与桌台）</button>
      <button class="btn ghost block" style="margin-top:8px" @tap="go('/pages/s/todo', true)">返回待办</button>
    </view>

    <view v-else>
      <view class="wiz-step">
        <view v-for="n in 4" :key="n" class="row" style="flex:1;gap:5px">
          <view class="sdot" :class="{ on: wiz.step === n, done: wiz.step > n }">{{ wiz.step > n ? "✓" : n }}</view>
          <view class="sln" v-if="n < 4" />
        </view>
      </view>

      <!-- 1 项目桌台 -->
      <view v-if="wiz.step === 1">
        <view class="card" style="background:#EAF3DE;border-color:#97C459;padding:10px 12px">
          <view class="tiny" style="color:#3B6D11;margin-bottom:6px">常用组合 · 点击直接跳到填分</view>
          <view class="row" style="flex-wrap:wrap">
            <button class="pill" style="background:#fff;border:1px solid #97C459;color:#04342C" @tap="combo(1,3)">狼人杀 · A3 桌</button>
            <button class="pill" style="background:#fff;border:1px solid #97C459;color:#04342C" @tap="combo(2,6)">德扑 · 卡座1</button>
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
        <view class="h2">选择桌台 <text class="tiny">选填 · 可跳过</text></view>
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
        <button class="btn block" style="margin-top:12px" :disabled="!wiz.projectId" @tap="next">下一步 · 选玩家</button>
      </view>

      <!-- 2 选玩家 -->
      <view v-if="wiz.step === 2">
        <view class="card" style="border-color:#1C1B19;padding:11px 12px">
          <view class="row" style="margin-bottom:8px">
            <text style="font-size:13px;font-weight:600">已选 {{ wiz.players.length }} 人</text>
            <text class="tiny gold" v-if="peopleWarn">{{ peopleWarn }}</text>
          </view>
          <view class="row" style="flex-wrap:wrap" v-if="pickedUsers.length">
            <view v-for="x in pickedUsers" :key="x.id" style="text-align:center">
              <view class="av" style="background:#1C1B19;color:#fff;margin:0 auto">{{ x.av }}</view>
              <view class="tiny" style="margin-top:2px">{{ x.nick }} <text style="color:#A32D2D" @tap="toggle(x.id)">×</text></view>
            </view>
          </view>
          <view class="tiny" v-else>尚未选择玩家</view>
        </view>
        <view class="h2">今日到店会员 <text class="tiny">点选即添加</text></view>
        <view class="av-grid">
          <view
            v-for="x in members.slice(0, 16)"
            :key="x.id"
            class="av-pick"
            :class="{ on: wiz.players.includes(x.id) }"
            @tap="toggle(x.id)"
          >
            <view class="av">{{ x.av }}</view>
            <text>{{ x.nick }}</text>
          </view>
        </view>
        <input class="field" v-model="search" placeholder="搜索昵称 / 手机后 4 位 / 会员号…" />
        <view class="card" v-if="search && found.length" style="padding:6px 12px">
          <view class="li" v-for="x in found" :key="x.id" @tap="toggle(x.id)">
            <view class="av" style="width:26px;height:26px">{{ x.av }}</view>
            <view class="gr"><view style="font-weight:500">{{ x.nick }}</view><view class="tiny">{{ x.no }}</view></view>
            <text class="tiny">添加</text>
          </view>
        </view>
        <button class="btn block" :disabled="!wiz.players.length" @tap="next">下一步 · 填分</button>
      </view>

      <!-- 3 填分 -->
      <view v-if="wiz.step === 3">
        <view class="card" style="background:#EEEDFE;border-color:#534AB7">
          <view class="h2" style="color:#26215C">全员碎片 <text class="tiny" style="color:#534AB7">一键铺满 · 快捷值取自项目配置</text></view>
          <view class="row">
            <button
              v-for="v in quick"
              :key="v"
              class="btn ghost"
              style="flex:1;color:#534AB7;border-color:#534AB7"
              :style="v === project?.shard ? 'background:#534AB7;color:#fff;border-color:#534AB7' : ''"
              @tap="shardAll(v)"
            >{{ v }}</button>
            <button class="btn ghost" style="flex:1.2;color:#534AB7;border-color:#534AB7" @tap="showCustom = !showCustom">自定义</button>
          </view>
          <view class="row" v-if="showCustom" style="margin-top:8px">
            <input class="field" style="margin:0;flex:1" type="number" v-model="customShard" placeholder="碎片值" />
            <button class="btn" @tap="applyCustom">铺满</button>
          </view>
        </view>
        <view class="h2">玩家分数 <text class="tiny">点奖杯标记冠军</text></view>
        <view
          v-for="x in pickedUsers"
          :key="x.id"
          class="card"
          :style="wiz.winners[x.id] ? 'border-color:#BA7517;background:#FAEEDA;padding:11px 12px;margin-bottom:8px' : 'padding:11px 12px;margin-bottom:8px'"
        >
          <view class="row">
            <view class="av" :style="wiz.winners[x.id] ? 'background:#BA7517;color:#fff' : ''">{{ x.av }}</view>
            <view style="margin-left:9px;flex:1">
              <view style="font-size:13px;font-weight:600">{{ x.nick }}</view>
              <view class="tiny gold" v-if="wiz.winners[x.id]">冠军</view>
            </view>
            <view style="text-align:right">
              <view class="tiny">碎片</view>
              <input class="field" style="width:50px;margin:0;text-align:right" type="number" :value="wiz.shr[x.id] || 0" @input="wiz.shr[x.id] = Number($event.detail.value || 0)" />
            </view>
            <view style="text-align:right;margin-left:8px">
              <view class="tiny">积分</view>
              <input class="field" style="width:62px;margin:0;text-align:right" type="number" :value="wiz.pts[x.id] || 0" @input="wiz.pts[x.id] = Number($event.detail.value || 0)" />
            </view>
            <view class="cup" :class="{ on: wiz.winners[x.id] }" @tap="toggleWin(x.id)">冠</view>
          </view>
        </view>
        <view class="card" style="background:#FAF9F5;padding:10px 12px">
          <view class="row">
            <text class="tiny">冠军总分均分</text>
            <input class="field" style="max-width:110px;margin:0 0 0 auto" type="number" v-model="splitTotal" placeholder="输入总分" />
            <button class="btn ghost" style="padding:6px 11px" @tap="split">均分</button>
          </view>
        </view>
        <button class="btn block" :disabled="!wiz.players.length" @tap="next">下一步 · 确认</button>
      </view>

      <!-- 4 确认 -->
      <view v-if="wiz.step === 4">
        <view class="card">
          <view class="h2">对局汇总</view>
          <view class="li"><view class="gr"><view style="font-weight:500">项目 / 桌台</view><view class="tiny">桌台为选填项</view></view><text style="font-weight:600">{{ project?.name }}{{ table ? " · " + table.name + " 桌" : "" }}</text></view>
          <view class="li"><view class="gr"><view style="font-weight:500">参与人数</view></view><text style="font-weight:600">{{ wiz.players.length }} 人</text></view>
          <view class="li"><view class="gr"><view style="font-weight:500">积分总额</view><view class="tiny">{{ winCount }} 名冠军</view></view><text style="font-weight:600;color:#185FA5">{{ fmt(totalPts) }}</text></view>
          <view class="li" style="border:none"><view class="gr"><view style="font-weight:500">碎片总额</view></view><text style="font-weight:600;color:#534AB7">{{ fmt(totalSh) }}</text></view>
        </view>
        <view class="card" style="background:#FAF9F5">
          <view class="tiny">赛事名称（已按录入时间自动取名，可直接修改）</view>
          <input class="field" v-model="wiz.event" @input="wiz.eventTouched = true" />
        </view>
        <view class="card">
          <view class="h2">逐人明细</view>
          <view class="li" v-for="x in pickedUsers" :key="x.id">
            <view class="av" style="width:24px;height:24px;font-size:11px" :style="wiz.winners[x.id] ? 'background:#BA7517;color:#fff' : ''">{{ x.av }}</view>
            <view class="gr">
              <view style="font-weight:500">{{ x.nick }}</view>
              <view class="tiny">{{ wiz.winners[x.id] ? "冠军 · " : "" }}{{ x.teamName || "无战队" }}</view>
            </view>
            <view style="text-align:right">
              <view style="font-size:12px;font-weight:600">{{ wiz.pts[x.id] ? "+" + fmt(wiz.pts[x.id]) + " 分" : "0 分" }}</view>
              <view class="tiny" style="color:#534AB7">+{{ fmt(wiz.shr[x.id] || 0) }} 碎片</view>
            </view>
          </view>
        </view>
        <view class="card" style="background:#FCEBEB;border-color:#E24B4A;padding:10px 12px">
          <view class="tiny" style="color:#A32D2D;line-height:1.7"><text style="font-weight:600">提交后立即入账，用户可见。</text>录错需由店长在电脑端作废，作废记入日志。</view>
        </view>
        <button class="btn block" style="margin-bottom:8px" :disabled="submitting" @tap="submit">确认提交</button>
        <view class="row">
          <button class="btn ghost" style="flex:1" @tap="saveAndTodo">存草稿</button>
          <button class="btn ghost" style="flex:1" @tap="wiz.step = 3">返回修改</button>
        </view>
      </view>
    </view>

    <view class="err" v-if="msg">{{ msg }}</view>
    <tab-bar current="game" />
  </view>
</template>

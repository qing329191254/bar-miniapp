<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import AppSelect from "../components/AppSelect.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import DateTimePicker from "../components/DateTimePicker.vue";
import { showToast } from "../composables/useToast";

type GiftBag = Record<number, number>;
type PlayerRow = { uid: number; nick: string; no?: string; teamName?: string; pts: number; sh: number; gifts: GiftBag };

const meta = ref({ projects: [] as any[], tables: [] as any[], cardTpls: [] as any[] });
const members = ref<any[]>([]);
const search = ref("");
const searchArea = ref<HTMLElement | null>(null);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");
const giftOpen = ref(false);
const giftUid = ref<number | null>(null);
const giftDraft = ref<GiftBag>({});

function localDateTimeValue(date = new Date()) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const form = reactive({
  pid: 1,
  tid: null as number | null,
  round: "",
  time: localDateTimeValue(),
  event: "",
  eventTouched: false,
  players: [] as PlayerRow[],
  winners: {} as Record<number, boolean>,
});

const CAT_LABEL: Record<string, string> = {
  GAME: "游戏卡",
  FOOD: "酒水小食卡",
  OTHER: "其他卡券",
};

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const r = await api<any>("/staff/projects");
    meta.value = r;
    if (r.projects[0]) form.pid = r.projects[0].id;
    members.value = await api("/admin/members?pageSize=0");
    if (!form.eventTouched) form.event = defaultEvent();
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "对局录入信息加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  document.addEventListener("pointerdown", closeSearchFromOutside);
  load();
});

onBeforeUnmount(() => document.removeEventListener("pointerdown", closeSearchFromOutside));

function defaultEvent() {
  const p = meta.value.projects.find((x) => x.id === form.pid);
  const date = new Date(form.time);
  const validDate = Number.isNaN(date.getTime()) ? new Date() : date;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(validDate.getMonth() + 1)}-${pad(validDate.getDate())} ${pad(validDate.getHours())}:${pad(validDate.getMinutes())} ${p?.name || "对局"}`;
}
const hits = computed(() => {
  const kw = search.value.trim();
  if (!kw) return [];
  return members.value.filter(
    (x) => x.role === "CUSTOMER" && (x.nick.includes(kw) || String(x.tail).includes(kw) || String(x.no).includes(kw)),
  );
});
const projectOpts = computed(() =>
  meta.value.projects.map((p) => ({ value: p.id, label: p.name })),
);
const tableOpts = computed(() => [
  { value: null, label: "不指定" },
  ...meta.value.tables.map((t) => ({ value: t.id, label: t.name })),
]);
const giftTplGroups = computed(() => {
  const groups: Record<string, { key: string; label: string; items: any[] }> = {};
  for (const t of meta.value.cardTpls || []) {
    const key = t.cat || "OTHER";
    if (!groups[key]) groups[key] = { key, label: CAT_LABEL[key] || key, items: [] };
    groups[key].items.push(t);
  }
  return Object.values(groups);
});
const giftPlayer = computed(() => form.players.find((p) => p.uid === giftUid.value) || null);

function giftCount(p: PlayerRow) {
  return Object.values(p.gifts || {}).reduce((s, n) => s + Number(n || 0), 0);
}
function giftPayload(p: PlayerRow) {
  return Object.entries(p.gifts || {})
    .filter(([, q]) => Number(q) > 0)
    .map(([tpl, qty]) => ({ tpl: Number(tpl), qty: Number(qty) }));
}
function onPidChange() {
  if (!form.eventTouched) form.event = defaultEvent();
}
function onTimeChange() {
  if (!form.eventTouched) form.event = defaultEvent();
}
function added(id: number) {
  return form.players.some((p) => p.uid === id);
}
function add(u: any) {
  if (added(u.id)) return;
  const shard = meta.value.projects.find((p) => p.id === form.pid)?.shard || 0;
  form.players.push({
    uid: u.id,
    nick: u.nick,
    no: u.no,
    teamName: u.teamName,
    pts: 0,
    sh: shard,
    gifts: {},
  });
}
function closeSearch() {
  search.value = "";
}
function closeSearchFromOutside(event: PointerEvent) {
  if (search.value && !searchArea.value?.contains(event.target as Node)) closeSearch();
}
function addFromResult(u: any) {
  add(u);
  closeSearch();
}
function addFirstHit() {
  const first = hits.value.find((x) => !added(x.id));
  if (!search.value.trim()) {
    showToast("请先输入搜索关键词", true);
  } else if (!first) {
    showToast(hits.value.length ? "匹配到的会员均已添加" : "未找到匹配会员", !hits.value.length);
  } else {
    add(first);
    showToast(`已添加 ${first.nick}`);
    closeSearch();
  }
}
function addAllHits() {
  if (!search.value.trim()) {
    showToast("请先输入搜索关键词", true);
    return;
  }
  const pending = hits.value.filter((x) => !added(x.id));
  if (!pending.length) {
    showToast(hits.value.length ? "匹配到的会员均已添加" : "未找到匹配会员", !hits.value.length);
    return;
  }
  pending.forEach(add);
  showToast(`已批量添加 ${pending.length} 位玩家`);
  closeSearch();
}
function remove(uid: number) {
  form.players = form.players.filter((p) => p.uid !== uid);
  delete form.winners[uid];
}
function openGift(p: PlayerRow) {
  giftUid.value = p.uid;
  giftDraft.value = { ...(p.gifts || {}) };
  giftOpen.value = true;
}
function closeGift() {
  giftOpen.value = false;
  giftUid.value = null;
  giftDraft.value = {};
}
function draftQty(tplId: number) {
  return Number(giftDraft.value[tplId] || 0);
}
function setDraftQty(tplId: number, next: number) {
  const n = Math.max(0, Math.min(99, Number(next) || 0));
  const copy = { ...giftDraft.value };
  if (n <= 0) delete copy[tplId];
  else copy[tplId] = n;
  giftDraft.value = copy;
}
function confirmGift() {
  const p = giftPlayer.value;
  if (!p) return;
  p.gifts = { ...giftDraft.value };
  closeGift();
}
async function submit() {
  try {
    await api("/staff/games", {
      method: "POST",
      body: {
        projectId: form.pid,
        tableId: form.tid,
        players: form.players.map((p) => ({
          uid: p.uid,
          pts: p.pts,
          sh: p.sh,
          cards: giftPayload(p),
        })),
        winners: Object.keys(form.winners).filter((k) => form.winners[Number(k)]).map(Number),
        event: form.event,
        round: (form.round || "").trim(),
        time: form.time,
      },
    });
    showToast("提交成功，已入账");
    form.players = [];
    form.winners = {};
  } catch (e: any) {
    showToast(e.message, true);
  }
}
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 4, showNote: true }" @retry="load">
  <div>
    <div class="hdr game-hdr">对局结果录入 <em>记录参与玩家、成绩、积分与赠卡</em></div>
    <div class="prod-grid">
      <div>
        <div class="card">
          <div class="st">基本信息</div>
          <div class="cards game-info-grid">
            <div>
              <div class="tiny">对局项目 *</div>
              <AppSelect v-model="form.pid" :options="projectOpts" @change="onPidChange" />
            </div>
            <div>
              <div class="tiny">桌台（选填）</div>
              <AppSelect v-model="form.tid" :options="tableOpts" />
            </div>
            <div>
              <div class="tiny">局次</div>
              <input class="inp" v-model="form.round" placeholder="第 3 局" />
            </div>
            <div>
              <div class="tiny game-time-label">对局时间（精确到分钟）</div>
              <DateTimePicker v-model="form.time" @change="onTimeChange" />
            </div>
          </div>
          <div class="tiny">赛事名称</div>
          <input class="inp" v-model="form.event" @input="form.eventTouched = true" />
        </div>
        <div class="card">
          <div class="st">参与玩家 <em>已添加 {{ form.players.length }} 人</em></div>
          <div ref="searchArea" class="player-search">
            <div class="row player-search-row">
              <div class="search-input-wrap">
                <input
                  class="inp search-input"
                  placeholder="搜索昵称 / 手机尾号 / 会员号"
                  v-model="search"
                  @keydown.enter.prevent="addFirstHit"
                  @keydown.esc.prevent="closeSearch"
                />
                <button v-if="search" class="search-clear" type="button" title="清除并收起" @click="closeSearch">×</button>
              </div>
              <button class="btn ghost" type="button" @click="addFirstHit">添加</button>
              <button class="btn ghost" type="button" @click="addAllHits">批量添加</button>
            </div>
            <div v-if="search.trim()" class="search-results">
              <div class="search-results-head">
                <span>{{ hits.length ? `找到 ${hits.length} 位会员` : "没有匹配的会员" }}</span>
                <button type="button" @click="closeSearch">收起</button>
              </div>
              <div v-if="hits.length" class="search-results-list">
                <div class="li search-result" v-for="x in hits" :key="x.id" :class="{ added: added(x.id) }" @click="!added(x.id) && addFromResult(x)">
                  <div class="gr"><b>{{ x.nick }}</b><span class="tiny">{{ x.no }}</span></div>
                  <span class="tiny">{{ added(x.id) ? "已添加" : "添加" }}</span>
                </div>
              </div>
            </div>
          </div>
          <table class="tb2 player-table" data-cols="llccccc">
            <thead>
              <tr><th>玩家</th><th>战队</th><th>积分</th><th>碎片</th><th>卡券</th><th>冠军</th><th></th></tr>
            </thead>
            <tbody>
            <tr v-for="p in form.players" :key="p.uid">
              <td>
                <b>{{ p.nick }}</b>
                <div class="tiny">{{ p.no || "" }}</div>
              </td>
              <td class="tiny">{{ p.teamName || "无战队" }}</td>
              <td><input class="inp score-input" type="number" v-model.number="p.pts" /></td>
              <td><input class="inp score-input" type="number" v-model.number="p.sh" /></td>
              <td>
                <button
                  type="button"
                  class="btn sm gift-cfg"
                  :class="{ on: giftCount(p) > 0 }"
                  @click="openGift(p)"
                >{{ giftCount(p) > 0 ? `已配 ${giftCount(p)} 张` : "配置卡券" }}</button>
              </td>
              <td class="col-champ">
                <label class="champ-check">
                  <input v-model="form.winners[p.uid]" type="checkbox" class="ui-check" />
                </label>
              </td>
              <td class="tiny" style="cursor:pointer" @click="remove(p.uid)">移除</td>
            </tr>
            <tr v-if="!form.players.length">
              <td colspan="7" class="table-empty">暂无参与玩家，请搜索或从右侧快速添加</td>
            </tr>
            </tbody>
          </table>
          <div class="row" style="margin-top:11px">
            <button class="btn ghost" @click="form.players=[];form.winners={}">清空</button>
            <span class="tiny gift-hint">卡券发放后 C 端卡包立即可见 · 作废时未使用赠卡一并回滚</span>
            <button class="btn pri submit-btn" style="margin-left:auto" :disabled="!form.players.length" @click="submit">提交并入账</button>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="st">今日到店会员 <em>点击快速添加</em></div>
        <div v-if="!members.filter(m=>m.role==='CUSTOMER').length" class="list-empty">暂无到店会员</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px">
          <div
            v-for="x in members.filter(m=>m.role==='CUSTOMER').slice(0,15)"
            :key="x.id"
            class="ph"
            :style="{ opacity: added(x.id) ? .4 : 1, cursor: added(x.id) ? 'default' : 'pointer' }"
            @click="add(x)"
          >{{ x.av }}</div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="giftOpen" class="gift-mask" @click.self="closeGift">
        <div class="gift-dlg">
          <div class="st">赠送卡券 <em v-if="giftPlayer">{{ giftPlayer.nick }}</em></div>
          <div class="gift-body">
            <div v-if="!giftTplGroups.length" class="tiny" style="padding:24px;text-align:center">暂无卡券模板，请先在「卡券配置」创建</div>
            <div v-for="g in giftTplGroups" :key="g.key" class="gift-group">
              <div class="gift-cat">{{ g.label }}</div>
              <div v-for="t in g.items" :key="t.id" class="gift-row">
                <div class="gr">
                  <b style="font-weight:500">{{ t.name }}</b>
                  <span class="tiny">有效期 {{ t.days || 30 }} 天</span>
                </div>
                <div class="gift-stepper">
                  <button type="button" class="step" @click="setDraftQty(t.id, draftQty(t.id) - 1)">−</button>
                  <input class="inp qty" type="number" min="0" max="99" :value="draftQty(t.id)" @change="setDraftQty(t.id, Number(($event.target as HTMLInputElement).value))" />
                  <button type="button" class="step" @click="setDraftQty(t.id, draftQty(t.id) + 1)">+</button>
                </div>
              </div>
            </div>
          </div>
          <div class="gift-actions">
            <button class="btn ghost" type="button" @click="closeGift">取消</button>
            <button class="btn pri" type="button" @click="confirmGift">确定</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.game-hdr em{margin-left:auto;text-align:right}
.game-info-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:8px}
.game-time-label{color:var(--ink2);font-weight:500}
.player-search{position:relative;margin-bottom:10px}
.player-search-row{gap:8px}
.search-input-wrap{position:relative;flex:1;min-width:0}
.search-input{margin:0;padding-right:38px}
.search-clear{position:absolute;right:7px;top:50%;width:28px;height:28px;transform:translateY(-50%);border:0;border-radius:7px;background:transparent;color:var(--ink3);font-size:20px;line-height:1;cursor:pointer}
.search-clear:hover{background:var(--bg);color:var(--ink)}
.search-results{position:absolute;z-index:12;top:calc(100% + 8px);left:0;right:0;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 30px rgba(28,27,25,.14);overflow:hidden}
.search-results-head{display:flex;align-items:center;justify-content:space-between;padding:9px 12px;border-bottom:1px solid var(--line);background:#FAF9F5;color:var(--ink3);font-size:11px}
.search-results-head button{border:0;background:transparent;color:var(--blue);font-size:12px;cursor:pointer}
.search-results-list{max-height:min(360px,45vh);overflow:auto;padding:0 12px}
.search-result{cursor:pointer}
.search-result:hover{background:rgba(28,27,25,.035);margin:0 -12px;padding-left:12px;padding-right:12px}
.search-result.added{opacity:.45;cursor:default}
.player-table td{padding-top:7px;padding-bottom:7px}
.player-table td.col-champ{text-align:center}
.champ-check{display:inline-flex;align-items:center;justify-content:center;margin:0;cursor:pointer}
.score-input{display:block;width:72px;margin:0 auto;padding:5px 7px;text-align:center}
.gift-cfg{white-space:nowrap}
.gift-cfg.on{border-color:#185FA5;color:#185FA5;background:#E6F1FB}
.gift-hint{margin-left:12px;color:var(--ink3)}
.submit-btn{padding:8px 20px}
.submit-btn:disabled{background:#D8D6D0;color:#8C8981;opacity:1;cursor:not-allowed}
.gift-mask{position:fixed;inset:0;z-index:80;background:rgba(28,27,25,.35);display:flex;align-items:center;justify-content:center;padding:24px}
.gift-dlg{width:min(480px,100%);max-height:min(80vh,640px);background:var(--card);border-radius:14px;box-shadow:0 16px 40px rgba(28,27,25,.18);display:flex;flex-direction:column;overflow:hidden}
.gift-dlg .st{padding:14px 16px 8px;margin:0}
.gift-body{padding:0 16px;overflow:auto;flex:1}
.gift-group{margin-bottom:12px}
.gift-cat{font-size:12px;font-weight:600;color:var(--ink2);margin:8px 0 4px}
.gift-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line)}
.gift-stepper{display:flex;align-items:center;gap:6px;flex-shrink:0}
.gift-stepper .step{width:28px;height:28px;border:1px solid var(--line2);border-radius:8px;background:#FAF9F5;cursor:pointer}
.gift-stepper .qty{width:48px;margin:0;padding:4px 6px;text-align:center}
.gift-actions{display:flex;justify-content:flex-end;gap:8px;padding:12px 16px;border-top:1px solid var(--line)}
@media(max-width:1100px){.game-info-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>

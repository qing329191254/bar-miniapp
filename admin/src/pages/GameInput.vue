<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import AppSelect from "../components/AppSelect.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import DateTimePicker from "../components/DateTimePicker.vue";
import { showToast } from "../composables/useToast";

const meta = ref({ projects: [] as any[], tables: [] as any[] });
const members = ref<any[]>([]);
const search = ref("");
const searchArea = ref<HTMLElement | null>(null);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");

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
  players: [] as { uid: number; nick: string; pts: number; sh: number }[],
  winners: {} as Record<number, boolean>,
});

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
  form.players.push({ uid: u.id, nick: u.nick, pts: 0, sh: shard });
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
async function submit() {
  try {
    await api("/staff/games", {
      method: "POST",
      body: {
        projectId: form.pid,
        tableId: form.tid,
        players: form.players,
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
    <div class="hdr game-hdr">对局结果录入 <em>记录参与玩家、成绩与本局积分</em></div>
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
          <table class="tb2 player-table" data-cols="lcccc">
            <thead>
              <tr><th>玩家</th><th>积分</th><th>碎片</th><th>冠军</th><th></th></tr>
            </thead>
            <tbody>
            <tr v-for="p in form.players" :key="p.uid">
              <td><b>{{ p.nick }}</b></td>
              <td><input class="inp score-input" type="number" v-model.number="p.pts" /></td>
              <td><input class="inp score-input" type="number" v-model.number="p.sh" /></td>
              <td class="col-champ">
                <label class="champ-check">
                  <input v-model="form.winners[p.uid]" type="checkbox" class="ui-check" />
                </label>
              </td>
              <td class="tiny" style="cursor:pointer" @click="remove(p.uid)">移除</td>
            </tr>
            <tr v-if="!form.players.length">
              <td colspan="5" class="table-empty">暂无参与玩家，请搜索或从右侧快速添加</td>
            </tr>
            </tbody>
          </table>
          <div class="row" style="margin-top:11px">
            <button class="btn ghost" @click="form.players=[];form.winners={}">清空</button>
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
.submit-btn{padding:8px 20px}
.submit-btn:disabled{background:#D8D6D0;color:#8C8981;opacity:1;cursor:not-allowed}
@media(max-width:1100px){.game-info-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";
import AppSelect from "../components/AppSelect.vue";

const meta = ref({ projects: [] as any[], tables: [] as any[] });
const members = ref<any[]>([]);
const search = ref("");
const msg = ref("");
const form = reactive({
  pid: 1,
  tid: null as number | null,
  round: "",
  event: "",
  eventTouched: false,
  players: [] as { uid: number; nick: string; pts: number; sh: number }[],
  winners: {} as Record<number, boolean>,
});

onMounted(async () => {
  const r = await api<any>("/staff/projects");
  meta.value = r;
  if (r.projects[0]) form.pid = r.projects[0].id;
  members.value = await api("/admin/members");
  if (!form.eventTouched) form.event = defaultEvent();
});

function defaultEvent() {
  const p = meta.value.projects.find((x) => x.id === form.pid);
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())} ${p?.name || "对局"}`;
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
function added(id: number) {
  return form.players.some((p) => p.uid === id);
}
function add(u: any) {
  if (added(u.id)) return;
  const shard = meta.value.projects.find((p) => p.id === form.pid)?.shard || 0;
  form.players.push({ uid: u.id, nick: u.nick, pts: 0, sh: shard });
}
function remove(uid: number) {
  form.players = form.players.filter((p) => p.uid !== uid);
  delete form.winners[uid];
}
async function submit() {
  msg.value = "";
  try {
    await api("/staff/games", {
      method: "POST",
      body: {
        projectId: form.pid,
        tableId: form.tid,
        players: form.players,
        winners: Object.keys(form.winners).filter((k) => form.winners[Number(k)]).map(Number),
        event: form.event,
      },
    });
    msg.value = "提交成功，已入账";
    form.players = [];
    form.winners = {};
  } catch (e: any) {
    msg.value = e.message;
  }
}
</script>

<template>
  <div>
    <div class="hdr">对局结果录入 <em>已并入个人冠军录入 · 所有玩家可填积分</em></div>
    <p class="tiny" v-if="msg" style="color:#3B6D11">{{ msg }}</p>
    <div class="prod-grid">
      <div>
        <div class="card">
          <div class="st">基本信息</div>
          <div class="cards" style="grid-template-columns:repeat(2,1fr)">
            <div>
              <div class="tiny">对局项目 *</div>
              <AppSelect v-model="form.pid" :options="projectOpts" @change="onPidChange" />
            </div>
            <div>
              <div class="tiny">桌台（选填）</div>
              <AppSelect v-model="form.tid" :options="tableOpts" />
            </div>
          </div>
          <div class="tiny">赛事名称</div>
          <input class="inp" v-model="form.event" @input="form.eventTouched = true" />
        </div>
        <div class="card">
          <div class="st">参与玩家 <em>已添加 {{ form.players.length }} 人</em></div>
          <div class="row" style="gap:8px;margin-bottom:10px">
            <input class="inp" style="flex:1;margin:0" placeholder="搜索昵称 / 手机尾号 / 会员号" v-model="search" />
          </div>
          <div class="card" v-if="search && hits.length" style="padding:6px 12px;margin-bottom:10px">
            <div class="li" v-for="x in hits" :key="x.id" :style="{ opacity: added(x.id) ? .5 : 1, cursor: added(x.id) ? 'default' : 'pointer' }" @click="add(x)">
              <div class="gr"><b>{{ x.nick }}</b><span class="tiny">{{ x.no }}</span></div>
              <span class="tiny">{{ added(x.id) ? "已添加" : "添加" }}</span>
            </div>
          </div>
          <table class="tb2">
            <thead>
              <tr><th>玩家</th><th>积分</th><th>碎片</th><th>冠军</th><th></th></tr>
            </thead>
            <tbody>
            <tr v-for="p in form.players" :key="p.uid">
              <td><b>{{ p.nick }}</b></td>
              <td><input class="inp" style="width:70px;padding:4px 7px" type="number" v-model.number="p.pts" /></td>
              <td><input class="inp" style="width:70px;padding:4px 7px" type="number" v-model.number="p.sh" /></td>
              <td><input type="checkbox" :checked="!!form.winners[p.uid]" @change="form.winners[p.uid] = ($event.target as HTMLInputElement).checked" /></td>
              <td class="tiny" style="cursor:pointer" @click="remove(p.uid)">移除</td>
            </tr>
            </tbody>
          </table>
          <div class="row" style="margin-top:11px">
            <button class="btn ghost" @click="form.players=[];form.winners={}">清空</button>
            <button class="btn" style="margin-left:auto" :disabled="!form.players.length" @click="submit">提交并入账</button>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="st">今日到店会员 <em>点击快速添加</em></div>
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
</template>

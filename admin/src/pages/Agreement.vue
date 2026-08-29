<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, DEFAULT_PAGE_SIZE } from "../api";
import AppPagination from "../components/AppPagination.vue";
import { usePagination } from "../composables/usePagination";

type DocKey = "terms" | "privacy";
type AgreementDoc = { ver: number; title: string; text?: string; major?: boolean; pub?: string; hist?: any[] };

const docs = ref<Record<DocKey, AgreementDoc> | null>(null);
const logs = ref<any[]>([]);
const members = ref<any[]>([]);
const tab = ref<DocKey>("terms");
const major = ref(false);
const openVer = ref<number | null>(null);
const keyword = ref("");
const msg = ref("");
const busy = ref(false);

const current = computed(() => docs.value?.[tab.value]);
const docName = computed(() => tab.value === "terms" ? "用户协议" : "隐私政策");
const memberMap = computed(() => new Map(members.value.map((u) => [u.id, u])));
const history = computed(() => current.value?.hist || []);
const selectedLogs = computed(() => {
  if (openVer.value == null) return [];
  const key = keyword.value.trim().toLowerCase();
  return logs.value
    .filter((x) => x.doc === tab.value && Number(x.ver) === openVer.value)
    .map((x) => ({ ...x, user: memberMap.value.get(x.uid) }))
    .filter((x) => !key || String(x.user?.nick || "").toLowerCase().includes(key) || String(x.user?.no || "").includes(key) || String(x.uid).includes(key));
});
const logsPg = usePagination(selectedLogs, DEFAULT_PAGE_SIZE);

function count(ver: number) {
  return logs.value.filter((x) => x.doc === tab.value && Number(x.ver) === Number(ver)).length;
}
function switchTab(next: DocKey) {
  tab.value = next;
  major.value = false;
  openVer.value = null;
  keyword.value = "";
  msg.value = "";
}
function nowLabel() {
  const d = new Date();
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
async function persist(message: string) {
  if (!docs.value) return;
  busy.value = true;
  msg.value = "";
  try {
    await api("/admin/agreements", { method: "PUT", body: { data: docs.value } });
    msg.value = message;
  } catch (e: any) {
    msg.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function saveDraft() {
  await persist("草稿已保存");
}
async function publish() {
  const d = current.value;
  if (!d || !d.title?.trim() || !d.text?.trim()) {
    msg.value = "请填写文档标题和正文";
    return;
  }
  if (!window.confirm(`确认发布${docName.value} v${Number(d.ver || 0) + 1}？`)) return;
  const next = Number(d.ver || 0) + 1;
  const pub = nowLabel();
  d.ver = next;
  d.pub = pub;
  d.major = major.value;
  d.hist = [{ v: next, type: major.value ? "重大变更" : "文字修订", pub }, ...(d.hist || [])];
  await persist(`已发布 v${next}${major.value ? "，老用户需重新确认" : ""}`);
  major.value = false;
}

onMounted(async () => {
  try {
    const [agreements, agreeLogs, users] = await Promise.all([
      api("/admin/agreements"), api("/admin/agreeLogs?pageSize=0"), api("/admin/members?pageSize=0"),
    ]);
    docs.value = agreements;
    logs.value = agreeLogs;
    members.value = users;
  } catch (e: any) {
    msg.value = e.message;
  }
});
</script>

<template>
  <div>
    <div class="hdr">协议与政策 <em>版本管理不可省 · 法律凭证</em></div>
    <p v-if="msg" class="tiny agreement-msg">{{ msg }}</p>
    <div v-if="docs && current" class="agreement-grid">
      <div class="card">
        <div class="row agreement-tabs">
          <button class="chip" :class="{ on: tab === 'terms' }" @click="switchTab('terms')">用户协议</button>
          <button class="chip" :class="{ on: tab === 'privacy' }" @click="switchTab('privacy')">隐私政策</button>
          <span class="tiny agreement-meta">当前 v{{ current.ver }} · {{ current.pub || '尚未发布' }} 发布 · 已同意 {{ count(current.ver) }} 人</span>
        </div>
        <div class="agreement-fields">
          <div><div class="tiny">文档标题</div><input v-model="current.title" class="inp" /></div>
          <div><div class="tiny">版本号</div><input class="inp" :value="`v${Number(current.ver || 0) + 1}（发布后自动生成）`" disabled /></div>
        </div>
        <div class="tiny">正文</div>
        <textarea v-model="current.text" class="inp agreement-editor" :placeholder="`请输入${docName}正文`"></textarea>
        <div class="row agreement-actions">
          <label class="row agreement-major"><input v-model="major" type="checkbox" /><span class="tiny">此为<b>重大条款变更</b>，需老用户重新确认</span></label>
          <button class="btn ghost" :disabled="busy" @click="saveDraft">存草稿</button>
          <button class="btn" :disabled="busy" @click="publish">发布 v{{ Number(current.ver || 0) + 1 }}</button>
        </div>
      </div>
      <div>
        <div class="card">
          <div class="st">版本历史 <em>永久保留不可删除</em></div>
          <div class="tb-wrap">
            <table class="tb2">
              <thead><tr><th>版本</th><th>类型</th><th>已同意用户</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="h in history" :key="h.v" :class="{ 'agreement-selected': openVer === h.v }">
                  <td><b>v{{ h.v }}</b><span v-if="h.v === current.ver" class="pill agreement-live">生效中</span></td>
                  <td class="tiny">{{ h.type }}<br />{{ h.pub }}</td>
                  <td><b>{{ count(h.v) }}</b> 人<div class="tiny">{{ count(h.v) ? '可下钻查看' : '暂无记录' }}</div></td>
                  <td><button class="btn ghost agreement-small" :disabled="!count(h.v)" @click="openVer = openVer === h.v ? null : h.v">{{ openVer === h.v ? '收起' : '查看名单' }}</button></td>
                </tr>
                <tr v-if="!history.length"><td colspan="4" class="table-empty">暂无协议版本记录</td></tr>
              </tbody>
            </table>
          </div>
          <div class="tiny agreement-foot">同意人数来自 C 端注册及重大变更后的重新确认记录。</div>
        </div>
        <div v-if="openVer != null" class="card">
          <div class="st">v{{ openVer }} 已同意用户 <em>{{ selectedLogs.length }} 人</em></div>
          <input v-model="keyword" class="inp" placeholder="搜索昵称 / 会员号 / ID" />
          <div class="tb-wrap agreement-users"><table class="tb2"><thead><tr><th>昵称</th><th>会员号</th><th>同意时间</th><th>状态</th></tr></thead><tbody>
            <tr v-for="x in logsPg.items" :key="`${x.uid}-${x.at}`"><td>{{ x.user?.nick || '未知用户' }}</td><td>{{ x.user?.no || `uid ${x.uid}` }}</td><td class="tiny">{{ x.at }}</td><td><span class="pill" :class="x.user?.status === 'ACTIVE' ? 'agreement-live' : 'agreement-off'">{{ x.user?.status === 'ACTIVE' ? '正常' : '已注销' }}</span></td></tr>
            <tr v-if="!selectedLogs.length"><td colspan="4" class="tiny agreement-empty">无匹配记录</td></tr>
          </tbody></table>
          <AppPagination v-model:page="logsPg.page" v-model:page-size="logsPg.pageSize" :total="logsPg.total" />
          </div>
        </div>
        <div class="note rd"><b>合规底线：</b>须覆盖个人信息收集与用途、账号注销与资产处理、金币性质与退款规则、积分清零、卡券有效期与争议解决方式。</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agreement-grid{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:12px}.agreement-tabs{margin-bottom:11px;flex-wrap:wrap}.agreement-meta{margin-left:auto}.agreement-fields{display:grid;grid-template-columns:1fr 1fr;gap:8px}.agreement-editor{height:300px;resize:vertical;line-height:1.75}.agreement-actions{margin-top:3px}.agreement-major{margin-right:auto}.agreement-major b{color:var(--red)}.agreement-msg{color:var(--green);margin-bottom:8px}.agreement-live{background:var(--greenbg);color:var(--green);margin-left:4px}.agreement-off{background:#EEECE6;color:var(--ink3)}.agreement-small{padding:4px 7px;font-size:11px}.agreement-selected td{background:#E6F1FB}.agreement-foot{margin-top:8px}.agreement-users{max-height:280px}.agreement-empty{text-align:center}.btn:disabled{opacity:.45;cursor:not-allowed}@media(max-width:1050px){.agreement-grid{grid-template-columns:1fr}.agreement-meta{width:100%;margin-left:0}.agreement-fields{grid-template-columns:1fr}}
</style>

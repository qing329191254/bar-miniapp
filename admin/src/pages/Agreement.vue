<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, DEFAULT_PAGE_SIZE } from "../api";
import AppPagination from "../components/AppPagination.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { usePagination } from "../composables/usePagination";
import { csvFilename, downloadXlsx } from "../exportCsv";
import { showToast } from "../composables/useToast";

type DocKey = "terms" | "privacy";
type AgreementDoc = { ver: number; title: string; text?: string; major?: boolean; pub?: string; hist?: any[] };

const docs = ref<Record<DocKey, AgreementDoc> | null>(null);
const logs = ref<any[]>([]);
const members = ref<any[]>([]);
const tab = ref<DocKey>("terms");
const major = ref(false);
const openVer = ref<number | null>(null);
const keyword = ref("");
const busy = ref(false);
const showPublishDlg = ref(false);
const exporting = ref(false);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");

const current = computed(() => docs.value?.[tab.value]);
const docName = computed(() => tab.value === "terms" ? "用户协议" : "隐私政策");
const nextVer = computed(() => Number(current.value?.ver || 0) + 1);
const memberMap = computed(() => new Map(members.value.map((u) => [u.id, u])));
const history = computed(() => current.value?.hist || []);
function verNum(v: unknown) {
  return Number(v);
}
function histVer(h: { v?: unknown; ver?: unknown }) {
  return Number(h?.v ?? h?.ver ?? 0);
}
function isOpenVer(v: unknown) {
  return openVer.value != null && openVer.value === verNum(v);
}

const selectedLogs = computed(() => {
  if (openVer.value == null) return [];
  const key = keyword.value.trim().toLowerCase();
  return logs.value
    .filter((x) => x.doc === tab.value && Number(x.ver) === openVer.value)
    .map((x) => ({ ...x, user: memberMap.value.get(x.uid) }))
    .filter((x) => !key || String(x.user?.nick || "").toLowerCase().includes(key) || String(x.user?.no || "").includes(key) || String(x.uid).includes(key));
});
const logsPg = usePagination(selectedLogs, DEFAULT_PAGE_SIZE);
const pagedLogs = logsPg.items;
const logsPage = logsPg.page;
const logsPageSize = logsPg.pageSize;
const logsTotal = logsPg.total;

function asList<T>(res: T[] | { items?: T[] } | null | undefined): T[] {
  if (Array.isArray(res)) return res;
  if (res && Array.isArray(res.items)) return res.items;
  return [];
}

function count(ver: number) {
  return logs.value.filter((x) => x.doc === tab.value && Number(x.ver) === Number(ver)).length;
}
function toggleVerList(ver: unknown) {
  const n = verNum(ver);
  if (!n) return;
  if (openVer.value === n) {
    openVer.value = null;
    return;
  }
  openVer.value = n;
  keyword.value = "";
}
function closeUserList() {
  openVer.value = null;
  keyword.value = "";
}
function exportUserList() {
  if (exporting.value || openVer.value == null) return;
  const list = selectedLogs.value;
  if (!list.length) {
    showToast("当前筛选条件下无数据可导出", true);
    return;
  }
  exporting.value = true;
  try {
    const headers = ["昵称", "会员号", "用户ID", "同意时间", "状态"];
    const body = list.map((x) => [
      x.user?.nick || "未知用户",
      x.user?.no || "",
      String(x.uid),
      x.at || "",
      x.user?.status === "ACTIVE" ? "正常" : "已注销",
    ]);
    downloadXlsx(
      csvFilename("协议同意名单", `v${openVer.value}_${docName.value}`, "xlsx"),
      headers,
      body,
      {
        colWidths: [14, 12, 10, 16, 10],
        textCols: [1, 2, 3],
        sheetName: "同意名单",
      },
    );
    showToast(`已导出 ${list.length} 条同意记录`);
  } catch (e: any) {
    showToast(e?.message || "导出失败", true);
  } finally {
    exporting.value = false;
  }
}
function switchTab(next: DocKey) {
  tab.value = next;
  major.value = false;
  openVer.value = null;
  keyword.value = "";
}
function nowLabel() {
  const d = new Date();
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
async function persist(message: string) {
  if (!docs.value) return;
  busy.value = true;
  try {
    await api("/admin/agreements", { method: "PUT", body: { data: docs.value } });
    showToast(message);
  } catch (e: any) {
    showToast(e.message, true);
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
    showToast("请填写文档标题和正文", true);
    return;
  }
  showPublishDlg.value = true;
}
async function confirmPublish() {
  const d = current.value;
  if (!d) return;
  showPublishDlg.value = false;
  const next = Number(d.ver || 0) + 1;
  const pub = nowLabel();
  d.ver = next;
  d.pub = pub;
  d.major = major.value;
  d.hist = [{ v: next, type: major.value ? "重大变更" : "文字修订", pub }, ...(d.hist || [])];
  await persist(`已发布 v${next}${major.value ? "，老用户需重新确认" : ""}`);
  major.value = false;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    try {
      docs.value = await api("/admin/agreements");
    } catch (e: any) {
      docs.value = null;
      err.value = e?.message || "协议与政策加载失败";
      return;
    }
    try {
      logs.value = asList(await api("/admin/agreeLogs?pageSize=0"));
    } catch (e: any) {
      logs.value = [];
      showToast(e?.message || "同意记录加载失败", true);
    }
    try {
      members.value = asList(await api("/admin/members?pageSize=0"));
    } catch {
      members.value = [];
    }
    loaded.value = true;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 0, showNote: true }" @retry="load">
  <div>
    <div class="hdr agreement-hdr">
      <span class="hdr-title">协议与政策</span>
      <em class="hdr-note">版本管理不可省 · 法律凭证</em>
    </div>
    <div v-if="docs && current" class="agreement-grid">
      <div class="card">
        <div class="row agreement-tabs">
          <button class="chip" :class="{ on: tab === 'terms' }" @click="switchTab('terms')">用户协议</button>
          <button class="chip" :class="{ on: tab === 'privacy' }" @click="switchTab('privacy')">隐私政策</button>
          <span class="tiny agreement-meta">当前 v{{ current.ver }} · {{ current.pub || '尚未发布' }} 发布 · 已同意 {{ count(current.ver) }} 人</span>
        </div>
        <div class="agreement-fields">
          <div><div class="tiny">文档标题</div><input v-model="current.title" class="inp" /></div>
          <div><div class="tiny">版本号</div><div class="inp agreement-ver-hint">v{{ nextVer }}（发布后自动生成）</div></div>
        </div>
        <div class="tiny">正文</div>
        <textarea v-model="current.text" class="inp agreement-editor" :placeholder="`请输入${docName}正文`"></textarea>
        <div class="row agreement-actions">
          <label class="row agreement-major"><input v-model="major" type="checkbox" /><span class="tiny">此为<b>重大条款变更</b>，需老用户重新确认</span></label>
          <button class="btn ghost" :disabled="busy" @click="saveDraft">存草稿</button>
          <button class="btn" :disabled="busy" @click="publish">发布 v{{ nextVer }}</button>
        </div>
      </div>
      <div>
        <div class="card">
          <div class="st">版本历史 <em>永久保留不可删除</em></div>
          <div class="tb-wrap">
            <table class="tb2 agreement-history-table">
              <thead><tr><th>版本</th><th>类型</th><th>已同意用户</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="h in history" :key="histVer(h)" :class="{ 'agreement-selected': isOpenVer(histVer(h)) }">
                  <td><b>v{{ histVer(h) }}</b><span v-if="histVer(h) === verNum(current.ver)" class="pill agreement-live">生效中</span></td>
                  <td class="tiny">{{ h.type }}<br />{{ h.pub }}</td>
                  <td><b>{{ count(histVer(h)) }}</b> 人<div class="tiny">{{ count(histVer(h)) ? '可下钻查看' : '暂无记录' }}</div></td>
                  <td><button type="button" class="btn ghost agreement-small" @click="toggleVerList(histVer(h))">{{ isOpenVer(histVer(h)) ? '收起' : '查看名单' }}</button></td>
                </tr>
                <tr v-if="!history.length"><td colspan="4" class="table-empty">暂无协议版本记录</td></tr>
              </tbody>
            </table>
          </div>
          <div class="tiny agreement-foot">同意人数统计自顾客注册，以及协议重大变更后的再次确认记录。</div>
        </div>
        <div class="side-note warn">
          <div class="side-note-body">
            <b>合规底线：</b>须覆盖个人信息收集与用途、账号注销与资产处理、金币性质与退款规则、积分清零、卡券有效期与争议解决方式。
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="openVer != null" class="dlg-mask agreement-user-mask" @click.self="closeUserList">
        <section class="dlg agreement-user-dlg">
          <div class="st agreement-user-hdr">
            <span>v{{ openVer }} 已同意用户 <em>{{ selectedLogs.length }} 人</em></span>
            <button type="button" class="agreement-close" @click="closeUserList">收起</button>
          </div>
          <input v-model="keyword" class="inp" placeholder="搜索昵称 / 会员号 / ID" />
          <div class="tb-wrap agreement-users">
            <table class="tb2 agreement-users-table">
              <thead><tr><th>昵称</th><th>会员号</th><th>同意时间</th><th>状态</th></tr></thead>
              <tbody>
                <tr v-for="x in pagedLogs" :key="`${x.uid}-${x.at}`">
                  <td>{{ x.user?.nick || '未知用户' }}</td>
                  <td>{{ x.user?.no || `uid ${x.uid}` }}</td>
                  <td class="tiny">{{ x.at }}</td>
                  <td><span class="pill" :class="x.user?.status === 'ACTIVE' ? 'agreement-live' : 'agreement-off'">{{ x.user?.status === 'ACTIVE' ? '正常' : '已注销' }}</span></td>
                </tr>
                <tr v-if="!selectedLogs.length"><td colspan="4" class="tiny agreement-empty">{{ count(openVer!) ? '无匹配记录' : '该版本暂无同意记录' }}</td></tr>
              </tbody>
            </table>
          </div>
          <AppPagination v-model:page="logsPage" v-model:page-size="logsPageSize" :total="logsTotal" />
          <button type="button" class="btn sm agreement-export" :disabled="exporting || !selectedLogs.length" @click="exportUserList">
            {{ exporting ? "导出中…" : "导出" }}
          </button>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
    <div v-if="showPublishDlg && current" class="dlg-mask" @click.self="showPublishDlg = false">
      <section class="dlg">
        <div class="st">发布{{ docName }}</div>
        <p class="dlg-body">
          确认发布 <b>{{ docName }} v{{ Number(current.ver || 0) + 1 }}</b>？
          <span v-if="major" class="dlg-warn">已勾选重大条款变更，发布后老用户登录时需重新确认。</span>
          <span v-else class="dlg-hint">发布后版本号自动递增，同意记录从 v{{ Number(current.ver || 0) + 1 }} 起重新统计。</span>
        </p>
        <div class="dlg-actions">
          <button class="btn ghost" type="button" :disabled="busy" @click="showPublishDlg = false">取消</button>
          <button class="btn" type="button" :disabled="busy" @click="confirmPublish">确认发布</button>
        </div>
      </section>
    </div>
    </Teleport>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.agreement-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}
.dlg{width:min(480px,100%);background:#fff;border-radius:16px;padding:24px;box-shadow:0 18px 45px rgba(0,0,0,.2)}
.dlg-body{margin:8px 0 0;font-size:13px;line-height:1.65;color:var(--ink2)}
.dlg-warn{display:block;margin-top:8px;color:var(--red);font-size:12px}
.dlg-hint{display:block;margin-top:8px;color:var(--ink3);font-size:12px}
.dlg-actions{display:grid;grid-template-columns:1fr 1.6fr;gap:10px;margin-top:20px}
.dlg-actions .btn{width:100%}
.agreement-grid{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:12px}.agreement-tabs{margin-bottom:11px;flex-wrap:wrap}.agreement-meta{margin-left:auto}.agreement-fields{display:grid;grid-template-columns:1fr 1fr;gap:8px}.agreement-ver-hint{color:var(--ink3);background:#fff;cursor:default;user-select:none}.agreement-editor{height:300px;resize:vertical;line-height:1.75}.agreement-actions{margin-top:3px}.agreement-major{margin-right:auto}.agreement-major b{color:var(--red)}.agreement-live{background:var(--greenbg);color:var(--green);margin-left:4px}.agreement-off{background:#EEECE6;color:var(--ink3)}.agreement-small{padding:4px 7px;font-size:11px}.agreement-history-table :is(th,td):nth-child(4){text-align:center}.agreement-selected td{background:#E6F1FB}.agreement-foot{margin-top:8px}.agreement-user-mask{z-index:1000}.agreement-user-dlg{width:min(640px,100%);max-height:min(88vh,720px);overflow:auto}.agreement-user-hdr{margin-bottom:10px}.agreement-user-hdr em{font-style:normal;font-size:11px;color:var(--ink3);font-weight:400;margin-left:6px}.agreement-close{margin-left:auto;border:none;background:transparent;padding:0;font-size:11px;color:var(--blue);cursor:pointer}.agreement-close:hover{text-decoration:underline}.agreement-users{max-height:min(52vh,420px);overflow:auto;margin-top:8px}.agreement-users-table :is(th,td):nth-child(4){text-align:center}.agreement-export{margin-top:10px}.agreement-export:disabled{opacity:.55;cursor:not-allowed}.agreement-empty{text-align:center;padding:16px 0}@media(max-width:1050px){.agreement-grid{grid-template-columns:1fr}.agreement-meta{width:100%;margin-left:0}.agreement-fields{grid-template-columns:1fr}}
</style>

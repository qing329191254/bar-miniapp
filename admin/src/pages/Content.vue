<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, uploadFile } from "../api";
import ImgField from "../components/ImgField.vue";
import IcoBtn from "../components/IcoBtn.vue";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

const addInp = ref<HTMLInputElement | null>(null);
const tab = ref<"gallery" | "play" | "faq">("gallery");
const deleteDlg = ref<{ kind: "photo" | "play" | "faq"; index: number } | null>(null);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");

const FAQ_DEFAULT = {
  title: "常见问题",
  sub: "资产与规则说明",
  items: [
    {
      q: "金币可以退款吗？",
      a: "充值的本金金币未消费部分可到店申请退还；赠送金币不可退、不可提现、不可转让。消费时优先扣减本金金币。",
    },
    {
      q: "积分什么时候清零？",
      a: "积分有效期为自然月，每月 1 日 13:00 清零，不结转到下月。请在清零前兑换卡券或到吧台提取。",
    },
    {
      q: "卡券过期了还能用吗？",
      a: "不能。游戏卡与酒水小食卡 30 天有效，宝箱卡 7 天有效，过期自动作废且不补偿，请留意卡包中的临期红标。",
    },
    {
      q: "碎片有什么用？",
      a: "碎片是荣誉值，只用于周榜排名与周奖励评定，不能兑换任何实物或抵扣消费，也不会清零。",
    },
    {
      q: "怎么加入战队？",
      a: "战队由本店统一分组，会员不能自建或自行申请加入，到吧台联系店员安排即可。",
    },
  ],
};

const content = ref<any>({
  gallery: { title: "店铺相册", items: [] },
  howToPlay: { title: "店铺玩法", sub: "", items: [], pic: "" },
  faq: { title: "常见问题", sub: "资产与规则说明", items: [] },
});

function normalizeFaq(raw: any) {
  if (Array.isArray(raw)) {
    return {
      title: "常见问题",
      sub: "资产与规则说明",
      items: raw
        .filter((it: any) => it && typeof it === "object")
        .map((it: any) => ({ q: String(it?.q || "").trim(), a: String(it?.a || "").trim() })),
    };
  }
  const f = raw && typeof raw === "object" ? raw : {};
  const items = Array.isArray(f.items)
    ? f.items.map((it: any) => ({
        q: String(it?.q || "").trim(),
        a: String(it?.a || "").trim(),
      }))
    : [];
  return {
    title: String(f.title || "常见问题").trim() || "常见问题",
    sub: String(f.sub || "资产与规则说明").trim() || "资产与规则说明",
    items,
  };
}

function normalizeGallery(raw: any) {
  // Bare [] is truthy — never use `raw || default` for this shape.
  if (Array.isArray(raw)) {
    return {
      title: "店铺相册",
      items: raw.filter((x: any) => x && x.url).map((x: any, i: number) => ({
        id: Number(x.id) || i + 1,
        name: String(x.name || "").trim(),
        desc: String(x.desc || "").trim(),
        url: String(x.url || "").trim(),
      })),
    };
  }
  const g = raw && typeof raw === "object" ? raw : {};
  const items = Array.isArray(g.items) ? g.items : [];
  return {
    title: String(g.title || "店铺相册").trim() || "店铺相册",
    items: items
      .filter((x: any) => x && x.url)
      .map((x: any, i: number) => ({
        id: Number(x.id) || i + 1,
        name: String(x.name || "").trim(),
        desc: String(x.desc || "").trim(),
        url: String(x.url || "").trim(),
      })),
  };
}

function normalizeHowToPlay(raw: any) {
  if (Array.isArray(raw)) {
    return {
      title: "店铺玩法",
      sub: "",
      items: raw.map((x: any) => String(x || "").trim()).filter(Boolean),
      pic: "",
    };
  }
  const h = raw && typeof raw === "object" ? raw : {};
  const items = Array.isArray(h.items) ? h.items.map((x: any) => String(x || "").trim()).filter(Boolean) : [];
  return {
    title: String(h.title || "店铺玩法").trim() || "店铺玩法",
    sub: String(h.sub || "").trim(),
    items,
    pic: String(h.pic || "").trim(),
  };
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const r = await api<any>("/admin/content");
    content.value = {
      gallery: normalizeGallery(r.gallery),
      howToPlay: normalizeHowToPlay(r.howToPlay),
      faq: normalizeFaq(r.faq),
    };
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "店铺内容加载失败";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const g = computed(() => content.value.gallery);
const h = computed(() => content.value.howToPlay);
const f = computed(() => content.value.faq);
function isImg(v: string) {
  return !!v && (/^\/uploads\//.test(v) || /^https?:/.test(v) || v.startsWith("data:"));
}

async function save(part: string) {
  try {
    if (part === "gallery") {
      content.value.gallery = normalizeGallery(content.value.gallery);
    }
    if (part === "play" || part === "howToPlay") {
      content.value.howToPlay = normalizeHowToPlay(content.value.howToPlay);
    }
    if (part === "faq") {
      content.value.faq = normalizeFaq(content.value.faq);
      const bad = (content.value.faq.items || []).findIndex((it: any) => !it.q || !it.a);
      if (bad >= 0) {
        showToast(`第 ${bad + 1} 条请填写完整问答`, true);
        return;
      }
    }
    const key = part === "play" ? "howToPlay" : part;
    await api("/admin/content", { method: "PUT", body: { data: { [key]: content.value[key] } } });
    showToast("已保存，小程序已同步");
  } catch (e: any) {
    showToast(e.message || "保存失败", true);
  }
}
function addPhoto() {
  addInp.value?.click();
}
async function onAddFiles(e: Event) {
  const files = [...((e.target as HTMLInputElement).files || [])];
  (e.target as HTMLInputElement).value = "";
  if (!files.length) return;
  try {
    content.value.gallery = normalizeGallery(content.value.gallery);
    const items = [...(g.value.items || [])];
    for (const file of files) {
      const url = await uploadFile(file);
      const id = items.reduce((m: number, x: any) => Math.max(m, x.id || 0), 0) + 1;
      items.push({ id, name: file.name.replace(/\.[^.]+$/, ""), desc: "", url });
    }
    g.value.items = items;
  } catch (e: any) {
    showToast(e.message || "上传失败", true);
  }
}
function delPhoto(i: number) {
  deleteDlg.value = { kind: "photo", index: i };
}
function movePhoto(i: number, d: number) {
  const a = g.value.items;
  const j = i + d;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]];
}
function addPlay() {
  content.value.howToPlay = normalizeHowToPlay(content.value.howToPlay);
  h.value.items = [...(h.value.items || []), ""];
}
function delPlay(i: number) {
  deleteDlg.value = { kind: "play", index: i };
}
function movePlay(i: number, d: number) {
  const a = h.value.items;
  const j = i + d;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]];
}
function addFaq() {
  content.value.faq = normalizeFaq(content.value.faq);
  f.value.items = [...(f.value.items || []), { q: "", a: "" }];
}
function fillFaqTemplate() {
  content.value.faq = {
    title: FAQ_DEFAULT.title,
    sub: FAQ_DEFAULT.sub,
    items: FAQ_DEFAULT.items.map((it) => ({ ...it })),
  };
  showToast("已填入推荐模板，请检查后点保存");
}
function delFaq(i: number) {
  deleteDlg.value = { kind: "faq", index: i };
}
function moveFaq(i: number, d: number) {
  const a = f.value.items;
  const j = i + d;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]];
}
function confirmDelete() {
  if (!deleteDlg.value) return;
  const { kind, index } = deleteDlg.value;
  if (kind === "photo") g.value.items.splice(index, 1);
  else if (kind === "play") h.value.items.splice(index, 1);
  else f.value.items.splice(index, 1);
  deleteDlg.value = null;
}
</script>

<template>
  <AppAsyncPage :loading="loading" :data="loaded" :err="err" :skeleton="{ variant: 'form', showFilter: false, metrics: 0, showNote: false }" @retry="load">
  <div v-if="content">
    <div class="hdr content-hdr">
      <span class="hdr-title">店铺内容</span>
      <em class="hdr-note">相册 · 玩法 · 常见问题</em>
    </div>
    <div class="row" style="gap:8px;margin-bottom:11px;flex-wrap:wrap">
      <span class="chip" :class="{ on: tab==='gallery' }" @click="tab='gallery'">店铺相册 · {{ g.items?.length || 0 }} 张</span>
      <span class="chip" :class="{ on: tab==='play' }" @click="tab='play'">店铺玩法 · {{ h.items?.length || 0 }} 条</span>
      <span class="chip" :class="{ on: tab==='faq' }" @click="tab='faq'">常见问题 · {{ f.items?.length || 0 }} 条</span>
      <span class="tiny" style="margin-left:auto">改动保存后即时同步小程序</span>
    </div>

    <div v-if="tab==='gallery'" class="content-grid">
      <div class="card">
        <div class="row" style="margin-bottom:11px">
          <b>相册图片</b>
          <span class="tiny" style="margin-left:8px">小程序相册弹层按此顺序展示</span>
          <button class="btn gold" style="margin-left:auto" @click="addPhoto">＋ 上传图片</button>
          <input ref="addInp" type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple hidden @change="onAddFiles" />
        </div>
        <div class="tiny">相册标题</div>
        <input class="inp" style="max-width:280px" v-model="g.title" />
        <table class="tb2 gallery-table">
          <thead>
            <tr><th>序号</th><th>预览</th><th>图片名称</th><th>说明</th><th>操作</th></tr>
          </thead>
          <tbody>
          <tr v-for="(it,i) in g.items" :key="it.id || i">
            <td><b>{{ i + 1 }}</b></td>
            <td><ImgField v-model="it.url" /></td>
            <td><input class="inp" style="padding:4px 7px;margin:0" v-model="it.name" /></td>
            <td><input class="inp" style="padding:4px 7px;margin:0" v-model="it.desc" placeholder="如 卡座区" /></td>
            <td>
              <div class="ops">
                <IcoBtn name="up" title="上移" :disabled="i===0" @click="movePhoto(i,-1)" />
                <IcoBtn name="down" title="下移" :disabled="i===g.items.length-1" @click="movePhoto(i,1)" />
                <IcoBtn name="trash" title="删除" @click="delPhoto(i)" />
              </div>
            </td>
          </tr>
          <tr v-if="!g.items?.length"><td colspan="5" class="tiny" style="text-align:center">暂无图片，小程序显示「商家尚未上传相册」</td></tr>
          </tbody>
        </table>
        <button class="btn" style="margin-top:10px" @click="save('gallery')">保存相册</button>
      </div>
      <div class="preview-col">
        <div class="card">
          <div class="st">小程序预览 <em>相册弹层</em></div>
          <div v-if="g.items?.length" class="gallery-sheet">
            <div v-for="(it, i) in g.items" :key="it.id || i" class="gallery-tile">
              <img v-if="isImg(it.url)" :src="it.url" alt="" />
              <div class="gallery-tile-shade"></div>
              <span>{{ it.name || `现场 ${i + 1}` }}<small v-if="it.desc">{{ it.desc }}</small></span>
            </div>
          </div>
          <div v-else class="gallery-sheet-empty">
            <b>商家尚未上传相册</b>
            <span>保存后小程序相册弹层即时展示</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab==='play'" class="content-grid">
      <div class="card">
        <div class="row" style="margin-bottom:11px">
          <b>玩法说明</b>
          <button class="btn gold" style="margin-left:auto" @click="addPlay">＋ 添加一条</button>
        </div>
        <div class="cards" style="grid-template-columns:1fr 1fr;margin-bottom:9px">
          <div><div class="tiny">弹层标题</div><input class="inp" v-model="h.title" /></div>
          <div><div class="tiny">副标题</div><input class="inp" v-model="h.sub" /></div>
        </div>
        <div class="row" style="gap:6px;margin-bottom:6px" v-for="(_,i) in h.items" :key="i">
          <span class="tiny" style="width:16px;flex:none">{{ i + 1 }}</span>
          <input class="inp" style="flex:1;margin:0" v-model="h.items[i]" />
          <div class="ops">
            <IcoBtn name="up" title="上移" :disabled="i===0" @click="movePlay(i,-1)" />
            <IcoBtn name="down" title="下移" :disabled="i===h.items.length-1" @click="movePlay(i,1)" />
            <IcoBtn name="trash" title="删除" @click="delPlay(i)" />
          </div>
        </div>
        <div class="tiny">场地示意图（选填）</div>
        <ImgField v-model="h.pic" size="md" />
        <div class="tiny" style="margin-top:4px">点击方块上传，小程序玩法页展示</div>
        <button class="btn" style="margin-top:10px" @click="save('howToPlay')">保存玩法</button>
      </div>
      <div>
        <div class="card">
          <div class="st">小程序预览 <em>玩法弹层</em></div>
          <div class="pv-phone">
            <div class="pv-status"><span>玩咖</span><span>21:40 · 5G</span></div>
            <div class="pv-sheet">
              <b>{{ h.title || "店铺玩法" }}</b>
              <div class="tiny" style="margin:4px 0 8px">{{ h.sub }}</div>
              <div class="tiny" style="line-height:1.8">
                <div v-for="(line,i) in h.items" :key="i">· {{ line }}</div>
                <div v-if="!h.items?.length">暂无内容</div>
              </div>
              <div v-if="h.pic && isImg(h.pic)" class="pv-pic"><img :src="h.pic" alt="" /></div>
              <div v-else-if="h.pic" class="pv-pic">{{ h.pic }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab==='faq'" class="content-grid">
      <div class="card">
        <div class="row" style="margin-bottom:11px;gap:8px;flex-wrap:wrap">
          <b>常见问题</b>
          <span class="tiny">会员端「我的 → 常见问题」展示</span>
          <button class="btn ghost" style="margin-left:auto" type="button" @click="fillFaqTemplate">填入推荐模板</button>
          <button class="btn gold" type="button" @click="addFaq">＋ 添加一条</button>
        </div>
        <div class="cards" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
          <div><div class="tiny">弹层标题</div><input class="inp" v-model="f.title" /></div>
          <div><div class="tiny">副标题</div><input class="inp" v-model="f.sub" /></div>
        </div>
        <div v-for="(it, i) in f.items" :key="i" class="faq-edit">
          <div class="faq-edit-hd">
            <b>第 {{ i + 1 }} 条</b>
            <div class="ops">
              <IcoBtn name="up" title="上移" :disabled="i===0" @click="moveFaq(i,-1)" />
              <IcoBtn name="down" title="下移" :disabled="i===f.items.length-1" @click="moveFaq(i,1)" />
              <IcoBtn name="trash" title="删除" @click="delFaq(i)" />
            </div>
          </div>
          <div class="tiny">问题</div>
          <input class="inp" v-model="it.q" placeholder="例如：金币可以退款吗？" />
          <div class="tiny" style="margin-top:8px">回答</div>
          <textarea class="inp faq-answer" v-model="it.a" rows="3" placeholder="填写解答说明" />
        </div>
        <div v-if="!f.items?.length" class="tiny faq-empty">暂无问答。可点「填入推荐模板」再按店内规则改，或「添加一条」自行编写。</div>
        <button class="btn" style="margin-top:10px" @click="save('faq')">保存常见问题</button>
      </div>
      <div>
        <div class="card">
          <div class="st">小程序预览 <em>常见问题弹层</em></div>
          <div class="pv-phone">
            <div class="pv-status"><span>玩咖</span><span>21:40 · 5G</span></div>
            <div class="pv-sheet">
              <b>{{ f.title || "常见问题" }}</b>
              <div class="tiny" style="margin:4px 0 10px">{{ f.sub || "资产与规则说明" }} · 共 {{ f.items?.length || 0 }} 条</div>
              <div v-if="f.items?.length" class="faq-preview-list">
                <div v-for="(it, i) in f.items" :key="i" class="faq-preview-item">
                  <b>{{ it.q || "（未填问题）" }}</b>
                  <div class="tiny">{{ it.a || "（未填回答）" }}</div>
                </div>
              </div>
              <div v-else class="tiny">暂无常见问题</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
    <div v-if="deleteDlg" class="dlg-mask" @click.self="deleteDlg = null">
      <section class="dlg">
        <div class="st">
          {{ deleteDlg.kind === "photo" ? "删除相册图片" : deleteDlg.kind === "play" ? "删除玩法说明" : "删除常见问题" }}
        </div>
        <p class="dlg-body">
          <template v-if="deleteDlg.kind === 'photo'">
            确认删除这张图片？小程序相册弹层会少一张。
          </template>
          <template v-else-if="deleteDlg.kind === 'play'">
            确认删除第 <b>{{ deleteDlg.index + 1 }}</b> 条说明？
            <span v-if="h.items[deleteDlg.index]" class="dlg-preview">「{{ h.items[deleteDlg.index] }}」</span>
          </template>
          <template v-else>
            确认删除第 <b>{{ deleteDlg.index + 1 }}</b> 条问答？
            <span v-if="f.items[deleteDlg.index]?.q" class="dlg-preview">「{{ f.items[deleteDlg.index].q }}」</span>
          </template>
        </p>
        <div class="dlg-actions">
          <button class="btn ghost" type="button" @click="deleteDlg = null">取消</button>
          <button class="btn dan" type="button" @click="confirmDelete">确认删除</button>
        </div>
      </section>
    </div>
    </Teleport>
  </div>
  </AppAsyncPage>
</template>

<style scoped>
.content-hdr .hdr-note {
  position: static;
  transform: none;
  margin-left: auto;
  text-align: right;
  pointer-events: auto;
  white-space: normal;
}
.content-grid {
  display: grid;
  grid-template-columns: minmax(680px, 1fr) minmax(300px, 340px);
  gap: 16px;
  align-items: start;
}
.content-grid > .card,
.preview-col,
.preview-col > .card { min-width: 0; }
.preview-col > .card { margin: 0; }
.gallery-table { table-layout: fixed; }
.gallery-table th:nth-child(1),
.gallery-table td:nth-child(1) { width: 54px; }
.gallery-table th:nth-child(2),
.gallery-table td:nth-child(2) { width: 82px; }
.gallery-table th:nth-child(5),
.gallery-table td:nth-child(5) { width: 148px; }
.gallery-table td { vertical-align: middle; }
.gallery-table .inp { width: 100%; min-width: 0; box-sizing: border-box; }
.gallery-sheet {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding-top: 2px;
}
.gallery-tile {
  position: relative;
  height: 128px;
  overflow: hidden;
  border-radius: 14px;
  background: #E2E0D9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gallery-tile img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.gallery-tile-shade { position: absolute; inset: 0; background: rgba(28,27,25,.08); }
.gallery-tile:has(img) .gallery-tile-shade { background: linear-gradient(180deg, transparent 38%, rgba(0,0,0,.48)); }
.gallery-tile span { position: relative; z-index: 1; color: #A5A29A; font-size: 13px; text-align: center; padding: 10px; }
.gallery-tile:has(img) span { color: #fff; align-self: flex-end; width: 100%; text-shadow: 0 1px 3px rgba(0,0,0,.35); }
.gallery-tile small { display: block; font-size: 10px; margin-top: 3px; opacity: .82; }
.gallery-sheet-empty {
  height: 268px;
  border-radius: 14px;
  background: #F5F4F0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: var(--ink2);
}
.gallery-sheet-empty span { color: var(--ink3); font-size: 11px; }
.pv-phone {
  background: #F5F4F0;
  border-radius: 16px;
  padding: 8px 8px 10px;
}
.pv-status {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--ink3);
  padding: 2px 6px 8px;
}
.pv-banner {
  position: relative;
  height: 150px;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(28, 27, 25, 0.12);
  color: #fff;
}
.pv-banner.empty {
  background: #fff;
  border: 1px dashed rgba(28, 27, 25, 0.24);
  box-shadow: none;
  cursor: default;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--ink2);
  gap: 6px;
}
.pv-banner.empty b { font-size: 13px; font-weight: 600; }
.pv-banner.empty span { font-size: 11px; color: var(--ink3); }
.pv-in { position: absolute; left: 18px; top: 32px; }
.pv-in b { font-size: 19px; letter-spacing: 2px; display: block; }
.pv-in i { font-style: normal; font-size: 11px; opacity: 0.78; display: block; margin-top: 7px; letter-spacing: 1px; }
.pv-page {
  position: absolute;
  right: 12px;
  bottom: 11px;
  background: rgba(0, 0, 0, 0.42);
  color: #fff;
  font-size: 11px;
  border-radius: 20px;
  padding: 3px 10px;
}
.pv-dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 10px;
  display: flex;
  justify-content: center;
  gap: 5px;
}
.pv-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  display: block;
}
.pv-dots i.on { background: #fff; }
.pv-sheet {
  background: #fff;
  border-radius: 12px;
  padding: 12px;
}
.pv-pic {
  min-height: 56px;
  max-height: 220px;
  margin-top: 8px;
  border-radius: 8px;
  background: #EDEBE4;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--ink3);
  overflow: hidden;
}
.pv-pic img { width: 100%; height: auto; max-height: 220px; object-fit: contain; display: block; }
.faq-edit {
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #faf9f5;
}
.faq-edit-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.faq-answer {
  min-height: 78px;
  resize: vertical;
  line-height: 1.55;
}
.faq-empty {
  padding: 16px 4px;
  color: var(--ink3);
  line-height: 1.6;
}
.faq-preview-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
}
.faq-preview-item {
  padding: 10px 11px;
  border-radius: 10px;
  background: #f5f4f0;
}
.faq-preview-item b {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}
.faq-preview-item .tiny {
  line-height: 1.7;
  color: var(--ink2);
  white-space: pre-wrap;
}
.dlg {
  width: min(480px, 100%);
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.dlg-body {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--ink2);
}
.dlg-preview {
  display: block;
  margin-top: 6px;
  color: var(--ink3);
  font-size: 12px;
}
.dlg-actions {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 10px;
  margin-top: 20px;
}
.dlg-actions .btn { width: 100%; }
@media (max-width: 960px) {
  .content-grid { grid-template-columns: 1fr; }
}
</style>

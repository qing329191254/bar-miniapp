<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { api, uploadFile } from "../api";
import ImgField from "../components/ImgField.vue";
import IcoBtn from "../components/IcoBtn.vue";

const addInp = ref<HTMLInputElement | null>(null);
const tab = ref<"gallery" | "play">("gallery");
const content = ref<any>({
  gallery: { title: "店铺相册", items: [] },
  howToPlay: { title: "店铺玩法", sub: "", items: [], pic: "" },
});
const msg = ref("");
const msgError = ref(false);
let msgTimer: number | undefined;

function showTip(text: string, error = false) {
  window.clearTimeout(msgTimer);
  msg.value = text;
  msgError.value = error;
  msgTimer = window.setTimeout(() => { msg.value = ""; }, error ? 3500 : 1800);
}

onUnmounted(() => window.clearTimeout(msgTimer));

onMounted(async () => {
  const r = await api<any>("/admin/content");
  content.value = {
    gallery: r.gallery || { title: "店铺相册", items: [] },
    howToPlay: r.howToPlay || { title: "店铺玩法", sub: "", items: [], pic: "" },
  };
});

const g = computed(() => content.value.gallery);
const h = computed(() => content.value.howToPlay);
function isImg(v: string) {
  return !!v && (/^\/uploads\//.test(v) || /^https?:/.test(v) || v.startsWith("data:"));
}

async function save(part: string) {
  msg.value = "";
  try {
    await api("/admin/content", { method: "PUT", body: { data: { [part]: content.value[part] } } });
    showTip("已保存，小程序已同步");
  } catch (e: any) {
    showTip(e.message || "保存失败", true);
  }
}
function addPhoto() {
  addInp.value?.click();
}
async function onAddFiles(e: Event) {
  const files = [...((e.target as HTMLInputElement).files || [])];
  (e.target as HTMLInputElement).value = "";
  if (!files.length) return;
  msg.value = "";
  try {
    const items = g.value.items || [];
    for (const f of files) {
      const url = await uploadFile(f);
      const id = items.reduce((m: number, x: any) => Math.max(m, x.id || 0), 0) + 1;
      items.push({ id, name: f.name.replace(/\.[^.]+$/, ""), desc: "", url });
    }
    g.value.items = items;
  } catch (e: any) {
    showTip(e.message || "上传失败", true);
  }
}
function delPhoto(i: number) {
  if (!window.confirm("确认删除这张图片？小程序相册弹层会少一张。")) return;
  g.value.items.splice(i, 1);
}
function movePhoto(i: number, d: number) {
  const a = g.value.items;
  const j = i + d;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]];
}
function addPlay() {
  h.value.items = h.value.items || [];
  h.value.items.push("");
}
function delPlay(i: number) {
  if (!window.confirm("确认删除这条说明？")) return;
  h.value.items.splice(i, 1);
}
function movePlay(i: number, d: number) {
  const a = h.value.items;
  const j = i + d;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]];
}
</script>

<template>
  <div v-if="content">
    <div class="hdr">店铺相册与玩法 <em>小程序首页内容配置</em></div>
    <Transition name="tip-fade">
      <div v-if="msg" class="content-toast" :class="{ error: msgError }">{{ msg }}</div>
    </Transition>
    <div class="row" style="gap:8px;margin-bottom:11px;flex-wrap:wrap">
      <span class="chip" :class="{ on: tab==='gallery' }" @click="tab='gallery'">店铺相册 · {{ g.items?.length || 0 }} 张</span>
      <span class="chip" :class="{ on: tab==='play' }" @click="tab='play'">店铺玩法 · {{ h.items?.length || 0 }} 条</span>
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

  </div>
</template>

<style scoped>
.content-grid {
  display: grid;
  grid-template-columns: minmax(680px, 1fr) minmax(300px, 340px);
  gap: 16px;
  align-items: start;
}
.content-toast {
  position: fixed;
  top: 36%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 30;
  padding: 7px 12px;
  border: 1px solid rgba(59,109,17,.2);
  border-radius: 8px;
  background: rgba(234,243,222,.96);
  color: var(--green);
  font-size: 12px;
  line-height: 1.4;
  box-shadow: 0 5px 16px rgba(28,27,25,.1);
  pointer-events: none;
}
.content-toast.error { color: var(--red); background: rgba(252,235,235,.97); border-color: rgba(163,45,45,.2); }
.tip-fade-enter-active,.tip-fade-leave-active { transition: opacity .18s ease, transform .18s ease; }
.tip-fade-enter-from,.tip-fade-leave-to { opacity: 0; transform: translate(-50%, calc(-50% - 6px)); }
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
@media (max-width: 960px) {
  .content-grid { grid-template-columns: 1fr; }
}
</style>

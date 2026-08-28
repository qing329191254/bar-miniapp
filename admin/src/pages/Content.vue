<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, uploadFile } from "../api";
import ImgField from "../components/ImgField.vue";
import IcoBtn from "../components/IcoBtn.vue";

const addInp = ref<HTMLInputElement | null>(null);
const tab = ref<"gallery" | "play" | "faq" | "shop">("gallery");
const previewIdx = ref(0);
const grads = [
  "linear-gradient(120deg,#231A0C 0%,#4A3B1E 48%,#8A6A2F 100%)",
  "linear-gradient(120deg,#141B33 0%,#2A3E6B 55%,#4E6BB8 100%)",
  "linear-gradient(120deg,#3A2310 0%,#7A4A1D 55%,#C07A2B 100%)",
  "linear-gradient(120deg,#1B2A24 0%,#2E5347 55%,#4E8A75 100%)",
];
const content = ref<any>({
  gallery: { title: "店铺相册", items: [] },
  howToPlay: { title: "店铺玩法", sub: "", items: [], pic: "" },
  shopInfo: {},
  faq: { title: "常见问题", items: [] },
});
const msg = ref("");

onMounted(async () => {
  const r = await api<any>("/admin/content");
  content.value = {
    gallery: r.gallery || { title: "店铺相册", items: [] },
    howToPlay: r.howToPlay || { title: "店铺玩法", sub: "", items: [], pic: "" },
    shopInfo: r.shopInfo || {},
    faq: r.faq || { title: "常见问题", items: [] },
  };
});

const g = computed(() => content.value.gallery);
const h = computed(() => content.value.howToPlay);
const s = computed(() => content.value.shopInfo);
const f = computed(() => content.value.faq);
const miss = computed(() => {
  const x = s.value || {};
  const m: string[] = [];
  if (!String(x.name || "").trim()) m.push("门店名称");
  if (!String(x.addr || "").trim()) m.push("门店地址");
  if (!String(x.tel || "").trim()) m.push("联系电话");
  return m;
});
const cur = computed(() => {
  const items = g.value.items || [];
  if (!items.length) return null;
  return items[previewIdx.value % items.length];
});
function bannerStyle() {
  const it = cur.value;
  const i = previewIdx.value;
  if (it?.url) {
    return {
      backgroundImage: `linear-gradient(180deg,rgba(0,0,0,.12),rgba(0,0,0,.4)), url(${it.url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: grads[i % grads.length] };
}
function isImg(v: string) {
  return !!v && (/^\/uploads\//.test(v) || /^https?:/.test(v) || v.startsWith("data:"));
}

async function save(part: string) {
  msg.value = "";
  try {
    await api("/admin/content", { method: "PUT", body: { data: { [part]: content.value[part] } } });
    msg.value = "已保存，C 端同步";
  } catch (e: any) {
    msg.value = e.message;
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
    msg.value = e.message;
  }
}
function delPhoto(i: number) {
  if (!window.confirm("确认删除这张图片？C 端首页轮播会少一屏。")) return;
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
function addFaq() {
  f.value.items = f.value.items || [];
  f.value.items.push({ q: "", a: "" });
}
function delFaq(i: number) {
  f.value.items.splice(i, 1);
}
function nextBanner() {
  const n = g.value.items?.length || 0;
  if (n < 2) return;
  previewIdx.value = (previewIdx.value + 1) % n;
}
function selBanner(i: number) {
  previewIdx.value = i;
}

watch(
  () => g.value.items?.length || 0,
  (n) => {
    if (!n) previewIdx.value = 0;
    else if (previewIdx.value >= n) previewIdx.value = n - 1;
  },
);
</script>

<template>
  <div v-if="content">
    <div class="hdr">店铺相册与玩法 <em>C 端首页与「我的」内容配置</em></div>
    <p class="tiny" v-if="msg" style="color:#3B6D11;margin-bottom:8px">{{ msg }}</p>
    <div class="row" style="gap:8px;margin-bottom:11px;flex-wrap:wrap">
      <span class="chip" :class="{ on: tab==='gallery' }" @click="tab='gallery'">店铺相册 · {{ g.items?.length || 0 }} 张</span>
      <span class="chip" :class="{ on: tab==='play' }" @click="tab='play'">店铺玩法 · {{ h.items?.length || 0 }} 条</span>
      <span class="chip" :class="{ on: tab==='faq' }" @click="tab='faq'">常见问题 · {{ f.items?.length || 0 }} 条</span>
      <span class="chip" :class="{ on: tab==='shop' }" @click="tab='shop'">门店信息</span>
      <span class="tiny" style="margin-left:auto">改动保存后即时同步 C 端</span>
    </div>

    <div v-if="tab==='gallery'" class="content-grid">
      <div class="card">
        <div class="row" style="margin-bottom:11px">
          <b>相册图片</b>
          <span class="tiny" style="margin-left:8px">C 端首页 banner 按此顺序轮播</span>
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
          <tr v-if="!g.items?.length"><td colspan="5" class="tiny" style="text-align:center">暂无图片，C 端显示「商家尚未上传相册」</td></tr>
          </tbody>
        </table>
        <button class="btn" style="margin-top:10px" @click="save('gallery')">保存相册</button>
      </div>
      <div class="preview-col">
        <div class="card">
          <div class="st">C 端预览 <em>首页轮播 · 一张图一屏</em></div>
          <div class="pv-phone">
            <div class="pv-status"><span>玩咖</span><span>21:40 · 5G</span></div>
            <div
              v-if="g.items?.length"
              class="pv-banner"
              :style="bannerStyle()"
              @click="nextBanner"
            >
              <div class="pv-in">
                <b>{{ cur?.name }}</b>
                <i>{{ cur?.desc }}</i>
              </div>
              <div class="pv-dots" v-if="g.items.length > 1">
                <i
                  v-for="(_,i) in g.items"
                  :key="i"
                  :class="{ on: i === (previewIdx % g.items.length) }"
                  @click.stop="selBanner(i)"
                />
              </div>
              <span class="pv-page">{{ (previewIdx % g.items.length) + 1 }} / {{ g.items.length }}</span>
            </div>
            <div v-else class="pv-banner empty">
              <b>商家尚未上传相册</b>
              <span>保存后 C 端首页即时展示</span>
            </div>
            <div class="tiny" style="text-align:center;margin-top:8px">点击画面切换下一张</div>
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
        <div class="tiny" style="margin-top:4px">点击方块上传，C 端玩法页展示</div>
        <button class="btn" style="margin-top:10px" @click="save('howToPlay')">保存玩法</button>
      </div>
      <div>
        <div class="card">
          <div class="st">C 端预览 <em>玩法弹层</em></div>
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
        <div class="note">入口：C 端首页「店铺玩法」。这里是给顾客看的说明，不要与对局项目配置（碎片/人数）混淆。</div>
      </div>
    </div>

    <div v-if="tab==='faq'" class="card">
      <div class="row" style="margin-bottom:11px">
        <b>常见问题</b>
        <button class="btn gold" style="margin-left:auto" @click="addFaq">＋ 添加一条</button>
      </div>
      <div class="card" v-for="(it,i) in f.items" :key="i" style="background:#FAF9F5">
        <div class="tiny">问题</div>
        <input class="inp" v-model="it.q" placeholder="如 金币可以退款吗？" />
        <div class="tiny">回答</div>
        <textarea class="inp" style="height:72px" v-model="it.a" />
        <IcoBtn name="trash" title="删除" @click="delFaq(i)" />
      </div>
      <button class="btn" @click="save('faq')">保存常见问题</button>
      <div class="note" style="margin-top:10px">入口：C 端「我的 → 帮助与联系 → 常见问题」。</div>
    </div>

    <div v-if="tab==='shop'" class="content-grid">
      <div class="card">
        <div class="note rd" v-if="miss.length">门店信息未配置完整，小程序无法上线。缺少：{{ miss.join(" / ") }}</div>
        <div class="tiny">门店名称 *上线必填</div>
        <input class="inp" v-model="s.name" placeholder="如 玩咖桌游酒吧（万象城店）" />
        <div class="tiny">门店地址 *上线必填</div>
        <input class="inp" v-model="s.addr" placeholder="精确到楼层与铺号" />
        <div class="tiny">联系电话 *上线必填</div>
        <input class="inp" v-model="s.tel" placeholder="须为常有人接的号码" />
        <div class="tiny">营业时间</div>
        <input class="inp" v-model="s.hours" placeholder="如 周一至周日 14:00 - 次日 02:00" />
        <div class="tiny">门店公告</div>
        <textarea class="inp" style="height:78px" v-model="s.notice" placeholder="合规提示与预约须知" />
        <button class="btn" @click="save('shopInfo')">保存门店信息</button>
      </div>
      <div>
        <div class="card">
          <div class="st">C 端预览 <em>我的 → 联系店员</em></div>
          <div class="pv-phone">
            <div class="pv-status"><span>玩咖</span><span>21:40 · 5G</span></div>
            <div class="pv-sheet">
              <b>{{ s.name || "（未配置门店名称）" }}</b>
              <div class="tiny" style="line-height:1.9;margin-top:6px">
                地址：{{ s.addr || "—" }}<br />
                电话：{{ s.tel || "—" }}<br />
                营业：{{ s.hours || "—" }}
              </div>
              <div class="tiny" v-if="s.notice" style="margin-top:7px;padding-top:7px;border-top:1px solid rgba(28,27,25,.12)">{{ s.notice }}</div>
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
  height: 56px;
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
.pv-pic img { width: 100%; height: 100%; object-fit: cover; display: block; }
@media (max-width: 960px) {
  .content-grid { grid-template-columns: 1fr; }
}
</style>

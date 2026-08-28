<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, media } from "@/utils/api";

const WEEK_HEAD = ["一", "二", "三", "四", "五", "六", "日"];

const data = ref(null);
const bannerIdx = ref(0);
const msg = ref("");
const showGallery = ref(false);
const showSign = ref(false);
const showPlay = ref(false);
const signing = ref(false);
let timer = null;
const grads = [
  "linear-gradient(120deg,#231A0C 0%,#4A3B1E 48%,#8A6A2F 100%)",
  "linear-gradient(120deg,#141B33 0%,#2A3E6B 55%,#4E6BB8 100%)",
  "linear-gradient(120deg,#3A2310 0%,#7A4A1D 55%,#C07A2B 100%)",
  "linear-gradient(120deg,#1B2A24 0%,#2E5347 55%,#4E8A75 100%)",
];

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

async function load() {
  data.value = await api("/home");
}

onShow(load);
onMounted(() => {
  timer = setInterval(() => {
    const n = gallery.value.length;
    if (n > 1) bannerIdx.value = (bannerIdx.value + 1) % n;
  }, 4000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});

const gallery = computed(() => {
  const g = data.value?.gallery;
  const items = Array.isArray(g) ? g : g?.items || [];
  return items.map((it, i) => ({
    t: it.name || "店铺相册",
    s: it.desc || "玩咖桌游酒吧",
    g: grads[i % grads.length],
    url: it.url ? media(it.url) : "",
  }));
});
const galleryTitle = computed(() => {
  const g = data.value?.gallery;
  if (g && !Array.isArray(g) && g.title) return g.title;
  return "店铺相册";
});

function openGallery() {
  if (!gallery.value.length) return;
  showGallery.value = true;
}
function closeGallery() {
  showGallery.value = false;
}
function preview(i) {
  const urls = gallery.value.map((x) => x.url).filter(Boolean);
  if (!urls.length) return;
  uni.previewImage({ urls, current: gallery.value[i]?.url || urls[0] });
}

const PLAY_DEFAULT = {
  title: "店铺玩法",
  sub: "桌游规则与场地",
  items: [
    "狼人杀 8-12 人，每局约 2 小时",
    "德州扑克 6-9 人，提供筹码与牌具",
    "台球 8 球，2-4 人",
    "剧本杀 6-8 人，需提前预约",
    "场地提供卡座 / 散台 / 吧台区域",
  ],
  pic: "场地示意图",
};

function isPicUrl(v) {
  return v && (/^\/uploads\//.test(v) || /^https?:/.test(v));
}

const play = computed(() => {
  const h = data.value?.howToPlay;
  if (!h || Array.isArray(h)) {
    return {
      title: PLAY_DEFAULT.title,
      sub: PLAY_DEFAULT.sub,
    };
  }
  return {
    title: h.title || PLAY_DEFAULT.title,
    sub: h.sub || PLAY_DEFAULT.sub,
  };
});

const howToPlay = computed(() => {
  const h = data.value?.howToPlay;
  if (!h || Array.isArray(h)) {
    return {
      ...PLAY_DEFAULT,
      items: Array.isArray(h) && h.length ? h : PLAY_DEFAULT.items,
      picUrl: "",
    };
  }
  const picRaw = h.picUrl || h.pic || "";
  return {
    title: h.title || PLAY_DEFAULT.title,
    sub: h.sub || PLAY_DEFAULT.sub,
    items: (h.items || []).length ? h.items : PLAY_DEFAULT.items,
    pic: isPicUrl(picRaw) ? "" : (h.pic || ""),
    picUrl: isPicUrl(picRaw) ? media(picRaw) : "",
  };
});

function openPlaySheet() {
  showPlay.value = true;
}
function closePlaySheet() {
  showPlay.value = false;
}
function previewPlayPic() {
  if (!howToPlay.value.picUrl) return;
  uni.previewImage({ urls: [howToPlay.value.picUrl] });
}

const signedSet = computed(() => new Set(data.value?.signed || []));
const signPoints = computed(() => Number(data.value?.signPoints || 0));
const streak = computed(() => Number(data.value?.streak || 0));
const signRules = computed(() => data.value?.signRules || []);
const signedToday = computed(() => !!data.value?.signedToday);
const signDate = computed(() => {
  const [year, month] = String(data.value?.signMonth || "").split("-").map(Number);
  const now = new Date();
  return {
    year: year || now.getFullYear(),
    month: month || now.getMonth() + 1,
    today: Number(data.value?.signToday || now.getDate()),
  };
});
const monthLabel = computed(() => `${signDate.value.year} 年 ${signDate.value.month} 月`);

const calCells = computed(() => {
  const { year, month, today } = signDate.value;
  const offset = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells = [];
  for (let i = 0; i < offset; i++) cells.push({ kind: "nil" });
  for (let d = 1; d <= daysInMonth; d++) {
    let kind = "fut";
    if (signedSet.value.has(d)) kind = "ok";
    else if (d < today) kind = "no";
    else if (d === today) kind = "now";
    cells.push({ kind, day: d });
  }
  return cells;
});

const nextHit = computed(() => {
  if (signedToday.value) return null;
  return signRules.value.find((r) => r.days === streak.value + 1) || null;
});

function ruleReward(r) {
  const pts = r.pts > 0 ? "+" + fmt(r.pts) + " 分" : "";
  const cards = (r.cards || []).map((c) => c.name + " ×" + c.qty).join("、");
  if (pts && cards) return pts + " + " + cards;
  return pts || cards || "—";
}

function openSignSheet() {
  showSign.value = true;
  msg.value = "";
}
function closeSignSheet() {
  showSign.value = false;
}

async function doSign() {
  if (signedToday.value || signing.value) return;
  signing.value = true;
  msg.value = "";
  try {
    const r = await api("/signin", { method: "POST" });
    let tip = "签到成功，+" + fmt(r.points) + " 积分";
    if (r.extraPts) tip += " · 连签 " + r.streak + " 天额外 +" + fmt(r.extraPts) + " 分";
    if (r.cards?.length) tip += " · 得卡券 " + r.cards.join("、");
    uni.showToast({ title: tip, icon: "none", duration: 2500 });
    data.value = await api("/home");
  } catch (e) {
    msg.value = e.message;
  } finally {
    signing.value = false;
  }
}
</script>

<template>
  <view class="pbody" v-if="data">
    <view
      class="home-b"
      :class="{ 'has-img': !!gallery[bannerIdx].url }"
      v-if="gallery.length"
      :style="gallery[bannerIdx].url
        ? { backgroundImage: 'url(' + gallery[bannerIdx].url + ')' }
        : { background: gallery[bannerIdx].g }"
      @tap="openGallery"
    >
      <view class="home-b-in">
        <view class="home-bt">{{ gallery[bannerIdx].t }}</view>
        <view class="home-bs">{{ gallery[bannerIdx].s }}</view>
      </view>
      <view class="home-b-page">{{ bannerIdx + 1 }} / {{ gallery.length }}</view>
    </view>
    <view class="home-b empty-b" v-else>
      <view style="text-align:center">
        <view style="font-size:13px;color:#6B6A65">商家尚未上传相册</view>
      </view>
    </view>

    <view class="home-kg">
      <view class="kg-i" @tap="go('/pages/c/order')">
        <view class="ic" style="background:linear-gradient(135deg,#3EAF8E,#9FE1CB)">点</view>
        <text>点单</text>
      </view>
      <view class="kg-i" @tap="go('/pages/c/cards')">
        <view class="ic" style="background:linear-gradient(135deg,#4E8ED9,#B5D4F4)">卡</view>
        <text>用卡</text>
      </view>
      <view class="kg-i" @tap="go('/pages/c/points')">
        <view class="ic" style="background:linear-gradient(135deg,#D96A96,#F4C0D1)">分</view>
        <text>积分</text>
      </view>
      <view class="kg-i" @tap="openSignSheet">
        <view class="ic" style="background:linear-gradient(135deg,#7FA94F,#C0DD97)">签</view>
        <text>{{ data.signedToday ? "已签" : "签到" }}</text>
      </view>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>

    <view class="home-op" @tap="openPlaySheet">
      <view class="home-ic" style="background:linear-gradient(135deg,#8F87E0,#CECBF6)">玩</view>
      <view class="home-txt">
        <view class="ht">{{ play.title }}</view>
        <view class="hs">{{ play.sub }}</view>
      </view>
      <text class="home-arr">›</text>
    </view>
    <view class="home-op" @tap="go('/pages/c/recharge')">
      <view class="home-ic" style="background:linear-gradient(135deg,#E89A3C,#FAC775)">充</view>
      <view class="home-txt">
        <view class="ht">充值有奖</view>
        <view class="hs">充多送多</view>
      </view>
      <text class="home-arr">›</text>
    </view>
    <tab-bar current="home" />

    <view v-if="showGallery" class="gal-mask" @tap="closeGallery" @touchmove.stop.prevent></view>
    <view v-if="showGallery" class="gal-sheet" @touchmove.stop>
      <view class="gal-hd">
        <text class="gal-title">{{ galleryTitle }}</text>
        <text class="gal-close" @tap="closeGallery">关闭</text>
      </view>
      <scroll-view scroll-y class="gal-body">
        <view class="gal-grid">
          <view v-for="(it, i) in gallery" :key="i" class="gal-cell" @tap.stop="preview(i)">
            <image v-if="it.url" class="gal-img" :src="it.url" mode="aspectFill" />
            <view v-else class="gal-ph">
              <text>{{ it.t }}</text>
              <text v-if="it.s" class="gal-desc">{{ it.s }}</text>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view v-if="showSign" class="gal-mask" @tap="closeSignSheet" @touchmove.stop.prevent></view>
    <view v-if="showSign" class="sign-sheet" @touchmove.stop>
      <scroll-view scroll-y class="sign-body">
        <view class="sign-hd">
          <text>{{ monthLabel }}</text>
          <text class="sign-sub">本月已签 {{ (data.signed || []).length }} 天</text>
        </view>
        <view class="cal">
          <view v-for="w in WEEK_HEAD" :key="w" class="cw">{{ w }}</view>
          <view
            v-for="(c, i) in calCells"
            :key="i"
            class="cd"
            :class="c.kind"
          >{{ c.day || "" }}</view>
        </view>
        <view class="sign-legend">
          <view class="tiny leg"><view class="leg-i ok"></view><text>已签</text></view>
          <view class="tiny leg"><view class="leg-i no"></view><text>漏签</text></view>
          <view class="tiny leg"><view class="leg-i now"></view><text>今日</text></view>
        </view>

        <view class="card sign-reward">
          <view class="between">
            <text class="tiny blue-t">今日签到可得</text>
            <text class="sign-pts">+{{ fmt(signPoints) }} 积分</text>
          </view>
          <view v-if="nextHit" class="sign-extra">
            <text class="tiny blue-t">连签 {{ streak + 1 }} 天额外奖励</text>
            <text class="sign-extra-r">{{ ruleReward(nextHit) }}</text>
          </view>
        </view>

        <view v-if="signRules.length" class="card sign-streak">
          <view class="between" style="margin-bottom:6px">
            <text class="tiny">已连续签到</text>
            <text class="streak-num">{{ streak }} 天</text>
          </view>
          <view v-for="r in signRules" :key="r.id" class="between rule-row">
            <text class="tiny" :class="streak >= r.days ? 'done' : 'todo'">
              {{ streak >= r.days ? "✓" : "○" }} 连续 {{ r.days }} 天
            </text>
            <text class="tiny rule-rw" :class="streak >= r.days ? 'done' : ''">
              {{ ruleReward(r) }}{{ streak >= r.days ? "" : " · 还差 " + (r.days - streak) + " 天" }}
            </text>
          </view>
        </view>

        <button
          class="btn block"
          :class="{ off: signedToday }"
          :disabled="signedToday || signing"
          @tap="doSign"
        >{{ signedToday ? "今日已签到" : "签到" }}</button>
        <view class="note sign-note">
          签到积分直接入库，同样受<text style="font-weight:600">月底清零</text>约束。漏签不可补签，<text style="font-weight:600">断签后连续天数从 1 重新累计</text>。
        </view>
        <view class="err" v-if="msg">{{ msg }}</view>
      </scroll-view>
    </view>

    <view v-if="showPlay" class="gal-mask" @tap="closePlaySheet" @touchmove.stop.prevent></view>
    <view v-if="showPlay" class="gal-sheet play-sheet" @touchmove.stop>
      <view class="gal-hd">
        <text class="gal-title">{{ howToPlay.title }}</text>
        <text class="gal-close" @tap="closePlaySheet">关闭</text>
      </view>
      <scroll-view scroll-y class="play-body">
        <view class="card play-card">
          <view style="font-weight:600;font-size:13px">{{ howToPlay.sub }}</view>
          <view class="play-list">
            <view v-for="(line, i) in howToPlay.items" :key="i" class="play-line">· {{ line }}</view>
          </view>
        </view>
        <image
          v-if="howToPlay.picUrl"
          class="play-pic"
          :src="howToPlay.picUrl"
          mode="widthFix"
          @tap="previewPlayPic"
        />
        <view v-else-if="howToPlay.pic" class="play-ph">{{ howToPlay.pic }}</view>
      </scroll-view>
    </view>
  </view>
</template>

<style scoped>
.gal-mask {
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(0,0,0,.35);
  z-index: 100;
}
.gal-sheet {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  border-radius: 18px 18px 0 0;
  padding: 15px 16px 24px;
  z-index: 101;
  max-height: 78%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  animation: gal-up .28s ease;
}
@keyframes gal-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
.gal-hd {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}
.gal-title { font-size: 14px; font-weight: 600; }
.gal-close { margin-left: auto; font-size: 13px; color: #9C9A93; }
.gal-body { max-height: 62vh; }
.gal-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.gal-cell {
  width: calc(50% - 5px);
  height: 100px;
  border-radius: 10px;
  overflow: hidden;
  background: linear-gradient(135deg, #E8E6DF, #D8D5CC);
}
.gal-img { width: 100%; height: 100%; display: block; }
.gal-ph {
  width: 100%; height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #9C9A93;
  text-align: center;
  padding: 8px;
  box-sizing: border-box;
}
.gal-desc { font-size: 10px; opacity: .7; margin-top: 2px; }

.sign-sheet {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  border-radius: 18px 18px 0 0;
  padding: 15px 16px 24px;
  z-index: 101;
  max-height: 88%;
  box-sizing: border-box;
  animation: gal-up .28s ease;
}
.sign-body { max-height: 80vh; }
.sign-hd {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}
.sign-sub { font-size: 11px; color: #9C9A93; font-weight: 400; margin-left: auto; }
.cal {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 10px;
}
.cw { font-size: 11px; color: #9C9A93; text-align: center; padding-bottom: 2px; }
.cd {
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.cd.ok { background: #EAF3DE; color: #3B6D11; border: 1px solid #97C459; }
.cd.no { background: #EEECE5; color: #9C9A93; }
.cd.now { background: #1C1B19; color: #fff; font-weight: 500; }
.cd.fut { background: #F7F6F2; color: #C6C4BD; }
.cd.nil { background: transparent; }
.sign-legend { display: flex; gap: 12px; margin-bottom: 11px; }
.leg { display: flex; align-items: center; }
.leg-i {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 2px;
  margin-right: 4px;
}
.leg-i.ok { background: #EAF3DE; border: 1px solid #97C459; }
.leg-i.no { background: #EEECE5; }
.leg-i.now { background: #1C1B19; }
.sign-reward {
  background: #E6F1FB;
  border-color: #185FA5;
  padding: 10px 12px;
  margin-bottom: 11px;
}
.blue-t { color: #185FA5; }
.sign-pts { color: #0C447C; font-weight: 600; }
.sign-extra {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed rgba(24, 95, 165, 0.25);
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.sign-extra-r { color: #0C447C; font-size: 12px; font-weight: 600; text-align: right; flex: 1; }
.sign-streak { padding: 10px 12px; margin-bottom: 11px; }
.streak-num { color: #3B6D11; font-weight: 600; }
.rule-row { padding: 3px 0; gap: 8px; }
.rule-rw { margin-left: auto; text-align: right; color: #6B6A65; flex: 1; }
.tiny.done { color: #3B6D11; }
.tiny.todo { color: #9C9A93; }
.btn.off { background: #EDEBE4; color: #9C9A93; }
.sign-note { margin-top: 11px; margin-bottom: 4px; }

.play-sheet { max-height: 72%; }
.play-body { max-height: 58vh; }
.play-card { padding: 12px 14px; margin-bottom: 11px; }
.play-list { margin-top: 5px; line-height: 1.8; }
.play-line { font-size: 13px; color: #6B6A65; }
.play-ph {
  height: 90px;
  border-radius: 10px;
  background: linear-gradient(135deg, #E8E6DF, #D8D5CC);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #9C9A93;
}
.play-pic {
  width: 100%;
  height: auto;
  border-radius: 10px;
  display: block;
}
</style>

<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, clearSession, go, relaunch } from "@/utils/api";

const me = ref(null);
const champs = ref({ list: [], total: 0, month: 0 });
const team = ref(null);
const showShop = ref(false);
const showFaq = ref(false);
const showTerms = ref(false);
const showPrivacy = ref(false);
const showDeact = ref(false);
const deactReason = ref("");
const deactMsg = ref("");

const TERMS_TEXT_DEFAULT = `一、协议主体与适用范围：您与玩咖桌游酒吧就使用本店微信小程序会员服务达成的协议。
二、账号注册与信息收集：收集微信昵称头像（展示身份）、手机号（绑定会员与订单）、性别/姓名（选填，姓名仅线下核销核对）。存储至注销后 6 个月。
三、金币规则：1 元=1 金币；本金金币可退，赠送金币不可退/提现/转让；消费优先扣本金；充值需到吧台付款由店员确认后到账，30 分钟未付自动关闭。
四、积分规则：对局与签到获得；每月最后一日 24:00 清零不结转；不可兑换现金。积分提取需生成提分单并由店员当面确认发放：30 分钟未确认自动关闭，冻结积分全额退回可用、不予没收；同一用户 24 小时内达到 3 次超时未确认的，暂停其提交提分单，随时间自然恢复、无需申请；提分单冻结期间的积分不参与月末清零，待单据终结后再按当时规则处理。
五、碎片规则：荣誉值，仅用于周榜排名与周奖励评定。
六、卡券规则：游戏卡/酒水卡 30 天有效，宝箱卡 7 天有效，过期作废不补偿；核销码 5 分钟有效。
七、订单与消费：金币支付订单店员接单时扣款，拒单全额退回；到吧台付款 30 分钟超时关闭。
八、战队：由本店分组，会员不可自建或申请加入。
九、账号注销：可在小程序内提交注销申请，由店长核对资产结清后执行；积分碎片清零、卡券作废、本金金币可退、赠送不退；个人信息 6 个月内删除。
十、争议解决：适用中华人民共和国法律，协商不成向本店所在地法院起诉。`;

const PRIVACY_TEXT_DEFAULT = `一、收集信息：微信昵称头像（必需）、手机号（必需）、性别与姓名（选填）。自动收集：OpenID、订单信息、对局记录、操作日志。
二、不收集：精确地理位置、通讯录/相册/麦克风权限（扫码时主动调起）、微信好友关系、支付账户信息（不接入线上支付）。
三、使用目的：提供服务、客户服务、匿名经营分析；不做自动化决策与精准营销。
四、对外提供：昵称头像在排行榜展示；订单状态、待办数量等必要业务信息通过微信公众平台服务商下发订阅消息；不出售个人信息。
五、存储：境内存储，注销后 6 个月内删除。
六、您的权利：查阅更正、查看资产明细、申请注销、撤回授权、投诉举报。
七、未成年人保护：本店为酒类经营场所，未成年人不得饮酒。
八、联系我们：门店名称、地址、电话见「我的 → 帮助与联系 → 联系店员」，15 个工作日内答复。`;

const SHOP_DEFAULT = {
  name: "玩咖桌游酒吧（万象城店）",
  addr: "广州市天河区天河路 208 号万象城 B2-17",
  tel: "020-8866 2043",
  hours: "周一至周日 14:00 - 次日 02:00（最后入场 01:00）",
  notice: "本店为酒类经营场所，未成年人不得饮酒。桌游包桌建议提前一天电话预约。",
};

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
      a: "积分有效期为自然月，每月最后一日 24:00 清零，不结转到下月。请在月底前兑换卡券或到吧台提取。",
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

onShow(async () => {
  me.value = await api("/me");
  try {
    champs.value = await api("/champions");
  } catch (e) {}
  if (me.value?.user?.teamId) {
    try {
      team.value = await api("/teams/" + me.value.user.teamId);
    } catch (e) {}
  }
});

function fmt(n) {
  const x = Number(n) || 0;
  return x.toLocaleString("en-US");
}
function logout() {
  clearSession();
  relaunch("/pages/login/login");
}
function gender(g) {
  return g === 1 ? "男" : g === 2 ? "女" : "未知";
}
const lastChamp = computed(() => {
  const d = champs.value.list?.[0]?.date;
  return d ? String(d).slice(5) : "—";
});

const shop = computed(() => {
  const s = me.value?.shop || {};
  return {
    name: s.name || SHOP_DEFAULT.name,
    addr: s.addr || SHOP_DEFAULT.addr,
    tel: s.tel || SHOP_DEFAULT.tel,
    hours: s.hours || SHOP_DEFAULT.hours,
    notice: s.notice || SHOP_DEFAULT.notice,
  };
});

function openShopSheet() {
  showShop.value = true;
}
function closeShopSheet() {
  showShop.value = false;
}
function callShop() {
  const tel = shop.value.tel;
  if (!tel) {
    uni.showToast({ title: "商家尚未配置联系电话", icon: "none" });
    return;
  }
  uni.makePhoneCall({ phoneNumber: tel.replace(/\s/g, "") });
}

const faq = computed(() => {
  const f = me.value?.content?.faq || {};
  const items = (f.items || []).length ? f.items : FAQ_DEFAULT.items;
  return {
    title: f.title || FAQ_DEFAULT.title,
    sub: f.sub || FAQ_DEFAULT.sub,
    items,
  };
});

const faqSub = computed(() => {
  const n = faq.value.items.length;
  return n ? `${n} 条 · 金币、积分与卡券规则` : "商家尚未配置";
});

function openFaqSheet() {
  showFaq.value = true;
}
function closeFaqSheet() {
  showFaq.value = false;
}

const terms = computed(() => {
  const doc = me.value?.agreements?.terms || {};
  const text = String(doc.text || "").trim();
  return {
    title: doc.title || "玩咖会员服务协议",
    ver: doc.ver || 2,
    pub: doc.pub || "08-20 14:30",
    text: text || TERMS_TEXT_DEFAULT,
  };
});

const termsSub = computed(() => {
  let s = `当前生效 v${terms.value.ver}`;
  const agreed = me.value?.user?.agreedVersion;
  if (agreed != null) s += ` · 你已同意 v${agreed}`;
  return s;
});

const termsMeta = computed(() => {
  let s = `当前生效版本 v${terms.value.ver} · ${terms.value.pub} 发布`;
  const agreed = me.value?.user?.agreedVersion;
  if (agreed != null) s += ` · 你已同意 v${agreed}`;
  return s;
});

function openTermsSheet() {
  showTerms.value = true;
}
function closeTermsSheet() {
  showTerms.value = false;
}

const privacy = computed(() => {
  const doc = me.value?.agreements?.privacy || {};
  const text = String(doc.text || "").trim();
  return {
    title: doc.title || "玩咖隐私政策",
    ver: doc.ver || 1,
    pub: doc.pub || "06-01 09:00",
    text: text || PRIVACY_TEXT_DEFAULT,
  };
});

const privacySub = computed(() => `当前生效 v${privacy.value.ver} · 信息收集与使用说明`);

const privacyMeta = computed(() => `当前生效版本 v${privacy.value.ver} · ${privacy.value.pub} 发布`);

function openPrivacySheet() {
  showPrivacy.value = true;
}
function closePrivacySheet() {
  showPrivacy.value = false;
}

const deactPending = computed(() => me.value?.user?.deact === "DEACTIVATE_PENDING");

const deactAssets = computed(() => {
  const u = me.value?.user;
  if (!u) return { coinP: 0, coinB: 0, point: 0, shard: 0, cards: 0 };
  return {
    coinP: u.coin?.p || 0,
    coinB: u.coin?.b || 0,
    point: u.point?.av || 0,
    shard: u.shard?.w || 0,
    cards: me.value?.usableCards || 0,
  };
});

function openDeactDlg() {
  if (deactPending.value) {
    uni.showToast({ title: "注销申请已提交，请到店由店长核对资产结清", icon: "none" });
    return;
  }
  deactReason.value = "";
  deactMsg.value = "";
  showDeact.value = true;
}
function closeDeactDlg() {
  showDeact.value = false;
}
async function submitDeact() {
  const reason = (deactReason.value || "").trim();
  if (!reason) {
    deactMsg.value = "请填写注销原因";
    return;
  }
  deactMsg.value = "";
  try {
    await api("/deactivate", { method: "POST", body: { reason } });
    showDeact.value = false;
    uni.showToast({ title: "注销申请已提交，请到店由店长核对资产结清", icon: "none", duration: 2500 });
    me.value = await api("/me");
  } catch (e) {
    deactMsg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody" v-if="me">
    <view class="profile-hd">
      <view class="row">
        <view class="ph-lg">{{ me.user.av }}</view>
        <view style="margin-left:12px;flex:1">
          <view style="font-size:17px;font-weight:600;letter-spacing:.5px">{{ me.user.nick }}</view>
          <view class="tiny" style="color:rgba(255,255,255,.72);margin-top:2px">{{ me.user.phone }} · {{ gender(me.user.gender) }}</view>
          <view class="row" style="margin-top:6px">
            <text class="pill-w">会员 {{ me.user.no }}</text>
            <text class="pill-w" v-if="me.user.teamName" style="color:#CECBF6">{{ me.user.teamName }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="asset-card">
      <view class="asset-grid">
        <view class="asset" @tap="go('/pages/c/recharge')">
          <view class="ab gold">{{ fmt(me.user.coin.total) }}</view>
          <text>金币</text>
        </view>
        <view class="asset" @tap="go('/pages/c/points')">
          <view class="ab" :style="{ color: me.user.point.av < 0 ? '#A32D2D' : '#185FA5' }">{{ fmt(me.user.point.av) }}</view>
          <text>积分</text>
        </view>
        <view class="asset" @tap="go('/pages/c/cards')">
          <view class="ab" style="color:#534AB7">{{ me.usableCards }} 张</view>
          <text>卡包</text>
        </view>
        <view class="asset" @tap="go('/pages/c/shard')">
          <view class="ab" style="color:#3B6D11">{{ fmt(me.user.shard.w) }}</view>
          <text>碎片</text>
        </view>
      </view>
    </view>

    <view class="honor-grid">
      <view class="honor g">
        <view>我的冠军</view>
        <view class="hv">{{ champs.total }}</view>
        <view class="hl">累计夺冠 · 本月 {{ champs.month }} · 最近 {{ lastChamp }}</view>
      </view>
      <view class="honor gn">
        <view>{{ me.user.teamName || "（暂无战队）" }}</view>
        <view class="hv">{{ team ? team.champs + " 冠" : "—" }}</view>
        <view class="hl">{{ team ? (team.members?.length || 0) + " 名成员" : "可联系店员加入" }}</view>
      </view>
    </view>

    <view class="card">
      <view class="h2">我的订单</view>
      <view class="g3">
        <button class="btn ghost" @tap="go('/pages/c/orders')">金币订单</button>
        <button class="btn ghost" @tap="go('/pages/c/cards')">卡包订单</button>
        <button class="btn ghost" @tap="go('/pages/c/points')">积分订单</button>
      </view>
    </view>

    <view class="card">
      <view class="h2">帮助与联系</view>
      <view class="li" @tap="openShopSheet">
        <view class="av">店</view>
        <view class="gr"><view style="font-weight:500">联系店员</view><view class="tiny">{{ me.shop?.tel ? "地址、电话与营业时间" : "商家尚未配置门店信息" }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="openFaqSheet">
        <view class="av">问</view>
        <view class="gr"><view style="font-weight:500">常见问题</view><view class="tiny">{{ faqSub }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="openTermsSheet">
        <view class="av">议</view>
        <view class="gr"><view style="font-weight:500">用户协议</view><view class="tiny">{{ termsSub }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li" @tap="openPrivacySheet">
        <view class="av">隐</view>
        <view class="gr"><view style="font-weight:500">隐私政策</view><view class="tiny">{{ privacySub }}</view></view>
        <text class="tiny">›</text>
      </view>
      <view class="li deact-li" @tap="openDeactDlg">
        <view class="av deact-av">注</view>
        <view class="gr">
          <view style="font-weight:600" :style="{ color: deactPending ? '#BA7517' : '#A32D2D' }">注销账号</view>
          <view class="tiny">{{ deactPending ? "申请已提交 · 待店长核对资产结清" : "清空资产并注销会员，操作不可恢复" }}</view>
        </view>
        <text v-if="deactPending" class="pill deact-pill">处理中</text>
        <text v-else class="tiny">›</text>
      </view>
      <view class="tiny deact-foot">协议为常驻入口，可随时查看当前生效版本全文与你的同意记录。</view>
    </view>

    <button class="btn ghost block" @tap="logout">切换账号</button>
    <tab-bar current="mine" />

    <view v-if="showShop" class="shop-mask" @tap="closeShopSheet" @touchmove.stop.prevent></view>
    <view v-if="showShop" class="shop-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">联系店员</text>
        <text class="shop-close" @tap="closeShopSheet">关闭</text>
      </view>
      <scroll-view scroll-y class="shop-body">
        <view class="card shop-card">
          <view style="font-weight:600;font-size:14px">{{ shop.name }}</view>
          <view class="shop-line">
            <text class="tiny shop-k">地址</text>
            <text class="shop-v">{{ shop.addr }}</text>
          </view>
          <view class="shop-line">
            <text class="tiny shop-k">电话</text>
            <text class="shop-v">{{ shop.tel }}</text>
          </view>
          <view class="shop-line">
            <text class="tiny shop-k">营业</text>
            <text class="shop-v">{{ shop.hours }}</text>
          </view>
        </view>
        <view v-if="shop.notice" class="card shop-notice">
          <view class="tiny shop-notice-t">{{ shop.notice }}</view>
        </view>
        <button class="btn block" :disabled="!shop.tel" @tap="callShop">
          {{ shop.tel ? "拨打电话" : "暂无联系电话" }}
        </button>
        <view class="note shop-tip">
          资产、订单与卡券的问题请到吧台当面处理——积分提取、卡券核销与本金退还都需要当面核对，电话无法完成。
        </view>
      </scroll-view>
    </view>

    <view v-if="showFaq" class="shop-mask" @tap="closeFaqSheet" @touchmove.stop.prevent></view>
    <view v-if="showFaq" class="shop-sheet faq-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">{{ faq.title }}</text>
        <text class="shop-close" @tap="closeFaqSheet">关闭</text>
      </view>
      <scroll-view scroll-y class="faq-body">
        <view class="tiny faq-sub">{{ faq.sub }} · 共 {{ faq.items.length }} 条</view>
        <view v-if="faq.items.length" class="faq-list">
          <view v-for="(it, i) in faq.items" :key="i" class="card faq-item">
            <view style="font-weight:600;font-size:13px">{{ i + 1 }}. {{ it.q }}</view>
            <view class="tiny faq-a">{{ it.a }}</view>
          </view>
        </view>
        <view v-else class="card tiny" style="text-align:center;padding:24px">商家尚未配置常见问题</view>
        <view class="note faq-tip">以上口径与《用户协议》一致。若店员口述与此处不符，请以协议全文为准并向店长反馈。</view>
      </scroll-view>
    </view>

    <view v-if="showTerms" class="shop-mask" @tap="closeTermsSheet" @touchmove.stop.prevent></view>
    <view v-if="showTerms" class="shop-sheet terms-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">{{ terms.title }} v{{ terms.ver }}</text>
        <text class="shop-close" @tap="closeTermsSheet">关闭</text>
      </view>
      <scroll-view scroll-y class="terms-body">
        <view class="tiny terms-meta">{{ termsMeta }}</view>
        <view class="terms-text">{{ terms.text }}</view>
        <view class="note terms-tip">
          协议为常驻可查入口，历史版本与你的同意记录由本店永久保留。如对条款有疑问可到吧台咨询店员。
        </view>
      </scroll-view>
    </view>

    <view v-if="showPrivacy" class="shop-mask" @tap="closePrivacySheet" @touchmove.stop.prevent></view>
    <view v-if="showPrivacy" class="shop-sheet terms-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">{{ privacy.title }} v{{ privacy.ver }}</text>
        <text class="shop-close" @tap="closePrivacySheet">关闭</text>
      </view>
      <scroll-view scroll-y class="terms-body">
        <view class="tiny terms-meta">{{ privacyMeta }}</view>
        <view class="terms-text">{{ privacy.text }}</view>
        <view class="note terms-tip">
          协议为常驻可查入口，历史版本与你的同意记录由本店永久保留。如对条款有疑问可到吧台咨询店员。
        </view>
      </scroll-view>
    </view>

    <view v-if="showDeact" class="dlg-mask" @tap="closeDeactDlg" @touchmove.stop.prevent>
      <view class="dlg-box" @tap.stop>
        <view class="dlg-title">申请注销账号</view>
        <view class="card dlg-assets">
          <view class="tiny dlg-assets-t">你当前的资产</view>
          <view class="between dlg-row">
            <text class="tiny">金币 · 本金</text>
            <text class="dlg-val red-t">¥{{ fmt(deactAssets.coinP) }}</text>
          </view>
          <view class="between dlg-row">
            <text class="tiny">金币 · 赠送</text>
            <text class="dlg-val gold-t">¥{{ fmt(deactAssets.coinB) }}</text>
          </view>
          <view class="between dlg-row">
            <text class="tiny">可用积分</text>
            <text class="dlg-val blue-t">{{ fmt(deactAssets.point) }}</text>
          </view>
          <view class="between dlg-row">
            <text class="tiny">本周碎片</text>
            <text class="dlg-val purple-t">{{ fmt(deactAssets.shard) }}</text>
          </view>
          <view class="between dlg-row">
            <text class="tiny">未核销卡券</text>
            <text class="dlg-val purple-t">{{ deactAssets.cards }} 张</text>
          </view>
        </view>
        <view class="tiny dlg-warn">
          注销后：<text class="red-t" style="font-weight:600">积分与碎片清零、未核销卡券全部作废</text>，均不折现；
          <text style="font-weight:600">本金金币 ¥{{ fmt(deactAssets.coinP) }} 可退还</text>，赠送金币不可退不可提现。
          <br />
          <text class="red-t" style="font-weight:600">提交后不会立即注销。</text>
          需到店由店长核对资产结清（当面退还本金）后执行。在此之前你的账号仍可正常使用，也可让店长驳回申请以撤销。
        </view>
        <view class="tiny dlg-label">原因 <text class="red-t">*必填</text></view>
        <textarea
          class="field dlg-input"
          v-model="deactReason"
          placeholder="请输入原因"
          maxlength="100"
          :show-confirm-bar="false"
        />
        <view class="err" v-if="deactMsg">{{ deactMsg }}</view>
        <view class="dlg-btns">
          <button class="btn ghost dlg-btn" @tap="closeDeactDlg">取消</button>
          <button class="btn danger dlg-btn" @tap="submitDeact">提交注销申请</button>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.shop-mask {
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 100;
}
.shop-sheet {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: #fff;
  border-radius: 18px 18px 0 0;
  padding: 15px 16px 24px;
  z-index: 101;
  max-height: 78%;
  box-sizing: border-box;
  animation: shop-up 0.28s ease;
}
@keyframes shop-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
.shop-hd {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.shop-title { font-size: 14px; font-weight: 600; }
.shop-close { margin-left: auto; font-size: 13px; color: #9c9a93; }
.shop-body { max-height: 62vh; }
.shop-card { padding: 12px 14px; margin-bottom: 11px; }
.shop-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
}
.shop-k { width: 56px; flex: none; color: #9c9a93; }
.shop-v { font-size: 12.5px; line-height: 1.7; color: #6b6a65; flex: 1; }
.shop-notice { background: #f5f4f0; padding: 11px 12px; margin-bottom: 11px; }
.shop-notice-t { line-height: 1.8; color: #6b6a65; }
.shop-tip { margin-top: 11px; }
.faq-sheet { max-height: 82%; }
.faq-body { max-height: 68vh; }
.faq-sub { color: #9c9a93; margin-bottom: 9px; }
.faq-list { display: flex; flex-direction: column; gap: 0; }
.faq-item { padding: 11px 12px; margin-bottom: 11px; }
.faq-a { line-height: 1.8; margin-top: 5px; color: #6b6a65; }
.faq-tip { margin-top: 4px; margin-bottom: 8px; }
.terms-sheet { max-height: 82%; }
.terms-body { max-height: 68vh; }
.terms-meta { color: #9c9a93; margin-bottom: 9px; }
.terms-text {
  font-size: 12px;
  color: #6b6a65;
  line-height: 1.8;
  white-space: pre-line;
}
.terms-tip { margin-top: 11px; margin-bottom: 8px; }
.deact-li { border-bottom: none; }
.deact-av { background: #fcebeb; color: #a32d2d; }
.deact-pill { background: #ba7517; color: #fff; }
.deact-foot { margin-top: 7px; color: #9c9a93; line-height: 1.7; }
.dlg-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 110;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}
.dlg-box {
  width: 100%;
  max-width: 340px;
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-sizing: border-box;
}
.dlg-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.dlg-assets { background: #f5f4f0; padding: 10px 12px; margin-bottom: 9px; }
.dlg-assets-t { color: #9c9a93; margin-bottom: 5px; }
.dlg-row { padding: 3px 0; }
.dlg-val { font-size: 12.5px; font-weight: 600; }
.red-t { color: #e24b4a; }
.gold-t { color: #ba7517; }
.blue-t { color: #185fa5; }
.purple-t { color: #534ab7; }
.dlg-warn { line-height: 1.8; color: #6b6a65; margin-bottom: 10px; }
.dlg-label { margin-bottom: 6px; }
.dlg-input {
  width: 100%;
  height: 72px;
  min-height: 72px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.5;
  box-sizing: border-box;
  margin-bottom: 8px;
}
.dlg-btns { display: flex; gap: 8px; margin-top: 4px; }
.dlg-btn { flex: 1; }
</style>

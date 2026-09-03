<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, clearSession, go, isStaffRole, relaunch, setPortal, toastText } from "@/utils/api";
import { startStaffReminder, stopStaffReminder } from "@/utils/staff-reminder";
import { iconSrc } from "@/utils/icons";

const chevSrc = iconSrc("chevron");

const me = ref(null);
const champs = ref({ list: [], total: 0, month: 0 });
const team = ref(null);
const showShop = ref(false);
const showFaq = ref(false);
const showTerms = ref(false);
const showPrivacy = ref(false);
const showDeact = ref(false);
const showEdit = ref(false);
const editNick = ref("");
const editGender = ref(0);
const editMsg = ref("");
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

const PRIVACY_TEXT_DEFAULT = `一、收集信息：微信昵称头像（必需）、手机号（必需）、性别与姓名（选填）。自动收集：微信账号标识、订单信息、对局记录、相关服务记录。
二、不收集：精确地理位置、通讯录/相册/麦克风权限（扫码时主动调起）、微信好友关系、支付账户信息（不接入线上支付）。
三、使用目的：提供服务、客户服务、匿名经营分析；不做自动化决策与精准营销。
四、对外提供：昵称头像在排行榜展示；门店待办提醒由吧台电脑值守页与员工小程序前台实时提示，不使用微信订阅消息推送；不出售个人信息。登录可通过微信授权手机号或短信验证码。
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
function switchToStaff() {
  setPortal("staff");
  startStaffReminder();
  relaunch("/pages/s/todo");
}
function openEditProfile() {
  editNick.value = me.value?.user?.nick || "";
  editGender.value = Number(me.value?.user?.gender || 0);
  editMsg.value = "";
  showEdit.value = true;
}
function closeEditProfile() {
  showEdit.value = false;
}
async function saveProfile() {
  const nick = editNick.value.trim();
  if (nick.length < 2 || nick.length > 12) { editMsg.value = "昵称长度为 2-12 个字符"; return; }
  try {
    await api("/profile", { method: "PUT", body: { nick, gender: editGender.value } });
    me.value = await api("/me");
    closeEditProfile();
    uni.showToast({ title: "资料已保存", icon: "success" });
  } catch (e) { editMsg.value = e.message || "保存失败"; }
}
const lastChamp = computed(() => {
  const d = champs.value.list?.[0]?.date;
  return d ? String(d).slice(5) : "—";
});
function genderLabel(g) { return g === 1 ? "男" : g === 2 ? "女" : "暂未设置"; }

function openTeamDetail() {
  const teamId = me.value?.user?.teamId;
  if (teamId) {
    go(`/pages/c/team?id=${teamId}`);
    return;
  }
  toastText("暂无战队，请联系店员");
}

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
    toastText("尚未配置联系电话");
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
    toastText("注销申请已提交");
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
    toastText("注销申请已提交", 2500);
    me.value = await api("/me");
  } catch (e) {
    deactMsg.value = e.message;
  }
}
</script>

<template>
  <page-meta :page-style="`overflow:${showEdit || showShop || showFaq || showTerms || showPrivacy || showDeact ? 'hidden' : 'visible'}`" />
  <app-toast />
  <view class="pbody" v-if="me">
    <view class="profile-hd">
      <view class="edit-entry" @tap="openEditProfile">编辑资料 <image class="chev chev-w" :src="chevSrc" mode="aspectFit" /></view>
      <view class="profile-hd-body">
        <view class="ph-lg">{{ me.user.av }}</view>
        <view class="profile-meta">
          <view class="profile-nick">{{ me.user.nick }}</view>
          <view class="profile-sub">{{ me.user.phone }} · {{ genderLabel(me.user.gender) }}</view>
          <view class="profile-pills">
            <text class="pill-w pill-member">会员 {{ me.user.no }}</text>
            <text class="pill-w pill-team">{{ me.user.teamName || "暂未加入战队" }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="asset-card">
      <view class="asset-grid">
        <view class="asset" @tap="go('/pages/c/recharge')">
          <view class="asset-ic-wrap">
            <app-icon name="coin" tone="gold" size="sm" shape="soft" />
          </view>
          <view class="ab gold number-display">{{ fmt(me.user.coin.total) }}</view>
          <text class="asset-label">金币</text>
        </view>
        <view class="asset" @tap="go('/pages/c/points')">
          <view class="asset-ic-wrap">
            <app-icon name="point" tone="blue" size="sm" shape="soft" />
          </view>
          <view class="ab number-display" :class="{ 'asset-val-sm': fmt(me.user.point.av).length > 5 }" :style="{ color: me.user.point.av < 0 ? '#A32D2D' : '#185FA5' }">{{ fmt(me.user.point.av) }}</view>
          <text class="asset-label">积分</text>
        </view>
        <view class="asset" @tap="go('/pages/c/cards')">
          <view class="asset-ic-wrap">
            <app-icon name="card" tone="indigo" size="sm" shape="soft" />
          </view>
          <view class="ab" style="color:#534AB7">{{ me.usableCards }}</view>
          <text class="asset-label">卡包</text>
        </view>
        <view class="asset" @tap="go('/pages/c/shard')">
          <view class="asset-ic-wrap">
            <app-icon name="shard" tone="green" size="sm" shape="soft" />
          </view>
          <view class="ab number-display" style="color:#3B6D11">{{ fmt(me.user.shard.w) }}</view>
          <text class="asset-label">碎片</text>
        </view>
      </view>
    </view>

    <view class="honor-grid">
      <view class="honor g" @tap="go('/pages/c/champion')">
        <view class="honor-hd"><text class="honor-ic">🏆</text><text>我的冠军</text></view>
        <view class="hv">{{ champs.total }}</view>
        <view class="hl">累计夺冠 · 本月 {{ champs.month }} · 最近 {{ lastChamp }}</view>
      </view>
      <view class="honor gn" @tap="openTeamDetail">
        <view class="honor-hd"><text class="honor-ic">👥</text><text>{{ me.user.teamName || "暂无战队" }}</text></view>
        <view class="hv">{{ team ? team.champs + " 冠" : "—" }}</view>
        <view class="hl">{{ team ? (team.members?.length || 0) + " 名成员" : "可联系店员加入" }}</view>
      </view>
    </view>

    <view class="card">
      <view class="h2">我的订单</view>
      <view class="g3">
        <button class="btn ghost" @tap="go('/pages/c/orders?tab=coin')">金币订单</button>
        <button class="btn ghost" @tap="go('/pages/c/orders?tab=card')">卡包订单</button>
        <button class="btn ghost" @tap="go('/pages/c/orders?tab=point')">积分订单</button>
      </view>
    </view>

    <view class="card">
      <view class="h2">帮助与联系</view>
      <view class="menu-li" @tap="openShopSheet">
        <app-icon name="shop" tone="teal" size="sm" shape="soft" />
        <view class="gr">
          <view class="menu-title">联系店员</view>
          <view class="menu-sub">{{ me.shop?.tel ? "地址、电话与营业时间" : "商家尚未配置门店信息" }}</view>
        </view>
        <image class="chev" :src="chevSrc" mode="aspectFit" />
      </view>
      <view class="menu-li" @tap="openFaqSheet">
        <app-icon name="faq" tone="blue" size="sm" shape="soft" />
        <view class="gr">
          <view class="menu-title">常见问题</view>
          <view class="menu-sub">{{ faqSub }}</view>
        </view>
        <image class="chev" :src="chevSrc" mode="aspectFit" />
      </view>
      <view class="menu-li" @tap="openTermsSheet">
        <app-icon name="terms" tone="purple" size="sm" shape="soft" />
        <view class="gr">
          <view class="menu-title">用户协议</view>
          <view class="menu-sub">{{ termsSub }}</view>
        </view>
        <image class="chev" :src="chevSrc" mode="aspectFit" />
      </view>
      <view class="menu-li" @tap="openPrivacySheet">
        <app-icon name="privacy" tone="indigo" size="sm" shape="soft" />
        <view class="gr">
          <view class="menu-title">隐私政策</view>
          <view class="menu-sub">{{ privacySub }}</view>
        </view>
        <image class="chev" :src="chevSrc" mode="aspectFit" />
      </view>
      <view class="menu-li deact-li" @tap="openDeactDlg">
        <app-icon name="deact" tone="red" size="sm" shape="soft" />
        <view class="gr">
          <view class="menu-title" :style="{ color: deactPending ? '#BA7517' : '#A32D2D', fontWeight: 600 }">注销账号</view>
          <view class="menu-sub">{{ deactPending ? "申请已提交 · 待店长核对资产结清" : "清空资产并注销会员，操作不可恢复" }}</view>
        </view>
        <text v-if="deactPending" class="pill deact-pill">处理中</text>
        <image v-else class="chev" :src="chevSrc" mode="aspectFit" />
      </view>
      <view class="tiny deact-foot">协议为常驻入口，可随时查看当前生效版本全文与你的同意记录。</view>
    </view>

    <button
      v-if="isStaffRole()"
      class="btn ghost block foot-btn"
      style="margin-bottom:10px"
      @tap="switchToStaff"
    >切换到员工端</button>
    <button class="btn ghost block foot-btn" @tap="logout">切换账号</button>
    <tab-bar current="mine" />

    <view v-if="showEdit" class="shop-mask" @tap="closeEditProfile" @touchmove.stop.prevent></view>
    <view v-if="showEdit" class="shop-sheet edit-sheet" @touchmove.stop.prevent>
      <view class="shop-hd"><text class="shop-title">编辑资料</text><text class="shop-close" @tap="closeEditProfile">关闭</text></view>
      <view class="edit-avatar">{{ me.user.av }}</view>
      <view class="tiny edit-avatar-tip">头像使用昵称前两字，修改昵称后会自动更新</view>
      <view class="edit-label">昵称 *</view>
      <input class="field edit-input" v-model="editNick" maxlength="12" placeholder="请输入昵称" />
      <view class="tiny">2-12 个字符，将展示在榜单与战队名单中</view>
      <view class="edit-label">性别</view>
      <view class="gender-row"><button class="gender-btn" :class="{active:editGender===1}" @tap="editGender=1">男</button><button class="gender-btn" :class="{active:editGender===2}" @tap="editGender=2">女</button><button class="gender-btn" :class="{active:editGender===0}" @tap="editGender=0">不显示</button></view>
      <view class="edit-readonly"><view><text>会员号</text><b>{{me.user.no}}</b></view><view><text>手机号</text><b>{{me.user.phone}}</b></view><view><text>战队</text><b>{{me.user.teamName || '未加入'}}</b></view><view class="tiny">会员号为账号唯一标识不可修改；换手机号与调整战队需到吧台由店员操作。</view></view>
      <view v-if="editMsg" class="err">{{editMsg}}</view><button class="btn block" @tap="saveProfile">保存</button>
    </view>

    <view v-if="showShop" class="shop-mask" @tap="closeShopSheet" @touchmove.stop.prevent></view>
    <view v-if="showShop" class="shop-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">联系店员</text>
        <text class="shop-close" @tap="closeShopSheet">关闭</text>
      </view>
      <scroll-view scroll-y :show-scrollbar="false" class="shop-body sheet-scroll">
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
      <scroll-view scroll-y :show-scrollbar="false" class="faq-body sheet-scroll">
        <view class="tiny faq-sub">{{ faq.sub }} · 共 {{ faq.items.length }} 条</view>
        <view v-if="faq.items.length" class="faq-list">
          <view v-for="(it, i) in faq.items" :key="i" class="card faq-item">
            <view style="font-weight:600;font-size:13px">{{ i + 1 }}. {{ it.q }}</view>
            <view class="tiny faq-a">{{ it.a }}</view>
          </view>
        </view>
        <view v-else class="card tiny" style="text-align:center;padding:24px">商家尚未配置常见问题</view>
        <view class="note faq-tip">以上内容与《用户协议》一致。若店员口述与此处不符，请以协议全文为准并向店长反馈。</view>
      </scroll-view>
    </view>

    <view v-if="showTerms" class="shop-mask" @tap="closeTermsSheet" @touchmove.stop.prevent></view>
    <view v-if="showTerms" class="shop-sheet terms-sheet" @touchmove.stop>
      <view class="shop-hd">
        <text class="shop-title">{{ terms.title }} v{{ terms.ver }}</text>
        <text class="shop-close" @tap="closeTermsSheet">关闭</text>
      </view>
      <scroll-view scroll-y :show-scrollbar="false" class="terms-body sheet-scroll">
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
      <scroll-view scroll-y :show-scrollbar="false" class="terms-body sheet-scroll">
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
          <button class="btn dlg-btn deact-submit" @tap="submitDeact">提交注销申请</button>
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
.sheet-scroll { scrollbar-width: none; -ms-overflow-style: none; }
.sheet-scroll::-webkit-scrollbar { display: none; width: 0; height: 0; }
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
.chev-w { width: 14px; height: 14px; opacity: .75; vertical-align: -2px; margin-left: 2px; }
.honor-ic { font-size: 14px; line-height: 1; }
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
.deact-submit { background:#b52b2b;color:#fff;border-color:#b52b2b;font-weight:600; }
.profile-hd-body {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.profile-meta {
  flex: 1;
  min-width: 0;
  padding-right: 4px;
}
.profile-nick {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding-right: 78px;
  line-height: 1.3;
}
.profile-sub {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.45;
}
.profile-pills {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
  min-width: 0;
}
.pill-member {
  flex: 0 0 auto;
}
.pill-team {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.edit-entry {
  position: absolute;
  top: 16px;
  right: 14px;
  z-index: 1;
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #fff;
  border-radius: 9px;
  padding: 6px 9px;
  font-size: 12px;
  white-space: nowrap;
}
.edit-entry text { margin-left:2px; }
.edit-sheet { max-height:82%; padding-bottom:22px; }
.edit-avatar { width:54px;height:54px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#8470C8,#D065A0);color:#fff;font-size:20px;font-weight:600; }
.edit-avatar-tip { margin:7px 0 13px;color:#9c9a93; }
.edit-label { margin-top:13px;margin-bottom:6px;font-size:13px;color:#6b6a65; }
.edit-input { width:100%;height:42px;border:1px solid rgba(28,27,25,.24);border-radius:9px;padding:0 11px;font-size:15px;box-sizing:border-box;margin-bottom:6px; }
.gender-row { display:flex;gap:8px; }
.gender-btn { min-width:58px;padding:7px 12px;border:1px solid rgba(28,27,25,.18);border-radius:9px;background:#fff;color:#6b6a65;font-size:13px; }
.gender-btn.active { background:#1c1b19;color:#fff;border-color:#1c1b19; }
.edit-readonly { background:#f5f4f0;border:1px solid rgba(28,27,25,.12);border-radius:12px;padding:11px 12px;margin:14px 0; }
.edit-readonly>view:not(.tiny) { display:flex;justify-content:space-between;padding:3px 0;font-size:13px; }.edit-readonly text { color:#9c9a93; }.edit-readonly .tiny { margin-top:7px;line-height:1.7;color:#9c9a93; }
</style>

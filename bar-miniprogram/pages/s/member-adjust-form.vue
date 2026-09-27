<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { api, go, hideWxHomeButton, toastText } from "@/utils/api";

const uid = ref(0);
const detail = ref(null);
const loading = ref(true);
const submitting = ref(false);
const dlg = ref(null); // shard | point | card | verify | null

const form = reactive({
  delta: "",
  cardDir: "grant", // grant | revoke
  tpl: 0,
  qty: "1",
  cardId: 0,
  tail: "",
  reason: "",
});

const member = computed(() => detail.value?.member || null);
const tpls = computed(() => detail.value?.cardTpls || []);
const unusedCards = computed(() => detail.value?.unusedCards || []);
const logs = computed(() => detail.value?.logs || []);
const unusedN = computed(() => Number(member.value?.unusedCards || 0));

const grantTplOpts = computed(() =>
  tpls.value.map((t) => ({ id: t.id, label: `${t.name}（${t.days || 30} 天）` })),
);
const revokeTplOpts = computed(() =>
  tpls.value
    .filter((t) => Number(t.unused || 0) > 0)
    .map((t) => ({ id: t.id, label: `${t.name} · 未用 ${t.unused} 张` })),
);
const cardTplOpts = computed(() => (form.cardDir === "revoke" ? revokeTplOpts.value : grantTplOpts.value));
const tplIndex = computed(() => {
  const i = cardTplOpts.value.findIndex((t) => t.id === form.tpl);
  return i < 0 ? 0 : i;
});
const cardOpts = computed(() =>
  unusedCards.value.map((c) => ({
    id: c.id,
    label: `${c.tplName}${c.cat === "OTHER" ? "（宝箱卡）" : ""} · ${c.daysLeft ?? c.days ?? "—"} 天后到期`,
  })),
);
const cardIndex = computed(() => {
  const i = unusedCards.value.findIndex((c) => c.id === form.cardId);
  return i < 0 ? 0 : i;
});
const selectedCard = computed(() => unusedCards.value.find((c) => c.id === form.cardId) || unusedCards.value[0] || null);

const dlgOpen = computed(() => !!dlg.value);
const shardChips = [10, 50, 120, -10, -50];
const pointChips = [100, 300, 500, -100, -300];

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}
function fmtPoint(av) {
  const n = Number(av || 0);
  return n < 0 ? `−${fmt(-n)}（待抵扣）` : fmt(n);
}
function memberNo(m) {
  const no = m?.no || "";
  return no.startsWith("WK") ? no : `WK${no}`;
}
function logLine(l) {
  const d = String(l.detail || "");
  return d.length > 72 ? `${d.slice(0, 72)}…` : d;
}

async function load({ soft = false } = {}) {
  if (!uid.value) return;
  loading.value = true;
  try {
    // 进页首屏用全局转圈；提交后刷新有数据时静默，避免叠两层
    detail.value = await api(`/staff/members/${uid.value}/adjust`, {
      loading: !soft,
      silent: soft,
    });
    syncDefaultTpl();
  } catch (e) {
    toastText(e?.message || "加载失败");
  } finally {
    loading.value = false;
  }
}

function syncDefaultTpl() {
  const opts = form.cardDir === "revoke" ? revokeTplOpts.value : grantTplOpts.value;
  if (!opts.length) {
    form.tpl = 0;
    return;
  }
  if (!opts.some((t) => t.id === form.tpl)) form.tpl = opts[0].id;
}

function switchPerson() {
  const pages = getCurrentPages();
  if (pages.length > 1) {
    uni.navigateBack({ delta: 1 });
    return;
  }
  go("/pages/s/member-adjust", true);
}

function openDlg(kind) {
  form.delta = "";
  form.qty = "1";
  form.tail = "";
  form.reason = "";
  form.cardDir = "grant";
  if (kind === "card") {
    syncDefaultTpl();
    if (!tpls.value.length) {
      toastText("暂无可用卡券模板");
      return;
    }
  }
  if (kind === "verify") {
    if (!unusedCards.value.length) {
      toastText("该顾客没有可核销的卡券");
      return;
    }
    form.cardId = unusedCards.value[0].id;
  }
  dlg.value = kind;
}

function closeDlg() {
  if (submitting.value) return;
  dlg.value = null;
}

function setChip(v) {
  form.delta = String(v);
}

function setCardDir(dir) {
  form.cardDir = dir;
  form.qty = "1";
  syncDefaultTpl();
  if (dir === "revoke" && !revokeTplOpts.value.length) {
    toastText("该顾客没有可扣减的未使用卡券");
  }
}

function onTplPick(e) {
  const t = cardTplOpts.value[Number(e.detail.value || 0)];
  if (t) form.tpl = t.id;
}
function onCardPick(e) {
  const c = unusedCards.value[Number(e.detail.value || 0)];
  if (c) form.cardId = c.id;
}

async function submitDlg() {
  if (!member.value || submitting.value) return;
  const reason = String(form.reason || "").trim();
  submitting.value = true;
  try {
    if (dlg.value === "shard" || dlg.value === "point") {
      const delta = Number(form.delta);
      if (!delta || Number.isNaN(delta)) {
        toastText("请输入调整值");
        return;
      }
      if (dlg.value === "shard") {
        const w = Number(member.value.shard?.w || 0);
        if (delta < 0 && -delta > w) {
          toastText(`扣减失败，超出本周碎片（当前 ${fmt(w)}）`);
          return;
        }
        await api(`/staff/members/${uid.value}/adjust-shard`, {
          method: "POST",
          body: { data: { delta, reason } },
        });
        toastText(`已调整 ${fmt(delta)} 碎片 · 已留痕`);
      } else {
        await api(`/staff/members/${uid.value}/adjust-point`, {
          method: "POST",
          body: { data: { delta, reason } },
        });
        toastText("已调整积分 · 已留痕");
      }
    } else if (dlg.value === "card") {
      const qtyAbs = Math.max(1, Math.abs(Number(form.qty) || 0));
      if (!form.tpl) {
        toastText("请选择卡券类型");
        return;
      }
      if (form.cardDir === "revoke" && !revokeTplOpts.value.length) {
        toastText("该顾客没有可扣减的未使用卡券");
        return;
      }
      const qty = form.cardDir === "revoke" ? -qtyAbs : qtyAbs;
      await api(`/staff/members/${uid.value}/adjust-cards`, {
        method: "POST",
        body: { data: { tpl: form.tpl, qty, reason } },
      });
      toastText(form.cardDir === "revoke" ? `已扣减 ${qtyAbs} 张未使用卡 · 已留痕` : `已补发 ${qtyAbs} 张 · 已留痕`);
    } else if (dlg.value === "verify") {
      const tail = String(form.tail || "").trim();
      if (!tail) {
        toastText("请核对并输入顾客手机尾号");
        return;
      }
      if (!form.cardId) {
        toastText("请选择卡券");
        return;
      }
      await api(`/staff/members/${uid.value}/direct-verify`, {
        method: "POST",
        body: { data: { cardId: form.cardId, tail, reason } },
      });
      toastText("已核销 1 张 · 已留痕");
    }
    dlg.value = null;
    await load({ soft: true });
  } catch (e) {
    toastText(e?.message || "操作失败");
  } finally {
    submitting.value = false;
  }
}

onLoad((q) => {
  uid.value = Number(q?.uid || 0);
});
onShow(() => {
  hideWxHomeButton();
  load();
});
</script>

<template>
  <page-meta :page-style="`overflow:${dlgOpen ? 'hidden' : 'visible'}`" />
  <view class="pbody">
    <view v-if="!loading && !member" class="empty">会员不存在或已失效</view>
    <template v-else-if="member">
      <view class="card head">
        <view class="av">{{ (member.av || member.nick || "?").slice(0, 2) }}</view>
        <view class="mid">
          <view class="name-row">
            <text class="nick">{{ member.nick }}</text>
            <text class="tail">尾号 {{ member.tail || "—" }}</text>
          </view>
          <view class="tiny">{{ memberNo(member) }} · {{ member.teamName || "无战队" }}</view>
        </view>
        <button class="btn ghost switch-btn" @tap.stop="switchPerson">换人</button>
      </view>

      <view class="card assets">
        <view class="st">当前资产 <text class="em">提交前请核对姓名与尾号</text></view>
        <view class="asset-row">
          <view class="gr">
            <text class="b">碎片</text>
            <text class="mut">本周 {{ fmt(member.shard?.w) }} · 历史累计 {{ fmt(member.shard?.t) }}</text>
          </view>
          <text class="val purple">周值 {{ fmt(member.shard?.w) }}</text>
        </view>
        <view class="asset-row">
          <view class="gr">
            <text class="b">积分</text>
            <text class="mut">
              <text v-if="member.point?.fz > 0">冻结 {{ fmt(member.point.fz) }} · </text>
              累计已提出 {{ fmt(member.point?.wd || 0) }}
            </text>
          </view>
          <text class="val" :class="{ red: member.point?.av < 0, blue: !(member.point?.av < 0) }">{{ fmtPoint(member.point?.av) }}</text>
        </view>
        <view class="asset-row">
          <view class="gr">
            <text class="b">卡包</text>
            <text class="mut">未使用 {{ fmt(unusedN) }} 张 · 已核销 {{ fmt(member.usedCards) }} 张</text>
          </view>
          <text class="val">{{ fmt(unusedN) }} 张</text>
        </view>
        <view class="asset-row dim">
          <view class="gr">
            <text class="b">金币</text>
            <text class="mut">本金 {{ fmt(member.coin?.p) }} / 赠送 {{ fmt(member.coin?.b) }} · 店员无权调整</text>
          </view>
          <text class="val">{{ fmt(member.coin?.total) }}</text>
        </view>
      </view>

      <view class="st">快速调整 <text class="em">提交即生效 · 系统自动留痕</text></view>
      <view class="actions">
        <button class="btn act shard" @tap="openDlg('shard')">调整碎片</button>
        <button class="btn act point" @tap="openDlg('point')">调整积分</button>
        <button class="btn act" @tap="openDlg('card')">调整卡券</button>
        <button class="btn act" :class="{ dan: unusedN > 0 }" :disabled="!unusedN" @tap="openDlg('verify')">
          代客核销{{ unusedN ? `（${unusedN} 张可用）` : "" }}
        </button>
      </view>

      <view class="warn">
        碎片 / 积分填正数增加、负数扣减；卡券在「调整卡券」里可选补发或扣减未使用卡。代客核销是当面用掉卡，需核对尾号。提交立即生效并留痕。原因选填。
      </view>

      <view class="st">最近调整 <text class="em">{{ logs.length }} 条 · 仅显示本会员</text></view>
      <view class="card logs">
        <view v-if="!logs.length" class="empty-logs">暂无手动调整记录</view>
        <view v-for="(l, i) in logs" :key="i" class="log-row">
          <view class="gr">
            <text class="b">{{ logLine(l) }}</text>
            <text class="mut">{{ l.t }} · {{ l.op }}（{{ l.role || "—" }}）</text>
          </view>
        </view>
      </view>

      <view class="note">
        <text class="b">本页范围：</text>碎片、积分、卡券均可快速增减；另可代客核销。金币不在本页，仍走 Web 端申请与老板审批。
      </view>
    </template>
  </view>

  <view v-if="dlg" class="mask" @tap="closeDlg" @touchmove.stop.prevent>
    <view class="dialog" @tap.stop>
      <view class="dlg-title">
        {{
          dlg === "shard"
            ? `调整碎片 · ${member?.nick || ""}`
            : dlg === "point"
              ? `调整积分 · ${member?.nick || ""}`
              : dlg === "card"
                ? `调整卡券 · ${member?.nick || ""}`
                : `代客核销 · ${member?.nick || ""}`
        }}
      </view>

      <template v-if="dlg === 'shard' || dlg === 'point'">
        <view class="tiny tip">
          尾号 {{ member?.tail || "—" }} ·
          <template v-if="dlg === 'shard'">
            当前本周 <text class="purple">{{ fmt(member?.shard?.w) }}</text> · 历史累计 {{ fmt(member?.shard?.t) }}
          </template>
          <template v-else>
            当前可用 <text class="b">{{ fmtPoint(member?.point?.av) }}</text>
            · 冻结 {{ fmt(member?.point?.fz) }}
          </template>
        </view>
        <view class="fld">调整值（正数增加 / 负数扣减）</view>
        <input v-model="form.delta" class="inp" type="text" :placeholder="dlg === 'shard' ? '如 50 或 -50' : '如 200 或 -200'" />
        <view class="chips">
          <button
            v-for="v in dlg === 'shard' ? shardChips : pointChips"
            :key="v"
            class="btn sm chip"
            @tap="setChip(v)"
          >{{ v > 0 ? `+${v}` : v }}</button>
        </view>
        <view v-if="dlg === 'shard'" class="hint red">
          碎片直接影响周榜排名与宝箱卡归属。扣减不能超过本周碎片；历史累计同步变动。
        </view>
        <view v-else class="hint">扣成负数将转为「待抵扣」，顾客后续获得的分优先冲抵。</view>
      </template>

      <template v-else-if="dlg === 'card'">
        <view class="tiny tip">尾号 {{ member?.tail || "—" }} · 补发入卡包；扣减只作废未使用卡</view>
        <view class="fld">操作</view>
        <view class="dir-row">
          <view class="dir" :class="{ on: form.cardDir === 'grant' }" @tap="setCardDir('grant')">补发（增加）</view>
          <view class="dir" :class="{ on: form.cardDir === 'revoke' }" @tap="setCardDir('revoke')">扣减未使用</view>
        </view>
        <view class="fld">卡券类型</view>
        <picker mode="selector" :range="cardTplOpts" range-key="label" :value="tplIndex" @change="onTplPick">
          <view class="inp picker">{{ cardTplOpts[tplIndex]?.label || (form.cardDir === 'revoke' ? '暂无未使用卡' : '请选择') }}</view>
        </picker>
        <view class="fld">数量</view>
        <input v-model="form.qty" class="inp" type="number" />
        <view v-if="form.cardDir === 'revoke'" class="hint red">将按卡种作废对应数量的未使用卡；不足时报错。已核销的不能扣。</view>
        <view v-else class="hint">补发即入卡包，顾客端立即可见。</view>
      </template>

      <template v-else>
        <view class="fld">选择卡券</view>
        <picker mode="selector" :range="cardOpts" range-key="label" :value="cardIndex" @change="onCardPick">
          <view class="inp picker">{{ cardOpts[cardIndex]?.label || "请选择" }}</view>
        </picker>
        <view v-if="selectedCard?.cat === 'OTHER' && selectedCard?.prize" class="prize">
          <view class="tiny gold">奖品说明（仅店员可见）</view>
          <view class="prize-text">{{ selectedCard.prize }}</view>
        </view>
        <view class="fld">核对顾客手机尾号 4 位 <text class="req">*必填</text></view>
        <input v-model="form.tail" class="inp" maxlength="4" type="number" placeholder="请顾客报出尾号" />
        <view class="hint red">
          代客核销是当面把卡用掉，必须核对尾号；与「扣减未使用」不同，核销后记为已使用。
        </view>
      </template>

      <view class="fld">原因 <text class="opt">选填</text></view>
      <input v-model="form.reason" class="inp" placeholder="建议填写，便于事后对账" />

      <view class="dlg-actions">
        <button class="btn ghost" :disabled="submitting" @tap="closeDlg">取消</button>
        <button class="btn dan" :disabled="submitting" @tap="submitDlg">
          {{
            submitting
              ? "提交中…"
              : dlg === "verify"
                ? "确认核销"
                : dlg === "card"
                  ? form.cardDir === "revoke"
                    ? "确认扣减"
                    : "确认补发"
                  : "确认调整"
          }}
        </button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.head { display: flex; align-items: center; gap: 12px; }
.av {
  width: 40px; height: 40px; border-radius: 50%; background: #eceae4; color: #6f6d66;
  display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex: none;
}
.mid { flex: 1; min-width: 0; }
.name-row { display: flex; align-items: baseline; gap: 6px; }
.nick { font-size: 15px; font-weight: 600; }
.tail { font-size: 12px; color: #9c9a93; }
.switch-btn {
  flex: none; margin: 0; padding: 7px 12px; font-size: 13px; font-weight: 500; line-height: 1.2;
  background: #fff; color: #1c1b19; border: 1px solid rgba(28, 27, 25, 0.14);
}
.st {
  display: flex; align-items: baseline; gap: 8px; margin: 4px 2px 8px;
  font-size: 14px; font-weight: 600;
}
.st .em, .assets .em { font-size: 11px; font-weight: 400; color: #9c9a93; }
.assets { padding: 12px 12px 4px; }
.asset-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 11px 0; border-bottom: 1px solid rgba(28, 27, 25, 0.06);
}
.asset-row:last-child { border-bottom: none; }
.asset-row.dim { opacity: 0.62; }
.gr { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.b { font-weight: 600; font-size: 13px; }
.mut { font-size: 11px; color: #9c9a93; }
.val { font-weight: 700; font-size: 14px; flex: none; }
.purple { color: #534ab7; }
.blue { color: #185fa5; }
.red { color: #a32d2d; }
.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
.btn.act {
  margin: 0; background: #fff; color: #1c1b19; border: 1px solid rgba(28, 27, 25, 0.14);
  font-weight: 600; padding: 11px 8px;
}
.btn.act.shard { border-color: #534ab7; color: #534ab7; }
.btn.act.point { border-color: #185fa5; color: #185fa5; }
.btn.act.dan { border-color: #e24b4a; color: #a32d2d; }
button.btn.act[disabled] { opacity: 0.45; color: #9c9a93 !important; border-color: rgba(28,27,25,.12) !important; }
.warn {
  background: #fcebeb; border: 1px solid #e24b4a; border-radius: 12px;
  padding: 10px 12px; margin-bottom: 12px; color: #a32d2d; font-size: 12px; line-height: 1.7;
}
.logs { padding: 4px 12px; }
.log-row { padding: 10px 0; border-bottom: 1px solid rgba(28, 27, 25, 0.06); }
.log-row:last-child { border-bottom: none; }
.empty-logs { text-align: center; padding: 18px; color: #9c9a93; font-size: 12px; }
.note {
  margin-top: 4px; padding: 10px 12px; border-radius: 12px; background: #e6f1fb;
  color: #185fa5; font-size: 12px; line-height: 1.65;
}
.note .b { color: #0c447c; }
.empty { text-align: center; padding: 40px; color: #9c9a93; }
.mask {
  position: fixed; inset: 0; background: rgba(28, 27, 25, 0.45);
  z-index: 1000; display: flex; align-items: flex-end; justify-content: center;
}
.dialog {
  width: 100%; max-height: 86vh; overflow-y: auto; background: #fff;
  border-radius: 16px 16px 0 0; padding: 18px 16px calc(16px + env(safe-area-inset-bottom));
  box-sizing: border-box;
}
.dlg-title { font-size: 16px; font-weight: 700; margin-bottom: 10px; }
.fld { font-size: 12px; color: #9c9a93; margin: 10px 0 6px; }
.fld .req { color: #a32d2d; }
.fld .opt { color: #9c9a93; font-weight: 400; }
.inp {
  width: 100%; height: 40px; padding: 0 12px; box-sizing: border-box;
  border-radius: 10px; border: 1px solid rgba(28, 27, 25, 0.12); background: #fff; font-size: 14px;
}
.picker { display: flex; align-items: center; }
.dir-row { display: flex; gap: 8px; }
.dir {
  flex: 1; text-align: center; padding: 9px 0; border-radius: 10px;
  border: 1px solid rgba(28, 27, 25, 0.12); background: #faf9f5; font-size: 13px;
}
.dir.on { background: #e6f1fb; border-color: #185fa5; color: #185fa5; font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chip { margin: 0; padding: 6px 10px; font-size: 12px; background: #faf9f5; color: #1c1b19; border: 1px solid rgba(28,27,25,.12); }
.tip { color: #9c9a93; margin-bottom: 4px; line-height: 1.6; }
.hint { margin-top: 8px; font-size: 11px; color: #9c9a93; line-height: 1.7; }
.hint.red { color: #a32d2d; }
.prize { background: #faeeda; border-radius: 8px; padding: 9px 10px; margin: 8px 0; }
.prize .gold { color: #ba7517; margin-bottom: 3px; }
.prize-text { font-size: 13px; font-weight: 600; }
.dlg-actions { display: grid; grid-template-columns: 1fr 1.5fr; gap: 8px; margin-top: 16px; }
.dlg-actions .btn { margin: 0; }
</style>

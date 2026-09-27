<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { api, hideWxHomeButton, toastText } from "@/utils/api";

const uid = ref(0);
const detail = ref(null);
const loading = ref(true);
const submitting = ref(false);
const tab = ref("shard"); // shard | point | card

const form = reactive({
  delta: "",
  tpl: 0,
  qty: "1",
  cardDir: "grant", // grant | revoke
  reason: "",
});

const member = computed(() => detail.value?.member || null);
const tpls = computed(() => detail.value?.cardTpls || []);
const tplOpts = computed(() =>
  tpls.value.map((t) => ({
    id: t.id,
    label: `${t.name}${t.unused ? ` · 未用 ${t.unused}` : ""}`,
  })),
);
const tplIndex = computed(() => {
  const i = tpls.value.findIndex((t) => t.id === form.tpl);
  return i < 0 ? 0 : i;
});

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

async function load() {
  if (!uid.value) return;
  loading.value = true;
  try {
    detail.value = await api(`/staff/members/${uid.value}/adjust`, { loading: false });
    if (!form.tpl && tpls.value.length) form.tpl = tpls.value[0].id;
  } catch (e) {
    toastText(e?.message || "加载失败");
  } finally {
    loading.value = false;
  }
}

function onTplPick(e) {
  const i = Number(e.detail.value || 0);
  const t = tpls.value[i];
  if (t) form.tpl = t.id;
}

async function submit() {
  const reason = String(form.reason || "").trim();
  if (reason.length < 2) {
    toastText("原因至少 2 个字");
    return;
  }
  submitting.value = true;
  try {
    if (tab.value === "shard" || tab.value === "point") {
      const delta = Number(form.delta);
      if (!delta || Number.isNaN(delta)) {
        toastText("请输入调整值");
        return;
      }
      if (tab.value === "shard") {
        const w = Number(member.value?.shard?.w || 0);
        if (delta < 0 && -delta > w) {
          toastText(`扣减失败，超出本周碎片（当前 ${fmt(w)}）`);
          return;
        }
        await api(`/staff/members/${uid.value}/adjust-shard`, {
          method: "POST",
          body: { data: { delta, reason } },
          loading: false,
        });
      } else {
        await api(`/staff/members/${uid.value}/adjust-point`, {
          method: "POST",
          body: { data: { delta, reason } },
          loading: false,
        });
      }
    } else {
      const qtyAbs = Math.abs(Number(form.qty) || 0);
      if (!qtyAbs) {
        toastText("请输入数量");
        return;
      }
      if (!form.tpl) {
        toastText("请选择卡券");
        return;
      }
      const qty = form.cardDir === "revoke" ? -qtyAbs : qtyAbs;
      await api(`/staff/members/${uid.value}/adjust-cards`, {
        method: "POST",
        body: { data: { tpl: form.tpl, qty, reason } },
        loading: false,
      });
    }
    toastText("已调整并留痕");
    form.delta = "";
    form.qty = "1";
    form.reason = "";
    await load();
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
  <view class="pbody">
    <view v-if="loading && !member" class="empty">加载中…</view>
    <template v-else-if="member">
      <view class="card head">
        <view class="av">{{ (member.av || member.nick || "?").slice(0, 2) }}</view>
        <view class="mid">
          <view class="nick">{{ member.nick }}</view>
          <view class="tiny">{{ member.no }} · {{ member.tail || "—" }} · {{ member.teamName || "无战队" }}</view>
        </view>
      </view>

      <view class="card stats">
        <view class="stat">
          <text class="num purple">{{ fmt(member.shard?.w) }}</text>
          <text class="tiny">本周碎片</text>
        </view>
        <view class="stat">
          <text class="num">{{ fmt(member.shard?.t) }}</text>
          <text class="tiny">历史碎片</text>
        </view>
        <view class="stat">
          <text class="num blue">{{ fmt(member.point?.av) }}</text>
          <text class="tiny">可用积分</text>
        </view>
        <view class="stat">
          <text class="num">{{ fmt(member.unusedCards) }}</text>
          <text class="tiny">未用卡券</text>
        </view>
      </view>

      <view class="tabs">
        <view class="tab" :class="{ on: tab === 'shard' }" @tap="tab = 'shard'">碎片</view>
        <view class="tab" :class="{ on: tab === 'point' }" @tap="tab = 'point'">积分</view>
        <view class="tab" :class="{ on: tab === 'card' }" @tap="tab = 'card'">卡券</view>
      </view>

      <view class="card form">
        <template v-if="tab === 'shard' || tab === 'point'">
          <view class="fld">调整值（正数增加 / 负数扣减）</view>
          <input v-model="form.delta" class="inp" type="text" placeholder="如 10 或 -5" />
          <view v-if="tab === 'shard'" class="hint warn">
            扣减不能超过本周碎片；历史累计会同步变动。已结算奖励不回溯。
          </view>
        </template>
        <template v-else>
          <view class="fld">操作</view>
          <view class="dir-row">
            <view class="dir" :class="{ on: form.cardDir === 'grant' }" @tap="form.cardDir = 'grant'">补发</view>
            <view class="dir" :class="{ on: form.cardDir === 'revoke' }" @tap="form.cardDir = 'revoke'">扣减未使用</view>
          </view>
          <view class="fld">卡券模板</view>
          <picker mode="selector" :range="tplOpts" range-key="label" :value="tplIndex" @change="onTplPick">
            <view class="inp picker">{{ tplOpts[tplIndex]?.label || "请选择" }}</view>
          </picker>
          <view class="fld">数量</view>
          <input v-model="form.qty" class="inp" type="number" placeholder="1" />
        </template>

        <view class="fld">原因 *</view>
        <input v-model="form.reason" class="inp" placeholder="必填，至少 2 个字" />

        <button class="btn block" :disabled="submitting" @tap="submit">
          {{ submitting ? "提交中…" : "确认调整" }}
        </button>
      </view>

      <view class="note">本页不调整金币。金币请走 Web 后台申请，由老板审批。</view>
    </template>
  </view>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.av {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #1c1b19;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex: none;
}
.nick {
  font-size: 16px;
  font-weight: 600;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  text-align: center;
  padding: 12px 8px;
}
.stat .num {
  display: block;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 2px;
}
.purple { color: #534ab7; }
.blue { color: #185fa5; }
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 9px 0;
  border-radius: 10px;
  background: #fff;
  border: 1px solid rgba(28, 27, 25, 0.1);
  font-size: 13px;
  font-weight: 500;
}
.tab.on {
  background: #1c1b19;
  color: #fff;
  border-color: #1c1b19;
}
.fld {
  font-size: 12px;
  color: #9c9a93;
  margin: 10px 0 6px;
}
.inp {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  box-sizing: border-box;
  border-radius: 10px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #fff;
  font-size: 14px;
}
.picker {
  display: flex;
  align-items: center;
}
.dir-row {
  display: flex;
  gap: 8px;
}
.dir {
  flex: 1;
  text-align: center;
  padding: 9px 0;
  border-radius: 10px;
  border: 1px solid rgba(28, 27, 25, 0.12);
  background: #faf9f5;
  font-size: 13px;
}
.dir.on {
  background: #e6f1fb;
  border-color: #185fa5;
  color: #185fa5;
  font-weight: 600;
}
.hint {
  margin-top: 8px;
  font-size: 11px;
  color: #9c9a93;
  line-height: 1.6;
}
.hint.warn {
  color: #a32d2d;
}
.btn.block {
  width: 100%;
  margin-top: 16px;
}
.note {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #faeeda;
  color: #854f0b;
  font-size: 12px;
  line-height: 1.65;
}
.empty {
  text-align: center;
  padding: 40px;
  color: #9c9a93;
}
</style>

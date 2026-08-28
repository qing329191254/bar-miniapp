<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, loadCart, saveCart, savedUser } from "@/utils/api";

const products = ref([]);
const tables = ref([]);
const cart = ref(loadCart());
const payType = ref("COIN");
const tableId = ref(null);
const remark = ref("");
const msg = ref("");
const loading = ref(false);
const showTable = ref(false);
const timeout = ref(30);
const meUser = ref(savedUser() || {});

onShow(async () => {
  const r = await api("/products");
  products.value = r.products || [];
  tables.value = r.tables || [];
  cart.value = loadCart();
  const valid = cart.value.filter((line) => {
    const p = products.value.find((x) => x.id === line.pid);
    if (!p || p.soldOut) return false;
    return (line.specIds || []).every((sid) => (p.specs || []).some((s) => s.id === sid));
  });
  if (valid.length !== cart.value.length) {
    cart.value = valid;
    saveCart(valid);
    uni.showToast({ title: "购物车有失效商品，已自动移除", icon: "none" });
  }
  try {
    const me = await api("/me");
    timeout.value = me.config?.offlineTimeout || 30;
    if (me.user) meUser.value = me.user;
  } catch (e) {}
});

function prod(pid) {
  return products.value.find((x) => x.id === pid);
}
function unitPrice(p, specIds) {
  if (!p) return 0;
  let n = p.price || 0;
  for (const sid of specIds || []) {
    const sp = (p.specs || []).find((x) => x.id === sid);
    if (sp) n += Number(sp.diff) || 0;
  }
  return n;
}
function specNames(p, specIds) {
  if (!p) return "";
  return (specIds || [])
    .map((sid) => (p.specs || []).find((x) => x.id === sid)?.name)
    .filter(Boolean)
    .join("、");
}
const lines = computed(() =>
  cart.value
    .map((c) => {
      const p = prod(c.pid);
      if (!p) return null;
      const price = unitPrice(p, c.specIds);
      return { ...c, p, price, spec: specNames(p, c.specIds) };
    })
    .filter(Boolean),
);
const total = computed(() => lines.value.reduce((s, x) => s + x.price * x.qty, 0));
const bal = computed(() => (meUser.value.coin?.p || 0) + (meUser.value.coin?.b || 0));
const lack = computed(() => Math.max(0, total.value - bal.value));
const tableName = computed(() => {
  const t = tables.value.find((x) => x.id === tableId.value);
  return t ? t.name : "";
});

async function submit() {
  if (total.value <= 0 || loading.value) return;
  msg.value = "";
  loading.value = true;
  try {
    const order = await api("/orders", {
      method: "POST",
      body: {
        items: cart.value.map((x) => ({ pid: x.pid, qty: x.qty, specIds: x.specIds || [] })),
        payType: payType.value,
        tableId: tableId.value,
        remark: remark.value,
      },
    });
    saveCart([]);
    cart.value = [];
    go("/pages/c/orders", true);
    uni.showToast({ title: `已下单 ${order.no}`, icon: "none" });
  } catch (e) {
    msg.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <view class="pbody">
    <view class="card">
      <view class="h2">商品明细</view>
      <view v-for="(x, i) in lines" :key="i" class="between" style="padding:4px 0">
        <text>{{ x.p.name }}{{ x.spec ? "（" + x.spec + "）" : "" }} ×{{ x.qty }}</text>
        <text class="tiny">{{ x.price * x.qty }}</text>
      </view>
      <view class="between" style="padding-top:9px;margin-top:7px;border-top:1px solid rgba(28,27,25,.12)">
        <text style="font-weight:600">应付</text>
        <text class="ord-sum">{{ total }} 金币</text>
      </view>
    </view>

    <view class="card">
      <view class="h2">支付方式</view>
      <view class="pay" :class="{ on: payType === 'COIN' }" @tap="payType = 'COIN'">
        <view class="gr">
          <view style="font-weight:600">金币支付</view>
          <view class="tiny">余额 {{ bal }}（本金 {{ meUser.coin?.p || 0 }} + 赠送 {{ meUser.coin?.b || 0 }}）</view>
          <view class="tiny gold">本单扣本金，赠送金币保留</view>
        </view>
        <view class="dot" :class="{ on: payType === 'COIN' }"></view>
      </view>
      <view class="pay" :class="{ on: payType === 'OFFLINE' }" @tap="payType = 'OFFLINE'">
        <view class="gr">
          <view style="font-weight:600">到吧台付款</view>
          <view class="tiny">生成订单，现金或自行扫码，{{ timeout }} 分钟有效</view>
        </view>
        <view class="dot" :class="{ on: payType === 'OFFLINE' }"></view>
      </view>
      <view v-if="payType === 'COIN' && lack > 0" class="lack">
        <view style="font-weight:600;color:#A32D2D">余额不足，还差 {{ lack }} 金币</view>
        <view class="tiny" style="color:#A32D2D;margin-top:4px">可以先提交订单，到吧台充值后店员才能接单。</view>
        <button class="btn ghost block" style="margin-top:9px;color:#A32D2D;border-color:#E9C4C4" @tap="go('/pages/c/recharge')">立即去充值</button>
      </view>
    </view>

    <view class="card">
      <view class="h2">桌台 <text class="tiny">选填</text></view>
      <button class="btn ghost block" style="text-align:left" @tap="showTable = true">
        {{ tableName ? tableName + " 桌" : "未指定 · 点击选择（可跳过）" }}
      </button>
    </view>
    <view class="card">
      <view class="h2">备注</view>
      <input class="field remark-field" v-model="remark" maxlength="50" placeholder="如「少冰」（50 字内）" />
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
    <button class="btn block gold" :disabled="total <= 0 || loading" @tap="submit">
      {{ loading ? "提交中…" : "提交订单 · " + total + " 金币" }}
    </button>

    <view v-if="showTable" class="gal-mask" @tap="showTable = false"></view>
    <view v-if="showTable" class="gal-sheet">
      <view class="between" style="margin-bottom:12px">
        <text style="font-weight:600">选择桌台</text>
        <text class="tiny">选填 · 可跳过</text>
      </view>
      <view class="g4">
        <view
          v-for="t in tables"
          :key="t.id"
          class="icell"
          :class="{ on: tableId === t.id }"
          @tap="tableId = t.id; showTable = false"
        >
          <view style="font-weight:600">{{ t.name }}</view>
          <view class="tiny">{{ t.area }} · {{ t.seats }} 位</view>
        </view>
      </view>
      <button class="btn ghost block" style="margin-top:10px" @tap="tableId = null; showTable = false">不选桌台（跳过）</button>
    </view>
  </view>
</template>

<style scoped>
.ord-sum { font-size: 21px; font-weight: 700; color: #1C1B19; }
.remark-field {
  height: 42px;
  padding: 0 12px;
  line-height: 42px;
  margin-bottom: 0;
}
.pay {
  display: flex;
  align-items: center;
  border: 1px solid rgba(28,27,25,.12);
  border-radius: 9px;
  padding: 11px;
  margin-bottom: 8px;
}
.pay.on { border-color: #BA7517; background: #FAEEDA; }
.dot {
  width: 16px; height: 16px; border-radius: 50%;
  border: 1px solid rgba(28,27,25,.24); flex: none;
}
.dot.on { background: #BA7517; border: none; }
.lack {
  border: 1px solid #A32D2D;
  background: #FCEBEB;
  border-radius: 9px;
  padding: 10px 11px;
}
.gal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.35); z-index: 100;
}
.gal-sheet {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: #fff; border-radius: 18px 18px 0 0;
  padding: 15px 16px 24px; z-index: 101;
}
</style>

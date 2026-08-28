<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, loadCart, media, saveCart, savedUser } from "@/utils/api";

const cats = ref([]);
const products = ref([]);
const cid = ref(0);
const cart = ref(loadCart());
const user = savedUser() || {};
const specPid = ref(0);
const specBase = ref(null);
const specQty = ref(1);

onShow(async () => {
  cart.value = loadCart();
  const r = await api("/products");
  cats.value = r.cats || [];
  products.value = r.products || [];
  const valid = cart.value.filter((line) => {
    const p = products.value.find((x) => x.id === line.pid);
    if (!p || p.soldOut) return false;
    return (line.specIds || []).every((sid) => (p.specs || []).some((s) => s.id === sid));
  });
  if (valid.length !== cart.value.length) {
    cart.value = valid;
    saveCart(valid);
    uni.showToast({ title: "已移除下架、售罄或失效规格商品", icon: "none" });
  }
  cid.value = cats.value[0]?.id || 0;
});

const shown = computed(() => products.value.filter((p) => p.cid === cid.value));
const total = computed(() =>
  cart.value.reduce((s, line) => s + unitPrice(prod(line.pid), line.specIds) * line.qty, 0),
);

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
function specKey(ids) {
  return (ids || []).slice().sort((a, b) => a - b).join(",");
}
function cartQty(pid) {
  return cart.value.filter((c) => c.pid === pid).reduce((s, c) => s + c.qty, 0);
}
function persist() {
  saveCart(cart.value);
}
function addSingle(pid) {
  const p = prod(pid);
  if (!p || p.soldOut) return;
  const i = cart.value.findIndex((c) => c.pid === pid && specKey(c.specIds) === "");
  const next = [...cart.value];
  if (i >= 0) next[i] = { ...next[i], qty: next[i].qty + 1 };
  else next.push({ pid, specIds: [], qty: 1 });
  cart.value = next;
  persist();
}
function decSingle(pid) {
  const i = cart.value.findIndex((c) => c.pid === pid && specKey(c.specIds) === "");
  if (i < 0) return;
  const next = [...cart.value];
  if (next[i].qty > 1) next[i] = { ...next[i], qty: next[i].qty - 1 };
  else next.splice(i, 1);
  cart.value = next;
  persist();
}
function openSpec(p) {
  if (p.soldOut) return;
  specPid.value = p.id;
  specBase.value = null;
  specQty.value = 1;
}
function specProduct() {
  return prod(specPid.value);
}
function specTotal() {
  const p = specProduct();
  if (!p) return 0;
  return unitPrice(p, specBase.value ? [specBase.value] : []);
}
function addSpec() {
  if (!specBase.value) return;
  const pid = specPid.value;
  const ids = [specBase.value];
  const key = specKey(ids);
  const i = cart.value.findIndex((c) => c.pid === pid && specKey(c.specIds) === key);
  const next = [...cart.value];
  if (i >= 0) next[i] = { ...next[i], qty: next[i].qty + specQty.value };
  else next.push({ pid, specIds: ids, qty: specQty.value });
  cart.value = next;
  persist();
  specPid.value = 0;
}
function checkout() {
  if (total.value <= 0) return;
  persist();
  go("/pages/c/checkout");
}
</script>

<template>
  <view class="ord-page">
    <view class="ord-sub">{{ user.nick }} {{ user.tail }} · 桌台选填</view>
    <view class="ord-main">
      <scroll-view scroll-y class="ord-side">
        <view
          v-for="c in cats"
          :key="c.id"
          class="ord-cat"
          :class="{ on: cid === c.id }"
          @tap="cid = c.id"
        >{{ c.name }}</view>
      </scroll-view>
      <scroll-view scroll-y class="ord-list">
        <view v-if="!shown.length" class="tiny" style="text-align:center;padding:40px 0">该分类暂无商品</view>
        <view v-for="p in shown" :key="p.id" class="ord-item" :class="{ dim: p.soldOut }">
          <image v-if="media(p.img)" class="pth" :src="media(p.img)" mode="aspectFill" />
          <view v-else class="pth ph">{{ (p.name || "商").slice(0, 1) }}</view>
          <view class="ord-info">
            <view class="ord-name">
              {{ p.name }}
              <text v-if="p.type === 'COMBO'" class="pill" style="background:#F3EEF8;color:#6B3FA0;margin-left:5px">套餐赠卡</text>
            </view>
            <view class="tiny">{{ p.desc }}<text v-if="p.soldOut"> 今日已售罄</text></view>
            <view class="ord-row">
              <text class="ord-price">{{ p.price }} 金币</text>
              <text v-if="p.soldOut" class="pill" style="background:#FCEBEB;color:#A32D2D;margin-left:6px">已估清</text>
              <view class="ord-act">
                <button
                  v-if="p.hasSpec"
                  class="spec-btn"
                  :disabled="p.soldOut"
                  @tap="openSpec(p)"
                >{{ cartQty(p.id) > 0 ? "已选 " + cartQty(p.id) + " 件" : "选规格" }}</button>
                <view v-else class="qty">
                  <button v-if="cartQty(p.id)" class="qty-btn ghost" @tap="decSingle(p.id)">−</button>
                  <text v-if="cartQty(p.id)" class="qty-n">{{ cartQty(p.id) }}</text>
                  <button class="qty-btn" :disabled="p.soldOut" @tap="addSingle(p.id)">+</button>
                </view>
              </view>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>
    <view class="ord-bar">
      <view>
        <view class="tiny">合计</view>
        <view class="ord-sum">{{ total }} 金币</view>
      </view>
      <button class="btn gold checkout-btn" :disabled="total <= 0" @tap="checkout">去结算</button>
    </view>

    <view v-if="specPid" class="gal-mask" @tap="specPid = 0" @touchmove.stop.prevent></view>
    <view v-if="specPid && specProduct()" class="gal-sheet" @touchmove.stop>
      <view class="gal-hd">
        <text class="gal-title">{{ specProduct().name }}</text>
        <text class="tiny">{{ specProduct().price }} 金币起</text>
      </view>
      <view class="card" style="margin-bottom:10px">
        <view class="lab">选择基酒</view>
        <view class="g2">
          <view
            v-for="s in (specProduct().specs || [])"
            :key="s.id"
            class="icell"
            :class="{ on: specBase === s.id }"
            style="width:calc(50% - 5px)"
            @tap="specBase = s.id"
          >
            {{ s.name }}
            <view class="tiny">{{ s.diff > 0 ? "+" + s.diff : "±0" }}</view>
          </view>
        </view>
      </view>
      <view class="between" style="margin-bottom:12px">
        <text class="ord-sum">{{ specTotal() }} 金币</text>
        <view class="qty">
          <button class="qty-btn ghost" @tap="specQty = Math.max(1, specQty - 1)">−</button>
          <text class="qty-n">{{ specQty }}</text>
          <button class="qty-btn" @tap="specQty++">+</button>
        </view>
      </view>
      <button class="btn block gold" :disabled="!specBase" @tap="addSpec">
        {{ specBase ? "加入购物车" : "请先选择基酒" }}
      </button>
    </view>
  </view>
</template>

<style>
page { height: 100%; overflow: hidden; background: #F5F4F0; }
</style>
<style scoped>
.ord-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #F5F4F0;
}
.ord-sub {
  padding: 6px 14px 4px;
  text-align: right;
  font-size: 11px;
  color: #9C9A93;
  flex-shrink: 0;
}
.ord-main { flex: 1; display: flex; min-height: 0; }
.ord-side {
  width: 78px;
  flex: none;
  background: #F5F4F0;
  border-right: 1px solid rgba(28,27,25,.12);
  height: 100%;
}
.ord-cat {
  padding: 13px 8px;
  font-size: 12px;
  color: #6B6A65;
  text-align: center;
}
.ord-cat.on {
  background: #fff;
  color: #1C1B19;
  font-weight: 600;
}
.ord-list {
  flex: 1;
  height: 100%;
  background: #fff;
  padding-bottom: 12px;
  box-sizing: border-box;
}
.ord-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid rgba(28,27,25,.08);
}
.ord-item.dim { opacity: .55; }
.pth {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  flex: none;
  background: #EDEBE4;
}
.pth.ph {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #9C9A93;
}
.ord-info { flex: 1; min-width: 0; }
.ord-name { font-weight: 600; font-size: 14px; }
.ord-row {
  display: flex;
  align-items: center;
  margin-top: 6px;
}
.ord-price { color: #BA7517; font-weight: 700; font-size: 13px; }
.ord-act { margin-left: auto; }
.qty { display: flex; align-items: center; gap: 8px; }
.qty-n { min-width: 15px; text-align: center; font-weight: 600; }
.qty-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  line-height: 26px;
  border-radius: 50%;
  background: #1C1B19;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin-left: 0;
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.qty-btn.ghost {
  background: #fff;
  color: #1C1B19;
  border: 1px solid rgba(28,27,25,.24);
}
.qty-btn[disabled] { background: #EDEBE4; color: #9C9A93; }
.spec-btn {
  padding: 4px 10px;
  margin: 0;
  font-size: 12px;
  border-radius: 99px;
  border: 1px solid rgba(28,27,25,.24);
  background: #fff;
  color: #1C1B19;
  line-height: 1.3;
}
.ord-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 11px 16px;
  padding-bottom: calc(11px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid rgba(28,27,25,.12);
}
.ord-sum { font-size: 19px; font-weight: 700; color: #BA7517; }
.checkout-btn {
  margin-left: auto;
  padding: 10px 24px;
}
.checkout-btn[disabled] { background: #EDEBE4; color: #9C9A93; }
.lab { font-size: 12px; color: #6B6A65; margin-bottom: 8px; }
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
}
.gal-hd {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.gal-title { font-size: 14px; font-weight: 600; }
.gal-hd .tiny { margin-left: auto; }
</style>

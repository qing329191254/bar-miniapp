<script setup>
import { computed, onMounted, ref } from "vue";
import { api, media } from "@/utils/api";

const cats = ref([]);
const products = ref([]);
const tables = ref([]);
const cid = ref(0);
const cart = ref({});
const payType = ref("COIN");
const tableIdx = ref(0);
const remark = ref("");
const msg = ref("");

onMounted(async () => {
  const r = await api("/products");
  cats.value = r.cats;
  products.value = r.products;
  tables.value = r.tables;
  cid.value = r.cats[0]?.id || 0;
});

const shown = computed(() => products.value.filter((p) => !cid.value || p.cid === cid.value));
const tableNames = computed(() => ["选择桌台（可选）", ...tables.value.map((t) => `${t.area} ${t.name}`)]);
const lines = computed(() =>
  Object.keys(cart.value)
    .map((pid) => {
      const p = products.value.find((x) => x.id === Number(pid));
      const qty = cart.value[pid];
      return p && qty ? { ...p, qty } : null;
    })
    .filter(Boolean),
);
const total = computed(() => lines.value.reduce((s, x) => s + x.price * x.qty, 0));

function add(p) {
  if (p.soldOut) return;
  cart.value = { ...cart.value, [p.id]: (cart.value[p.id] || 0) + 1 };
}
function sub(p) {
  const n = (cart.value[p.id] || 0) - 1;
  const next = { ...cart.value };
  if (n <= 0) delete next[p.id];
  else next[p.id] = n;
  cart.value = next;
}

async function submit() {
  msg.value = "";
  try {
    const tableId = tableIdx.value > 0 ? tables.value[tableIdx.value - 1].id : null;
    const order = await api("/orders", {
      method: "POST",
      body: {
        items: lines.value.map((x) => ({ pid: x.id, qty: x.qty })),
        payType: payType.value,
        tableId,
        remark: remark.value,
      },
    });
    cart.value = {};
    msg.value = `已下单 ${order.no} · ${order.status === "PENDING_ACCEPT" ? "待接单" : "待付款"}`;
  } catch (e) {
    msg.value = e.message;
  }
}
</script>

<template>
  <view class="pbody">
    <scroll-view scroll-x class="catbar">
      <view v-for="c in cats" :key="c.id" class="chip" :class="{ on: cid === c.id }" @tap="cid = c.id">{{ c.name }}</view>
    </scroll-view>
    <view class="card" v-for="p in shown" :key="p.id">
      <view class="between">
        <view class="row" style="flex:1;min-width:0;gap:10px">
          <image v-if="p.img" class="pth" :src="media(p.img)" mode="aspectFill" />
          <view v-else class="pth ph">{{ (p.name || "商").slice(0, 1) }}</view>
          <view style="flex:1;min-width:0">
            <view style="font-weight:600">{{ p.name }}</view>
            <view class="tiny">{{ p.desc }}</view>
            <text class="gold" style="font-weight:700">{{ p.price }} 金币</text>
            <text v-if="p.soldOut" class="pill" style="background:#FCEBEB;color:#A32D2D;margin-left:6px">沽清</text>
          </view>
        </view>
        <view class="row">
          <button class="btn ghost" @tap="sub(p)">−</button>
          <text>{{ cart[p.id] || 0 }}</text>
          <button class="btn" @tap="add(p)">+</button>
        </view>
      </view>
    </view>
    <view class="card" v-if="total">
      <view class="between"><text style="font-weight:600">合计</text><text class="gold" style="font-weight:700">{{ total }} 金币</text></view>
      <view class="row" style="margin:10px 0">
        <button class="btn" :class="payType==='COIN'?'gold':'ghost'" @tap="payType='COIN'">金币</button>
        <button class="btn" :class="payType==='OFFLINE'?'gold':'ghost'" @tap="payType='OFFLINE'">到店付</button>
      </view>
      <picker :value="tableIdx" :range="tableNames" @change="tableIdx = Number($event.detail.value)">
        <view class="field">{{ tableNames[tableIdx] }}</view>
      </picker>
      <input class="field" v-model="remark" placeholder="备注" />
      <button class="btn block gold" @tap="submit">提交订单</button>
    </view>
    <view class="err" v-if="msg">{{ msg }}</view>
  </view>
</template>

<style scoped>
.pth {
  width: 52px;
  height: 52px;
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
</style>

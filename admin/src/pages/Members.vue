<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api";

const route = useRoute();
const router = useRouter();
const members = ref<any[]>([]);
const cards = ref<any[]>([]);
const champs = ref<any[]>([]);
const wdrs = ref<any[]>([]);
const kw = ref("");
const uid = computed(() => Number(route.query.uid || 0));

onMounted(async () => {
  members.value = await api("/admin/members");
  cards.value = await api("/admin/cards");
  champs.value = await api("/admin/champs");
  wdrs.value = await api("/admin/withdrawals");
});

const shown = computed(() =>
  members.value.filter(
    (x) =>
      x.role === "CUSTOMER" &&
      (!kw.value || x.nick.includes(kw.value) || String(x.no).includes(kw.value) || String(x.tail).includes(kw.value)),
  ),
);
const me = computed(() => members.value.find((x) => x.id === uid.value));
function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
</script>

<template>
  <div v-if="me">
    <div class="hdr">会员详情 · {{ me.nick }} <em style="cursor:pointer" @click="router.push('/members')">← 返回列表</em></div>
    <div class="card">
      <div class="st">基本信息</div>
      <div class="cards" style="grid-template-columns:repeat(4,1fr)">
        <div><div class="tiny">会员号</div><b>{{ me.no }}</b></div>
        <div><div class="tiny">手机号</div><b>{{ me.phone }}</b></div>
        <div><div class="tiny">性别</div><b>{{ me.gender===1?'男':(me.gender===2?'女':'未知') }}</b></div>
        <div><div class="tiny">战队</div><b>{{ me.teamName || "（无战队）" }}</b></div>
      </div>
    </div>
    <div class="cards">
      <div class="mtr"><div class="k">金币</div><div class="v" style="color:#BA7517">{{ fmt(me.coin.total) }}</div><div class="tiny">本金 {{ fmt(me.coin.p) }} / 赠送 {{ fmt(me.coin.b) }}</div></div>
      <div class="mtr"><div class="k">积分</div><div class="v" style="color:#185FA5">{{ fmt(me.point.av) }}</div><div class="tiny">周 {{ fmt(me.point.wg) }} · 冻结 {{ fmt(me.point.fz) }}</div></div>
      <div class="mtr"><div class="k">碎片</div><div class="v" style="color:#534AB7">{{ fmt(me.shard.w) }}</div><div class="tiny">历史 {{ fmt(me.shard.t) }}</div></div>
      <div class="mtr"><div class="k">卡包</div><div class="v">{{ cards.filter(c=>c.uid===me.id && c.status==='UNUSED').length }} 张</div></div>
    </div>
    <div class="card">
      <div class="st">个人冠军 <em>{{ champs.filter(c=>c.uid===me.id).length }} 次</em></div>
      <div class="li" v-for="(ch,i) in champs.filter(c=>c.uid===me.id).slice(0,6)" :key="i">
        <div class="gr"><b>{{ ch.event }}</b><span class="tiny">{{ ch.date }} · 参赛 {{ ch.n }} 人 · 获奖时 {{ ch.teamName }}</span></div>
      </div>
      <div class="tiny" v-if="!champs.filter(c=>c.uid===me.id).length">暂无夺冠记录</div>
    </div>
  </div>
  <div v-else>
    <div class="hdr">会员列表 <em>{{ shown.length }} 人 · 点击查看详情</em></div>
    <input class="inp" style="max-width:260px;margin-bottom:11px" placeholder="搜索昵称 / 会员号 / 手机尾号" v-model="kw" />
    <div class="card" style="padding:0;overflow-x:auto">
      <table class="tb2" data-cols="lcccccc">
        <thead>
          <tr><th>会员</th><th>手机</th><th>战队</th><th>金币</th><th>积分</th><th>碎片(周/总)</th><th></th></tr>
        </thead>
        <tbody>
        <tr v-for="x in shown" :key="x.id" style="cursor:pointer" @click="router.push('/members?uid='+x.id)">
          <td><b>{{ x.nick }}</b><div class="tiny">{{ x.no }}</div></td>
          <td>{{ x.phone }}</td>
          <td class="tiny">{{ x.teamName || "—" }}</td>
          <td><b style="color:#BA7517">{{ fmt(x.coin.total) }}</b></td>
          <td><b style="color:#185FA5">{{ fmt(x.point.av) }}</b></td>
          <td class="tiny">{{ fmt(x.shard.w) }} / {{ fmt(x.shard.t) }}</td>
          <td class="tiny" style="color:#185FA5">详情 ›</td>
        </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

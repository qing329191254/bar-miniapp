<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";

const router = useRouter();
const preset = ref("7d");
const rows = ref<any[]>([]);
const loading = ref(true);

const ROLE: Record<string, string> = { STAFF: "店员", MANAGER: "店长", BOSS: "老板" };

function fmt(n: number) {
  return Number(n || 0).toLocaleString("en-US");
}
function openDetail(uid: number) {
  router.push({ path: `/jobs/${uid}`, query: { preset: preset.value } });
}
async function load() {
  loading.value = true;
  try {
    rows.value = await api("/admin/jobs?preset=" + preset.value);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">
      <span class="hdr-title">员工作业记录</span>
      <em class="hdr-note">含核销 / 接单 / 收款 / 对局录入全量流水</em>
    </div>
    <div class="card">
      <div class="st">筛选</div>
      <div class="flt-chips">
        <span class="chip" :class="{ on: preset === 'today' }" @click="preset = 'today'; load()">今天</span>
        <span class="chip" :class="{ on: preset === '7d' }" @click="preset = '7d'; load()">近 7 天</span>
        <span class="chip" :class="{ on: preset === '30d' }" @click="preset = '30d'; load()">近 30 天</span>
        <span class="chip" :class="{ on: preset === 'month' }" @click="preset = 'month'; load()">本月</span>
      </div>
    </div>
    <div v-if="loading" class="card"><p class="tiny" style="padding:24px;text-align:center">加载中…</p></div>
    <div v-else class="card" style="padding:0;overflow:auto">
      <table class="tb2" data-cols="lccccccc">
        <thead>
          <tr>
            <th>员工</th><th>角色</th><th>接单</th><th>经手金额</th><th>核销</th><th>对局</th><th>发分</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.user.id">
            <td><b>{{ r.user.nick }}</b><div class="tiny">{{ r.user.phone }}</div></td>
            <td><span class="pill" style="background:#E6F1FB;color:#185FA5">{{ ROLE[r.user.role] || r.user.role }}</span></td>
            <td>{{ r.orders }}</td>
            <td><b>¥{{ fmt(r.amount) }}</b></td>
            <td>{{ r.verifies }}</td>
            <td>{{ r.games }}</td>
            <td>{{ r.wds }}</td>
            <td><button class="btn sm ghost" @click="openDetail(r.user.id)">查看流水</button></td>
          </tr>
          <tr v-if="!rows.length"><td colspan="8" class="tiny" style="text-align:center;padding:26px">当前筛选条件下无员工</td></tr>
        </tbody>
      </table>
    </div>
    <div class="note">
      <b>口径：</b>作业总量 = 接单 + 确认充值 + 核销 + 对局录入的条目数之和。<b>经手金额</b>只计已归属经手人的单。<b>发分</b>为经手确认发放的提分单笔数。
    </div>
  </div>
</template>

<style scoped>
.flt-chips { display: flex; flex-wrap: wrap; gap: 6px; }
</style>

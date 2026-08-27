<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";

const preset = ref("7d");
const rows = ref<any[]>([]);

async function load() {
  rows.value = await api("/admin/jobs?preset=" + preset.value);
}
onMounted(load);
</script>

<template>
  <div>
    <div class="hdr">员工作业记录</div>
    <div style="margin:8px 0">
      <button class="btn" :class="preset==='today'?'gold':'ghost'" @click="preset='today';load()">今日</button>
      <button class="btn" :class="preset==='7d'?'gold':'ghost'" @click="preset='7d';load()">7 天</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>员工</th><th>经手金额</th><th>充值收款</th><th>点单收款</th>
          <th>接单数</th><th>核销数</th><th>录局数</th><th>发分数</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.user.id">
          <td>{{ r.user.nick }} · {{ { STAFF: "店员", MANAGER: "店长", BOSS: "老板" }[r.user.role] || r.user.role }}</td>
          <td>{{ r.amount }}</td><td>{{ r.rcAmt }}</td><td>{{ r.odAmt }}</td>
          <td>{{ r.orders }}</td><td>{{ r.verifies }}</td><td>{{ r.games }}</td><td>{{ r.wds }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

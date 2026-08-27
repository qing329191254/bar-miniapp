<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, setSession } from "../api";

const router = useRouter();
const staff = ref<any[]>([]);
const err = ref("");

onMounted(async () => {
  try {
    const r = await api<any>("/dev/accounts");
    staff.value = r.staff.filter((u: any) => u.role === "MANAGER" || u.role === "BOSS");
  } catch (e: any) {
    err.value = e.message || "无法连接后端";
  }
});

async function pick(id: number) {
  try {
    const r = await api<any>("/auth/login", { method: "POST", body: { userId: id } });
    if (r.user.role === "CUSTOMER") {
      err.value = "请用店长或老板账号";
      return;
    }
    setSession(r.token, r.user);
    router.replace("/dash");
  } catch (e: any) {
    err.value = e.message;
  }
}
</script>

<template>
  <div class="login">
    <h2>玩咖桌游酒吧 · 管理后台</h2>
    <p class="tiny" style="margin:8px 0 16px">店长 / 老板登录。资产负债与调账审批仅老板可见。</p>
    <p style="color:#A32D2D" v-if="err">{{ err }}</p>
    <button class="acct" v-for="u in staff" :key="u.id" @click="pick(u.id)">
      <b>{{ u.nick }}</b> · {{ u.role === "BOSS" ? "老板" : "店长" }}
    </button>
  </div>
</template>

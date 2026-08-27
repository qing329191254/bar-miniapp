<script setup>
import { onMounted, ref } from "vue";
import { api, setSession, relaunch } from "@/utils/api";

const accounts = ref({ customers: [], staff: [] });
const err = ref("");

onMounted(async () => {
  try {
    accounts.value = await api("/dev/accounts");
  } catch (e) {
    err.value = e.message || "无法连接服务器，请确认后端已启动，并在微信开发者工具关闭域名校验。";
  }
});

async function pick(id) {
  err.value = "";
  try {
    const r = await api("/auth/login", { method: "POST", body: { userId: id } });
    setSession(r.token, r.user);
    relaunch(r.user.role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo");
  } catch (e) {
    err.value = e.message;
  }
}
</script>

<template>
  <view class="pbody">
    <view class="tiny" style="margin-bottom:12px">选一个演示账号进入。会员走 C 端，店员/店长/老板进待办。</view>
    <view class="err" v-if="err">{{ err }}</view>
    <view class="h2">会员</view>
    <button class="acct" v-for="u in accounts.customers" :key="u.id" @tap="pick(u.id)">
      <view class="av">{{ u.av }}</view>
      <view>
        <view style="font-weight:600">{{ u.nick }}</view>
        <view class="tiny">{{ u.no }} · 金币 {{ u.coin.total }}</view>
      </view>
    </button>
    <view class="h2" style="margin-top:16px">员工</view>
    <button class="acct" v-for="u in accounts.staff" :key="u.id" @tap="pick(u.id)">
      <view class="av">{{ u.av }}</view>
      <view>
        <view style="font-weight:600">{{ u.nick }}</view>
        <view class="tiny">{{ u.role }} · {{ u.no }}</view>
      </view>
    </button>
  </view>
</template>

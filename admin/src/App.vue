<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearSession, savedUser } from "./api";
import AppToast from "./components/AppToast.vue";

const route = useRoute();
const router = useRouter();
const user = computed(() => savedUser());
const isBoss = computed(() => user.value?.role === "BOSS");

const BOSS_ONLY = new Set(["staff", "logs", "settlecfg"]);
const COLLAPSE_KEY = "wanka_admin_nav_off";

function loadOff(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(COLLAPSE_KEY) || "{}");
  } catch {
    return {};
  }
}

const off = reactive<Record<string, boolean>>(loadOff());

function persistOff() {
  localStorage.setItem(COLLAPSE_KEY, JSON.stringify({ ...off }));
}

const groups = computed(() => {
  const all: { g: string; items: { k: string; n: string }[] }[] = [
    { g: "经营", items: [
      { k: "dash", n: "数据看板" },
      { k: "dailyBiz", n: "营业一览" },
      { k: "orders", n: "订单记录与管理" },
      { k: "recharges", n: "充值记录与管理" },
      { k: "jobs", n: "员工作业记录" },
      { k: "reports", n: "报表与对账" },
    ] },
    { g: "对局", items: [
      { k: "gameinput", n: "对局结果录入" },
      { k: "gameRecords", n: "对局记录查询" },
      { k: "settle", n: "榜单与结算" },
      { k: "rankHistory", n: "榜单历史记录" },
      { k: "settlecfg", n: "榜单与奖励规则" },
      { k: "projects", n: "对局项目配置" },
    ] },
    { g: "积分", items: [{ k: "withdrawals", n: "提分单管理" }] },
    { g: "商品", items: [{ k: "products", n: "商品管理" }] },
    { g: "营销", items: [
      { k: "cardTpls", n: "卡券配置" },
      { k: "tiers", n: "充值档位配置" },
      { k: "signRules", n: "签到奖励配置" },
    ] },
    { g: "会员", items: [{ k: "members", n: "会员列表" }, { k: "deactivations", n: "注销申请处理" }, { k: "teams", n: "战队管理" }] },
    { g: "内容", items: [{ k: "content", n: "店铺相册与玩法" }, { k: "agreement", n: "协议与政策" }] },
    { g: "设置", items: [
      { k: "push", n: "消息推送" },
      { k: "shopinfo", n: "门店信息" },
      { k: "config", n: "风控参数" },
      { k: "staff", n: "员工与权限" },
      { k: "logs", n: "操作日志" },
    ] },
  ];
  return all
    .map((grp) => ({
      ...grp,
      items: grp.items.filter((it) => isBoss.value || !BOSS_ONLY.has(it.k)),
    }))
    .filter((grp) => grp.items.length);
});

function on(k: string) {
  const p = route.path.replace("/", "") || "dash";
  return p === k;
}
function bossOnly(k: string) {
  return BOSS_ONLY.has(k);
}
function toggle(g: string) {
  off[g] = !off[g];
  persistOff();
}

function onFoldEnd(el: HTMLElement, done: () => void, after?: () => void) {
  let doneOnce = false;
  const finish = (ev?: TransitionEvent) => {
    if (doneOnce) return;
    if (ev?.propertyName && ev.propertyName !== "height") return;
    doneOnce = true;
    el.removeEventListener("transitionend", finish);
    after?.();
    done();
  };
  el.addEventListener("transitionend", finish);
  window.setTimeout(() => finish({ propertyName: "height" } as TransitionEvent), 280);
}

function foldEnter(el: Element, done: () => void) {
  const e = el as HTMLElement;
  e.style.height = "0";
  e.style.overflow = "hidden";
  e.style.opacity = "0";
  void e.offsetHeight;
  e.style.transition = "height .22s ease, opacity .18s ease";
  e.style.height = `${e.scrollHeight}px`;
  e.style.opacity = "1";
  onFoldEnd(e, done, () => {
    e.style.height = "";
    e.style.overflow = "";
    e.style.opacity = "";
    e.style.transition = "";
  });
}

function foldLeave(el: Element, done: () => void) {
  const e = el as HTMLElement;
  e.style.height = `${e.scrollHeight}px`;
  e.style.overflow = "hidden";
  e.style.opacity = "1";
  void e.offsetHeight;
  e.style.transition = "height .22s ease, opacity .18s ease";
  e.style.height = "0";
  e.style.opacity = "0";
  onFoldEnd(e, done);
}
function logout() {
  clearSession();
  router.replace("/");
}
function roleName() {
  const r = user.value?.role;
  if (r === "BOSS") return "老板";
  if (r === "MANAGER") return "店长";
  return "员工";
}

watch(
  () => route.path,
  (p) => {
    const k = p.replace("/", "") || "dash";
    const grp = groups.value.find((g) => g.items.some((it) => it.k === k));
    if (grp && off[grp.g]) {
      off[grp.g] = false;
      persistOff();
    }
  },
  { immediate: true },
);
</script>

<template>
  <div v-if="route.path === '/'" class="login-wrap">
    <router-view />
  </div>
  <div v-else class="layout">
    <div class="wtop">
      <img class="brand-logo" src="/logo.png" alt="" />
      <b style="margin-left:8px;font-size:14px">玩咖桌游酒吧 · 管理后台</b>
      <span class="tiny" style="margin-left:auto">{{ roleName() }} · {{ user?.nick }}{{ isBoss ? "" : " · 不含负债与毛利" }}</span>
      <div style="width:24px;height:24px;border-radius:50%;background:#EDEBE4;display:flex;align-items:center;justify-content:center;font-size:11px">{{ (user?.nick || "管").slice(-1) }}</div>
    </div>
    <div class="wbody">
      <aside class="side">
        <nav class="side-scroll">
          <div class="side-scroll-inner">
            <template v-for="grp in groups" :key="grp.g">
              <div class="ngrp" :class="{ off: off[grp.g] }" @click="toggle(grp.g)">
                <span>{{ grp.g }}</span>
                <svg class="chev" viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M6 3.5 11 8 6 12.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <Transition @enter="foldEnter" @leave="foldLeave">
                <div v-if="!off[grp.g]" class="nav-items">
                  <router-link
                    v-for="it in grp.items"
                    :key="it.k"
                    class="nit"
                    :class="{ on: on(it.k) }"
                    :to="'/' + it.k"
                  >
                    <span>{{ it.n }}</span>
                  </router-link>
                </div>
              </Transition>
            </template>
          </div>
        </nav>
        <div class="side-foot">
          <button class="btn ghost" style="width:100%" @click="logout">退出 / 切换账号</button>
        </div>
      </aside>
      <main class="main"><router-view /></main>
    </div>
    <AppToast />
  </div>
</template>

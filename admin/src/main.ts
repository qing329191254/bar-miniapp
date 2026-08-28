import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";
import { savedUser, token } from "./api";
import Login from "./pages/Login.vue";
import Dashboard from "./pages/Dashboard.vue";
import Collection from "./pages/Collection.vue";
import Jobs from "./pages/Jobs.vue";
import Records from "./pages/Records.vue";
import Members from "./pages/Members.vue";
import Products from "./pages/Products.vue";
import GameInput from "./pages/GameInput.vue";
import Content from "./pages/Content.vue";
import Agreement from "./pages/Agreement.vue";
import Config from "./pages/Config.vue";
import CardTemplates from "./pages/CardTemplates.vue";
import WithdrawalManagement from "./pages/WithdrawalManagement.vue";
import SignRewards from "./pages/SignRewards.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Login },
    { path: "/dash", component: Dashboard },
    { path: "/jobs", component: Jobs },
    { path: "/orders", component: Records },
    { path: "/recharges", component: Records },
    { path: "/withdrawals", component: WithdrawalManagement },
    { path: "/gameRecords", component: Records },
    { path: "/members", component: Members },
    { path: "/products", component: Products },
    { path: "/gameinput", component: GameInput },
    { path: "/content", component: Content },
    { path: "/agreement", component: Agreement },
    { path: "/config", component: Config },
    { path: "/cardTpls", component: CardTemplates },
    { path: "/signRules", component: SignRewards },
    { path: "/:coll", component: Collection },
  ],
});
const BOSS_ONLY = new Set(["/tiers", "/staff", "/logs", "/cfg", "/settlecfg", "/coinAdjusts"]);
router.beforeEach((to) => {
  if (to.path === "/") return true;
  if (!token()) return "/";
  const role = savedUser()?.role;
  if (role === "CUSTOMER" || role === "STAFF") {
    return "/";
  }
  if (BOSS_ONLY.has(to.path) && role !== "BOSS") return "/dash";
  return true;
});
createApp(App).use(router).mount("#app");

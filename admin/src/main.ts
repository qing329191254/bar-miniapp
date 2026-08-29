import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";
import { savedUser, token } from "./api";
import Login from "./pages/Login.vue";
import Dashboard from "./pages/Dashboard.vue";
import Collection from "./pages/Collection.vue";
import Jobs from "./pages/Jobs.vue";
import JobDetail from "./pages/JobDetail.vue";
import Orders from "./pages/Orders.vue";
import Recharges from "./pages/Recharges.vue";
import Reports from "./pages/Reports.vue";
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
import Teams from "./pages/Teams.vue";
import Settlement from "./pages/Settlement.vue";
import SettlementHistory from "./pages/SettlementHistory.vue";
import SettlementConfig from "./pages/SettlementConfig.vue";
import DailyBiz from "./pages/DailyBiz.vue";
import CoinAdjust from "./pages/CoinAdjust.vue";
import Deactivations from "./pages/Deactivations.vue";
import DeactivationDetail from "./pages/DeactivationDetail.vue";
import DashDrill from "./pages/DashDrill.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Login },
    { path: "/dash", component: Dashboard },
    { path: "/dailyBiz", component: DailyBiz },
    { path: "/liabCoin", component: DashDrill, props: { kind: "coin" } },
    { path: "/liabPoint", component: DashDrill, props: { kind: "point" } },
    { path: "/liabCard", component: DashDrill, props: { kind: "card" } },
    { path: "/alertPoint", component: DashDrill, props: { kind: "alert" } },
    { path: "/coinAdjusts", component: CoinAdjust },
    { path: "/deactivations", component: Deactivations },
    { path: "/deactivations/:id", component: DeactivationDetail },
    { path: "/jobs", component: Jobs },
    { path: "/jobs/:uid", component: JobDetail },
    { path: "/orders", component: Orders },
    { path: "/recharges", component: Recharges },
    { path: "/reports", component: Reports },
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
    { path: "/teams", component: Teams },
    { path: "/settle", component: Settlement },
    { path: "/rankHistory", component: SettlementHistory },
    { path: "/settlecfg", component: SettlementConfig },
    { path: "/:coll", component: Collection },
  ],
});
const BOSS_ONLY = new Set(["/tiers", "/staff", "/logs", "/cfg", "/settlecfg", "/liabCoin", "/liabPoint", "/liabCard"]);
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

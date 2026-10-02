<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppSelect from "../components/AppSelect.vue";
import { showToast } from "../composables/useToast";

type Config = {
  rankDim: "WEEK" | "MONTH";
  rankRange: number;
  prizeMap: Record<string, string>;
  teamReward: boolean;
  teamCard: string;
  stack: boolean;
  reqShard: boolean;
  settleCap: number;
};
type CardTpl = { id: number; name: string; sub?: string; cat?: string };

const defaults: Config = {
  rankDim: "WEEK",
  rankRange: 3,
  prizeMap: {},
  teamReward: true,
  teamCard: "",
  stack: true,
  reqShard: true,
  settleCap: 20,
};

const cfg = ref<Config>({ ...defaults, prizeMap: {} });
const templates = ref<CardTpl[]>([]);
const loading = ref(true);
const loaded = ref(false);
const err = ref("");
const saving = ref(false);
const orphanHint = ref("");

const prizeRows = computed(() => {
  const half = Math.ceil(cfg.value.rankRange / 2);
  return Array.from({ length: half }, (_, i) => [
    i + 1,
    i + 1 + half <= cfg.value.rankRange ? i + 1 + half : 0,
  ]);
});
const dimHint = computed(() =>
  cfg.value.rankDim === "WEEK"
    ? "当期从每周一 12:00 起算 · 下周一 12:00 结算发奖励卡"
    : "当期从每月 1 日 12:00 起算 · 次月 1 日 12:00 结算发奖励卡 · 1 日 13:00 积分清零",
);

/** Options come only from live 卡券配置 (template id). */
const rewardOpts = computed(() =>
  templates.value.map((t) => ({
    value: String(t.id),
    label: t.name,
  })),
);

const tplById = computed(() =>
  Object.fromEntries(templates.value.map((t) => [String(t.id), t])),
);
const tplBySub = computed(() =>
  Object.fromEntries(
    templates.value.filter((t) => t.sub).map((t) => [String(t.sub), t]),
  ),
);

function resolveRef(ref: string | number | undefined | null): string {
  const raw = String(ref ?? "").trim();
  if (!raw) return "";
  if (tplById.value[raw]) return raw;
  if (raw.startsWith("TPL_") && tplById.value[raw.slice(4)]) return raw.slice(4);
  const bySub = tplBySub.value[raw];
  return bySub ? String(bySub.id) : "";
}

function defaultTplId(rank = 1): string {
  if (!templates.value.length) return "";
  // Prefer common treasure order when present; otherwise first template.
  const prefer = ["TREASURE_DIAMOND", "TREASURE_GOLD", "TREASURE_SILVER", "TREASURE_BRONZE", "TREASURE_TEAM"];
  const pick = prefer[Math.min(Math.max(rank, 1) - 1, prefer.length - 1)];
  const hit = templates.value.find((t) => t.sub === pick);
  return String((hit || templates.value[0]).id);
}

function setRange(value: number | string) {
  const n = Math.max(1, Math.min(20, Math.floor(Number(value) || 1)));
  cfg.value.rankRange = n;
  for (let i = 1; i <= n; i++) {
    const key = String(i);
    const resolved = resolveRef(cfg.value.prizeMap[key]);
    cfg.value.prizeMap[key] = resolved || defaultTplId(i);
  }
  // Drop ranks outside range from local map (save also trims via rankRange UI).
  for (const k of Object.keys(cfg.value.prizeMap)) {
    if (Number(k) > n) delete cfg.value.prizeMap[k];
  }
}

function setCap(value: number | string) {
  cfg.value.settleCap = Math.max(1, Math.min(999, Math.floor(Number(value) || 20)));
}

function migrateLoadedCfg(raw: Partial<Config>) {
  const next: Config = {
    ...defaults,
    ...raw,
    prizeMap: { ...(raw.prizeMap || {}) },
  };
  const missing: string[] = [];
  const prize: Record<string, string> = {};
  for (const [k, v] of Object.entries(next.prizeMap)) {
    if (!/^\d+$/.test(k)) continue;
    const id = resolveRef(v);
    if (id) prize[k] = id;
    else if (v) missing.push(`第 ${k} 名`);
  }
  next.prizeMap = prize;
  const teamId = resolveRef(next.teamCard);
  if (next.teamCard && !teamId) missing.push("战队奖励");
  next.teamCard = teamId || (next.teamReward ? defaultTplId(4) : "");
  orphanHint.value = missing.length
    ? `原配置中的 ${missing.join("、")} 卡型已不在卡券配置中，已清空请重新选择`
    : "";
  return next;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const d = await api<any>("/admin/settlement-config");
    templates.value = d.templates || [];
    cfg.value = migrateLoadedCfg({ ...defaults, ...(d.cfg || {}) });
    setRange(cfg.value.rankRange);
    setCap(cfg.value.settleCap);
    if (!cfg.value.teamCard && cfg.value.teamReward) {
      cfg.value.teamCard = defaultTplId(4);
    }
    loaded.value = true;
  } catch (e: any) {
    err.value = e?.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!templates.value.length) {
    showToast("请先在「卡券配置」中新增卡券后再设置奖励", true);
    return;
  }
  setRange(cfg.value.rankRange);
  setCap(cfg.value.settleCap);
  for (let i = 1; i <= cfg.value.rankRange; i++) {
    if (!resolveRef(cfg.value.prizeMap[String(i)])) {
      showToast(`请为第 ${i} 名选择卡券配置中的奖励卡型`, true);
      return;
    }
  }
  if (cfg.value.teamReward && !resolveRef(cfg.value.teamCard)) {
    showToast("请选择战队奖励卡型", true);
    return;
  }
  saving.value = true;
  try {
    await api("/admin/settlement-config", { method: "PUT", body: { data: cfg.value } });
    orphanHint.value = "";
    showToast("规则已保存，顾客端榜单已同步更新");
  } catch (e: any) {
    showToast(e?.message || "保存失败", true);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="settle-config-page">
    <div class="hdr settle-config-hdr">
      <span class="hdr-title">榜单与奖励规则</span>
      <em class="hdr-note">影响顾客端榜单与周期奖励 · 仅老板可编辑</em>
    </div>
    <AppAsyncPage
      :loading="loading"
      :data="loaded"
      :err="err"
      :skeleton="{ variant: 'form', formSections: 3, formColumns: 1, showHeader: false, showFilter: false, metrics: 0, showNote: true }"
      @retry="load"
    >
      <section class="card">
        <div class="st">榜单统计口径</div>
        <div class="dimension-row">
          <div class="chip-row">
            <button class="chip" :class="{ on: cfg.rankDim === 'WEEK' }" @click="cfg.rankDim = 'WEEK'">周维度</button>
            <button class="chip" :class="{ on: cfg.rankDim === 'MONTH' }" @click="cfg.rankDim = 'MONTH'">月维度</button>
          </div>
          <span class="tiny">{{ dimHint }}</span>
        </div>
        <div class="note section-note">切换后，顾客端碎片榜/冠军榜的「当期新增」会变成当周或当月。积分榜固定为当前可用积分，不随周/月切换。</div>
      </section>

      <section class="card">
        <div class="st">个人奖励 <em>名次占位制 · 超出范围不发 · 卡型来自卡券配置</em></div>
        <div class="range-row">
          <span class="tiny">发放名次范围</span>
          <button v-for="n in [1, 3, 5, 10]" :key="n" class="chip" :class="{ on: cfg.rankRange === n }" @click="setRange(n)">前 {{ n }} 名</button>
          <span class="tiny custom-label">自定义</span>
          <input
            :value="cfg.rankRange"
            class="inp range-input"
            type="number"
            min="1"
            max="20"
            @change="setRange(($event.target as HTMLInputElement).value)"
          />
          <span class="tiny">名（1-20）</span>
        </div>
        <div v-if="!rewardOpts.length" class="note warn-note">卡券配置中暂无卡券，请先新增卡券后再设置奖励。</div>
        <div v-else class="tb-wrap">
          <table class="tb2 prize-table">
            <thead>
              <tr>
                <th>名次</th>
                <th>奖励卡型</th>
                <th>名次</th>
                <th>奖励卡型</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pair in prizeRows" :key="pair[0]">
                <template v-for="rank in pair" :key="rank || 'empty'">
                  <template v-if="rank">
                    <td>第 {{ rank }} 名</td>
                    <td>
                      <AppSelect
                        v-model="cfg.prizeMap[String(rank)]"
                        :options="rewardOpts"
                        compact
                        no-margin
                        class="prize-select"
                        placeholder="请选择卡券"
                      />
                    </td>
                  </template>
                  <template v-else>
                    <td></td>
                    <td></td>
                  </template>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="orphanHint" class="note warn-note">{{ orphanHint }}</div>
        <div class="config-footnote">共 {{ cfg.rankRange }} 个名次占位，选项与「卡券配置」实时同步；卡券被删除后需重新选择，否则该名次结算时跳过。</div>
      </section>

      <section class="card">
        <div class="st">战队奖励</div>
        <label class="setting-row">
          <span><b>夺冠战队奖励</b><small>战队榜第 1 全员发放</small></span>
          <input v-model="cfg.teamReward" type="checkbox" class="ui-toggle" />
        </label>
        <label v-if="cfg.teamReward" class="setting-row">
          <span><b>奖励卡型</b><small>来自卡券配置</small></span>
          <AppSelect
            v-model="cfg.teamCard"
            :options="rewardOpts"
            no-margin
            class="team-select"
            placeholder="请选择卡券"
          />
        </label>
        <label class="setting-row">
          <span><b>本人需有碎片</b><small>碎片为 0 的成员跳过，结算记录标记为「本周期无碎片」</small></span>
          <input v-model="cfg.reqShard" type="checkbox" class="ui-toggle" />
        </label>
      </section>

      <section class="card">
        <div class="st">奖励叠加</div>
        <label class="setting-row no-border">
          <span><b>同一用户战队奖 + 个人奖可同发</b></span>
          <input v-model="cfg.stack" type="checkbox" class="ui-toggle" />
        </label>
      </section>

      <section class="card cap-card">
        <div class="st">结算发放上限 <em>重要资金规则 · 仅老板可编辑</em></div>
        <label class="setting-row no-border">
          <span>
            <b>单次自动结算发放卡券总张数上限</b>
            <small>超过则整批置「被拦截」、一张不发，仅老板可强制发放。手动补发不受此上限约束</small>
          </span>
          <input
            :value="cfg.settleCap"
            class="inp cap-input"
            type="number"
            min="1"
            max="999"
            @change="setCap(($event.target as HTMLInputElement).value)"
          />
        </label>
        <div class="config-footnote cap-help">
          发放名次与卡券总量是两项独立限制。出现多人并列或叠加战队奖时，即使只奖励前 3 名，也可能发出更多卡券；总量上限可帮助门店控制奖励成本。<b>修改后仅影响后续结算</b>，已发放或已拦截的批次不会自动变化，仍需老板在「榜单与结算」中处理。
        </div>
      </section>

      <button class="btn pri save-btn" :disabled="saving || !rewardOpts.length" @click="save">
        {{ saving ? "保存中…" : "保存规则" }}
      </button>
      <div class="note final-note">
        <b>口径说明：</b>碎片榜「历史」= 永久累计；积分榜 = 实时可用库存（个人库存 / 战队为成员之和）；冠军榜可看当周或累计。周维度每周一 12:00 自动结算碎片奖励；月维度次月 1 日 12:00 自动结算。<b>发奖以冻结快照为准</b>，结算后调队不影响已发放奖励；极端并列无上界，结算预览页会显示发放总量。
      </div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.settle-config-page{width:100%;min-width:0}.settle-config-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}.dimension-row,.range-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.dimension-row{justify-content:space-between}.chip-row{display:flex;gap:6px}.chip{font-family:inherit}.section-note{margin:9px 0 0}.range-row{margin-bottom:10px}.custom-label{margin-left:4px}.range-input{width:78px;margin:0;padding:4px 7px;font-size:12px}.prize-table th:nth-child(odd){width:14%}.prize-table th:nth-child(even){width:36%}.prize-table :deep(.prize-select){width:100%}.config-footnote{margin-top:7px;color:var(--ink3);font-size:11px;line-height:1.7}.setting-row{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:11px 0;border-bottom:1px solid var(--line);cursor:pointer}.setting-row.no-border{border-bottom:0}.setting-row span{min-width:0}.setting-row b{display:block;font-size:13px;font-weight:500}.setting-row small{display:block;margin-top:2px;color:var(--ink2);font-size:11px;font-weight:400}.setting-row :deep(.team-select){width:220px;flex:none}.cap-input{width:90px;margin:0;padding:5px 8px;text-align:right}.cap-help b{color:var(--ink2)}.save-btn{margin-bottom:11px}.save-btn:disabled{opacity:.55;cursor:not-allowed}.final-note{margin-bottom:0}.warn-note{margin-top:8px;color:#A32D2D}@media(max-width:720px){.settle-config-hdr .hdr-note{margin-left:0;text-align:left;width:100%}.setting-row{align-items:flex-start}.setting-row :deep(.team-select){width:min(220px,50%)}.prize-table{min-width:620px}}
</style>

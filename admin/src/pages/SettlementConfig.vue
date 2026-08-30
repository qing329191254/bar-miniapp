<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";

type Config = {
  rankDim:"WEEK"|"MONTH"; rankRange:number; prizeMap:Record<string,string>;
  teamReward:boolean; teamCard:string; stack:boolean; reqShard:boolean; settleCap:number;
};
type CardTpl = { id:number; name:string; sub:string };

const defaults:Config={rankDim:"WEEK",rankRange:3,prizeMap:{1:"TREASURE_DIAMOND",2:"TREASURE_GOLD",3:"TREASURE_SILVER"},teamReward:true,teamCard:"TREASURE_TEAM",stack:true,reqShard:true,settleCap:20};
const cfg=ref<Config>({...defaults,prizeMap:{...defaults.prizeMap}}), templates=ref<CardTpl[]>([]);
const loading=ref(true), err=ref(""), message=ref(""), saving=ref(false);
const fallback=["TREASURE_DIAMOND","TREASURE_GOLD","TREASURE_SILVER"];
const personalSubs=["TREASURE_DIAMOND","TREASURE_GOLD","TREASURE_SILVER","TREASURE_TEAM"];
const teamSubs=["TREASURE_TEAM","TREASURE_SILVER","TREASURE_DIAMOND"];

const templateMap=computed(()=>Object.fromEntries(templates.value.map(t=>[t.sub,t])));
const prizeRows=computed(()=>{const half=Math.ceil(cfg.value.rankRange/2);return Array.from({length:half},(_,i)=>[i+1,i+1+half<=cfg.value.rankRange?i+1+half:0])});
const dimHint=computed(()=>cfg.value.rankDim==="WEEK"?"周一 00:00 重置 · 结算发宝箱卡":"按自然月累计 · 随月底清零归零");

function setRange(value:number|string){
  const n=Math.max(1,Math.min(20,Math.floor(Number(value)||1))); cfg.value.rankRange=n;
  for(let i=1;i<=n;i++)if(!cfg.value.prizeMap[String(i)])cfg.value.prizeMap[String(i)]=fallback[Math.min(i-1,2)];
}
function setCap(value:number|string){cfg.value.settleCap=Math.max(1,Math.min(999,Math.floor(Number(value)||20)))}
function optionName(sub:string){return templateMap.value[sub]?.name||({TREASURE_DIAMOND:"钻石宝箱卡",TREASURE_GOLD:"黄金宝箱卡",TREASURE_SILVER:"白银宝箱卡",TREASURE_TEAM:"战队宝箱卡"} as Record<string,string>)[sub]||sub}
async function load(){loading.value=true;err.value="";try{const d=await api<any>("/admin/settlement-config");cfg.value={...defaults,...(d.cfg||{}),prizeMap:{...defaults.prizeMap,...(d.cfg?.prizeMap||{})}};templates.value=d.templates||[];setRange(cfg.value.rankRange);setCap(cfg.value.settleCap)}catch(e:any){err.value=e?.message||"加载失败"}finally{loading.value=false}}
async function save(){saving.value=true;message.value="";try{setRange(cfg.value.rankRange);setCap(cfg.value.settleCap);await api("/admin/settlement-config",{method:"PUT",body:{data:cfg.value}});message.value="规则已保存，C 端榜单同步生效"}catch(e:any){message.value=e?.message||"保存失败"}finally{saving.value=false}}
onMounted(load);
</script>

<template>
  <div class="settle-config-page">
    <div class="hdr settle-config-hdr"><span class="hdr-title">榜单与奖励规则</span><em class="hdr-note">影响 C 端榜单口径与周/月结算发放 · 仅老板可改</em></div>
    <AppAsyncPage :loading="loading" :data="cfg" :err="err" @retry="load">
      <div v-if="message" class="save-message" :class="{error:message.includes('失败')}">{{ message }}</div>

      <section class="card">
        <div class="st">榜单统计口径</div>
        <div class="dimension-row"><div class="chip-row"><button class="chip" :class="{on:cfg.rankDim==='WEEK'}" @click="cfg.rankDim='WEEK'">周维度</button><button class="chip" :class="{on:cfg.rankDim==='MONTH'}" @click="cfg.rankDim='MONTH'">月维度</button></div><span class="tiny">{{ dimHint }}</span></div>
        <div class="note section-note">切换后 C 端榜单的「当周新增/当月新增」维度随之变化；碎片按当月对局聚合、积分取当月累计、冠军取当月夺冠数。</div>
      </section>

      <section class="card">
        <div class="st">个人奖励 <em>名次占位制 · 超出范围不发</em></div>
        <div class="range-row"><span class="tiny">发放名次范围</span><button v-for="n in [1,3,5,10]" :key="n" class="chip" :class="{on:cfg.rankRange===n}" @click="setRange(n)">前 {{ n }} 名</button><span class="tiny custom-label">自定义</span><input :value="cfg.rankRange" class="inp range-input" type="number" min="1" max="20" @change="setRange(($event.target as HTMLInputElement).value)"/><span class="tiny">名（1-20）</span></div>
        <div class="tb-wrap"><table class="tb2 prize-table"><thead><tr><th>名次</th><th>奖励卡型</th><th>名次</th><th>奖励卡型</th></tr></thead><tbody>
          <tr v-for="pair in prizeRows" :key="pair[0]">
            <template v-for="rank in pair" :key="rank||'empty'">
              <template v-if="rank"><td>第 {{ rank }} 名</td><td><select v-model="cfg.prizeMap[String(rank)]" class="inp prize-select"><option v-for="sub in personalSubs" :key="sub" :value="sub">{{ optionName(sub) }}</option></select></td></template>
              <template v-else><td></td><td></td></template>
            </template>
          </tr>
        </tbody></table></div>
        <div class="config-footnote">共 {{ cfg.rankRange }} 个名次占位，超出范围的名次不发奖。缺卡型映射的名次结算时自动跳过并在日志标注。</div>
      </section>

      <section class="card">
        <div class="st">战队奖励</div>
        <label class="setting-row"><span><b>夺冠战队奖励</b><small>战队榜第 1 全员发放</small></span><input v-model="cfg.teamReward" type="checkbox" class="toggle"/></label>
        <label v-if="cfg.teamReward" class="setting-row"><span><b>奖励卡型</b></span><select v-model="cfg.teamCard" class="inp team-select"><option v-for="sub in teamSubs" :key="sub" :value="sub">{{ optionName(sub) }}</option></select></label>
        <label class="setting-row"><span><b>本人需有碎片</b><small>碎片为 0 的成员跳过，结算记录标记为「本周期无碎片」</small></span><input v-model="cfg.reqShard" type="checkbox" class="toggle"/></label>
      </section>

      <section class="card"><div class="st">奖励叠加</div><label class="setting-row no-border"><span><b>同一用户战队奖 + 个人奖可同发</b></span><input v-model="cfg.stack" type="checkbox" class="toggle"/></label></section>

      <section class="card cap-card">
        <div class="st">结算发放上限 <em>D3 · 资金规则 · 仅老板可改</em></div>
        <label class="setting-row no-border"><span><b>单次自动结算发放卡券总张数上限</b><small>超过则整批置「被拦截」、一张不发，仅老板可强制发放。手动补发不受此上限约束</small></span><input :value="cfg.settleCap" class="inp cap-input" type="number" min="1" max="999" @change="setCap(($event.target as HTMLInputElement).value)"/></label>
        <div class="config-footnote cap-help">注意与上方「发放名次范围」是两个维度的约束：名次占位制下并列人数无上限，叠加战队奖全员发放，名次范围设 3 也可能发出 30 张——卡住张数才是真的卡住成本。<b>改动只影响后续结算</b>，不回溯已发放或已拦截的历史批次；当前若有被拦截批次，改高上限后仍需老板在「榜单与结算」页手动强制发放或撤销重跑。</div>
      </section>

      <button class="btn pri save-btn" :disabled="saving" @click="save">{{ saving?'保存中…':'保存规则' }}</button>
      <div class="note final-note"><b>口径说明：</b>碎片榜「历史」= 永久累计；积分榜「历史」= 当月累计（随清零归零）。<b>发奖以冻结快照为准</b>，结算后调队不影响已发放奖励；极端并列无上界，结算预览页会显示发放总量。</div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.settle-config-page{width:100%;min-width:0}.settle-config-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}.dimension-row,.range-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.dimension-row{justify-content:space-between}.chip-row{display:flex;gap:6px}.chip{font-family:inherit}.section-note{margin:9px 0 0}.range-row{margin-bottom:10px}.custom-label{margin-left:4px}.range-input{width:78px;margin:0;padding:4px 7px;font-size:12px}.prize-table th:nth-child(odd){width:14%}.prize-table th:nth-child(even){width:36%}.prize-select{margin:0;padding:5px 30px 5px 8px;font-size:12px}.config-footnote{margin-top:7px;color:var(--ink3);font-size:11px;line-height:1.7}.setting-row{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:11px 0;border-bottom:1px solid var(--line);cursor:pointer}.setting-row.no-border{border-bottom:0}.setting-row span{min-width:0}.setting-row b{display:block;font-size:13px;font-weight:500}.setting-row small{display:block;margin-top:2px;color:var(--ink2);font-size:11px;font-weight:400}.team-select{width:220px;margin:0}.toggle{width:36px;height:20px;accent-color:var(--ink);cursor:pointer}.cap-input{width:90px;margin:0;padding:5px 8px;text-align:right}.cap-help b{color:var(--ink2)}.save-btn{margin-bottom:11px}.save-btn:disabled{opacity:.55;cursor:not-allowed}.final-note{margin-bottom:0}.save-message{margin-bottom:12px;padding:9px 12px;border-radius:8px;background:var(--greenbg);color:var(--green);font-size:12px}.save-message.error{background:var(--redbg);color:var(--red)}@media(max-width:720px){.settle-config-hdr .hdr-note{margin-left:0;text-align:left;width:100%}.setting-row{align-items:flex-start}.team-select{width:min(220px,50%)}.prize-table{min-width:620px}}
</style>

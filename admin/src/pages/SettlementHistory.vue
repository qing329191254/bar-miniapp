<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import AppDateInput from "../components/AppDateInput.vue";
import { settleRewardText, settleStatusText } from "../settlementDisplay";

type Row = { id:number; week:string; type:string; target?:string; nick?:string; sh?:number; status:string; desc?:string };
type Week = { week:string; rows:Row[]; winners:number; team:number; personal:number; manual:number; granted:number; revoked:number; total:number };

const PRESETS:[string,string][] = [["today","今天"],["yday","昨天"],["7d","近 7 天"],["30d","近 30 天"],["month","本月"],["all","全部"],["custom","自定义"]];
const TYPES:Record<string,[string,string]> = {
  TEAM_CHAMPION:["战队冠军","purple"], PERSONAL_RANK1:["个人第 1 名","gold"],
  PERSONAL_RANK2:["个人第 2 名","blue"], PERSONAL_RANK3:["个人第 3 名","green"], MANUAL:["手动补发","pink"],
};
const router=useRouter();
const data=ref<{weeks:Week[];rows:Row[]}|null>(null), loading=ref(true), err=ref("");
const preset=ref("all"), dateFrom=ref(""), dateTo=ref(""), selectedWeek=ref("");
const day=(d:Date)=>new Date(d.getFullYear(),d.getMonth(),d.getDate());

function weekEnd(week:string){
  const m=(week.split("~")[1]||week).match(/^(\d{2})-(\d{2})$/); if(!m)return null;
  const now=new Date(); let year=now.getFullYear(); const month=Number(m[1]);
  if(month>now.getMonth()+2)year--; const d=new Date(year,month-1,Number(m[2])); return isNaN(+d)?null:d;
}
function bounds():[Date|null,Date|null]{
  if(preset.value==="all")return [null,null];
  if(preset.value==="custom")return [dateFrom.value?new Date(dateFrom.value+"T00:00:00"):null,dateTo.value?new Date(dateTo.value+"T23:59:59"):null];
  const today=day(new Date()), end=new Date(today); end.setHours(23,59,59,999);
  if(preset.value==="today")return [today,end];
  if(preset.value==="yday"){const from=new Date(today);from.setDate(from.getDate()-1);const to=new Date(from);to.setHours(23,59,59,999);return [from,to]}
  if(preset.value==="month")return [new Date(today.getFullYear(),today.getMonth(),1),end];
  const from=new Date(today);from.setDate(from.getDate()-(preset.value==="7d"?6:29));return [from,end];
}
const allWeeks=computed(()=>data.value?.weeks||[]);
const latestWeek=computed(()=>[...allWeeks.value].sort((a,b)=>b.week.localeCompare(a.week))[0]?.week||"");
const weeks=computed(()=>{const [from,to]=bounds();return allWeeks.value.filter(w=>{const d=weekEnd(w.week);return d?(!from||d>=from)&&(!to||d<=to):preset.value==="all"}).sort((a,b)=>b.week.localeCompare(a.week))});
const stats=computed(()=>weeks.value.reduce((s,w)=>({weeks:s.weeks+1,granted:s.granted+Number(w.granted||0),revoked:s.revoked+Number(w.revoked||0),total:s.total+Number(w.total??w.rows?.length??0)}),{weeks:0,granted:0,revoked:0,total:0}));
const selected=computed(()=>allWeeks.value.find(w=>w.week===selectedWeek.value)||null);
const details=computed(()=>[...(selected.value?.rows||[])].sort((a,b)=>Number(b.sh||0)-Number(a.sh||0)));
const rangeLabel=computed(()=>preset.value==="custom"?(dateFrom.value&&dateTo.value?`${dateFrom.value} 至 ${dateTo.value}`:"请选择起止日期"):(PRESETS.find(x=>x[0]===preset.value)?.[1]||"全部"));
const fmt=(n:number)=>Number(n||0).toLocaleString("en-US");
function setPreset(v:string){preset.value=v;if(v!=="custom"){dateFrom.value="";dateTo.value=""}selectedWeek.value=""}
function toggle(week:string){selectedWeek.value=selectedWeek.value===week?"":week}
function typeMeta(type:string):[string,string]{return TYPES[type]||[type||"其他奖励","grey"]}
function statusText(s:string){return settleStatusText(s)}
async function load(){loading.value=true;err.value="";try{data.value=await api("/admin/settlement/history?preset=all")}catch(e:any){err.value=e?.message||"加载失败";data.value=null}finally{loading.value=false}}
onMounted(load);
</script>

<template>
  <div class="rank-history-page">
    <div class="hdr rank-history-hdr"><span class="hdr-title">榜单历史记录</span><em class="hdr-note">全周期结算快照 · 共 {{ allWeeks.length }} 个已结算周次</em><button class="btn sm ghost hdr-back" @click="router.push('/settle')">当前周结算 ›</button></div>
    <AppAsyncPage :loading="loading" :data="data" :err="err" @retry="load">
      <div class="card flt-card">
        <div class="st">筛选 <em>当前范围：{{ rangeLabel }}</em></div>
        <div class="flt-chips"><span v-for="[key,label] in PRESETS" :key="key" class="chip" :class="{on:preset===key}" @click="setPreset(key)">{{ label }}</span></div>
        <div v-if="preset==='custom'" class="flt-custom"><span class="tiny">起</span><AppDateInput v-model="dateFrom" @change="selectedWeek=''"/><span class="tiny">止</span><AppDateInput v-model="dateTo" @change="selectedWeek=''"/><span v-if="!dateFrom||!dateTo" class="tiny flt-custom-hint">请选择起止日期</span></div>
      </div>
      <div class="rank-metrics">
        <div class="mtr"><div class="k">结算周次</div><div class="v">{{ stats.weeks }}</div><div class="tiny">{{ rangeLabel }}</div></div>
        <div class="mtr"><div class="k">已发放奖励</div><div class="v">{{ fmt(stats.granted) }}</div><div class="tiny">张宝箱卡</div></div>
        <div class="mtr"><div class="k">已撤销</div><div class="v" :class="{red:stats.revoked}">{{ fmt(stats.revoked) }}</div><div class="tiny">异常人工撤销</div></div>
        <div class="mtr"><div class="k">发放总量</div><div class="v">{{ fmt(stats.total) }}</div><div class="tiny">含撤销在内</div></div>
      </div>
      <div class="card rank-table-card"><div class="tb-wrap"><table class="tb2 rank-table" data-cols="lccccccc">
        <thead><tr><th>周次</th><th>获奖人数</th><th>战队奖</th><th>个人奖</th><th>手动补发</th><th>已发放</th><th>已撤销</th><th class="col-op">操作</th></tr></thead>
        <tbody><tr v-for="w in weeks" :key="w.week" :class="{selected:selectedWeek===w.week}"><td><b>{{ w.week }}</b><div class="tiny">{{ w.week===latestWeek?'最近结算':'历史周次' }}</div></td><td>{{ w.winners }} 人</td><td>{{ w.team }}</td><td>{{ w.personal }}</td><td>{{ w.manual||'—' }}</td><td><b class="green">{{ w.granted }}</b></td><td><b v-if="w.revoked" class="red">{{ w.revoked }}</b><span v-else class="mut">0</span></td><td class="col-op"><button class="btn sm ghost" @click="toggle(w.week)">{{ selectedWeek===w.week?'收起明细':'查看明细' }}</button></td></tr><tr v-if="!weeks.length"><td colspan="8" class="table-empty">所选时间范围内无结算记录</td></tr></tbody>
      </table></div></div>
      <div v-if="selected" class="card detail-card">
        <div class="st">{{ selected.week }} 发放明细 <em>{{ selected.rows.length }} 条</em><button class="detail-close" @click="selectedWeek=''">收起</button></div>
        <div class="tb-wrap"><table class="tb2 detail-table" data-cols="lllccl"><thead><tr><th>获奖人</th><th>奖励类型</th><th>奖励内容</th><th>依据对象</th><th>快照碎片</th><th>状态</th></tr></thead><tbody>
          <tr v-for="r in details" :key="r.id" :class="{revoked:r.status==='REVOKED'}"><td><b>{{ r.nick||'—' }}</b></td><td><span class="pill type-pill" :class="typeMeta(r.type)[1]">{{ typeMeta(r.type)[0] }}</span></td><td>{{ settleRewardText(r) }}</td><td class="mut">{{ r.target||'—' }}</td><td>{{ r.sh?fmt(r.sh):'—' }}</td><td><span class="pill status-pill" :class="r.status.toLowerCase()">{{ statusText(r.status) }}</span></td></tr><tr v-if="!details.length"><td colspan="6" class="table-empty">该周期暂无发放明细</td></tr>
        </tbody></table></div>
        <div class="detail-footnote">「快照碎片」为结算时刻该获奖人/战队的当周碎片值，后续对局不会改写此数字——这是发奖的依据凭证。</div>
      </div>
      <div class="note"><b>快照原则：</b>发奖依据结算当时的规则快照，后续修改「榜单与奖励规则」<b>不影响已结算周次</b>，故历史周次的奖励构成可能与当前规则不同，这是预期行为而非数据错误。撤销记录会同时作废对应未核销卡券，已核销的不追回。</div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.rank-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:12px}.rank-metrics .tiny{margin-top:2px}.rank-table-card{padding:0;overflow:hidden}.rank-table{min-width:820px}.rank-table th,.rank-table td{text-align:center}.rank-table th:first-child,.rank-table td:first-child{text-align:left}.rank-table tbody tr.selected td{background:var(--goldbg)}.rank-table td b,.detail-table td b{font-weight:500}.green{color:var(--green)}.red{color:var(--red)!important}.detail-card{animation:detail-in .2s ease}.detail-close{margin-left:auto;border:0;background:transparent;color:var(--blue);font-size:11px;cursor:pointer}.detail-table{min-width:760px}.detail-table tr.revoked{opacity:.55}.detail-footnote{margin-top:7px;color:var(--ink3);font-size:11px}.type-pill.purple{color:#534AB7;background:#EEEDFE}.type-pill.gold{color:#BA7517;background:#FAEEDA}.type-pill.blue{color:#185FA5;background:#E6F1FB}.type-pill.green{color:#3B6D11;background:#EAF3DE}.type-pill.pink{color:#993556;background:#FBEAF0}.type-pill.grey{color:#6B6A65;background:#F1EFE9}.status-pill.granted{color:#3B6D11;background:#EAF3DE}.status-pill.revoked{color:#A32D2D;background:#FCEBEB}.status-pill.skipped{color:#6B6A65;background:#F1EFE9}@keyframes detail-in{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}@media(max-width:900px){.rank-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.rank-history-hdr .hdr-note{position:static;transform:none;white-space:normal}}
</style>

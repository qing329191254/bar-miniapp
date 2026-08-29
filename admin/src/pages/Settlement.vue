<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, savedUser } from "../api";
const data=ref<any>({rows:[]}), msg=ref(""); const boss=savedUser()?.role==="BOSS";
const labels:any={TEAM_CHAMPION:"战队夺冠",PERSONAL_RANK1:"个人第 1",PERSONAL_RANK2:"个人第 2",PERSONAL_RANK3:"个人第 3",MANUAL:"手动补发"};
async function load(){data.value=await api('/admin/settlement/current')}
async function revoke(r:any){if(!confirm(`确认撤销 ${r.nick} 的奖励？`))return;try{await api(`/admin/settlement/${r.id}/revoke`,{method:'POST'});await load();msg.value='奖励已撤销'}catch(e:any){msg.value=e.message}}
onMounted(load);
</script>
<template><div><div class="hdr">榜单与结算 <em>{{ data.week || '暂无结算周期' }} · 名次占位制，可叠加</em></div><div v-if="msg" class="notice">{{msg}}</div><section class="card"><div class="settle-head"><span class="pill on">已执行</span><span class="tiny">结算快照冻结，发放奖励以本周期记录为准</span><button class="btn ghost mini" @click="load">刷新</button></div><table class="tb2"><thead><tr><th>获奖对象</th><th>类型</th><th>奖励</th><th>碎片校验</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="r in data.rows" :key="r.id"><td><b>{{r.target}}</b><div class="tiny">{{r.nick}}</div></td><td><span class="pill">{{labels[r.type]||r.type}}</span></td><td>{{r.desc}}</td><td :class="r.sh?'':'red'">{{r.sh}}</td><td><span class="pill" :class="r.status==='GRANTED'?'on':''">{{r.status==='GRANTED'?'已发放':r.status==='REVOKED'?'已撤销':'未通过'}}</span></td><td><button v-if="boss&&r.status==='GRANTED'" class="btn ghost mini" @click="revoke(r)">撤销</button><span v-else class="tiny">—</span></td></tr></tbody></table></section><div class="note">名次占位：并列第 3 名均可获得第 3 名奖励。撤销会同步作废尚未核销的对应卡券，已核销的不追回。</div></div></template>
<style scoped>.settle-head{display:flex;gap:10px;align-items:center;margin-bottom:12px}.settle-head .btn{margin-left:auto}.mini{padding:5px 10px;font-size:12px}.notice{color:var(--green);font-size:12px;margin-bottom:8px}.pill.on{color:#3B6D11;background:var(--greenbg)}.red{color:#B52B2B}</style>

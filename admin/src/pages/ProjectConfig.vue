<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import AppAsyncPage from "../components/AppAsyncPage.vue";
import { showToast } from "../composables/useToast";

type Project = { id?:number; name:string; min:number; max:number; shard:number; recent:number; sort:number; disabled:boolean };
const blank=():Project=>({name:"",min:0,max:0,shard:50,recent:0,sort:99,disabled:false});
const projects=ref<Project[]|null>(null), draft=ref<Project>(blank()), selectedId=ref<number|null>(null), isNew=ref(false);
const loading=ref(true), err=ref(""), saving=ref(false);
const sorted=computed(()=>[...(projects.value||[])].sort((a,b)=>Number(a.sort||99)-Number(b.sort||99)||Number(a.id||0)-Number(b.id||0)));

function edit(project:Project){selectedId.value=project.id||null;isNew.value=false;draft.value={...project}}
function create(){selectedId.value=null;isNew.value=true;draft.value=blank()}
function normalize(){draft.value.name=String(draft.value.name||"").trim();draft.value.min=Math.max(0,Math.floor(Number(draft.value.min)||0));draft.value.max=Math.max(0,Math.floor(Number(draft.value.max)||0));draft.value.shard=Math.max(0,Math.floor(Number(draft.value.shard)||0));if(draft.value.max&&draft.value.max<draft.value.min)draft.value.max=draft.value.min}
async function load(){loading.value=true;err.value="";try{const res=await api<any>("/admin/projects?pageSize=0");projects.value=Array.isArray(res)?res:(res.items||[]);const current=projects.value.find(x=>x.id===selectedId.value)||sorted.value[0];if(current)edit(current);else create()}catch(e:any){err.value=e?.message||"加载失败";projects.value=null}finally{loading.value=false}}
async function save(){normalize();if(!draft.value.name){showToast("请填写项目名称",true);return}saving.value=true;try{const path=isNew.value?"/admin/projects":`/admin/projects/${selectedId.value}`;const saved=await api<Project>(path,{method:isNew.value?"POST":"PUT",body:{data:draft.value}});selectedId.value=saved.id||selectedId.value;isNew.value=false;await load();showToast(`${draft.value.name}已保存，移动端快捷值同步更新`)}catch(e:any){showToast(e?.message||"保存失败",true)}finally{saving.value=false}}
onMounted(load);
</script>

<template>
  <div class="project-page">
    <div class="hdr project-config-hdr"><span class="hdr-title">对局项目配置</span><em class="hdr-note">默认碎片值联动移动端快捷值</em></div>
    <AppAsyncPage :loading="loading" :data="projects" :err="err" @retry="load">
      <div class="project-layout">
        <section class="card project-list-card">
          <div class="list-head"><b>项目列表</b><button class="btn sm pri" @click="create">＋ 新增项目</button></div>
          <div class="tb-wrap"><table class="tb2 project-table" data-cols="lccccc"><thead><tr><th>项目</th><th>常规人数</th><th>默认碎片值</th><th>近 30 天</th><th>状态</th><th class="col-op">操作</th></tr></thead><tbody>
            <tr v-for="project in sorted" :key="project.id" :class="{disabled:project.disabled,selected:selectedId===project.id&&!isNew}"><td><b>{{ project.name }}</b></td><td class="mut">{{ project.min }}-{{ project.max }} 人</td><td><b class="shard">{{ project.shard }}</b></td><td class="mut">{{ project.recent }} 局</td><td><span class="pill" :class="project.disabled?'off':'on'">{{ project.disabled?'已停用':'启用' }}</span></td><td class="col-op"><button class="btn sm ghost" @click="edit(project)">编辑</button></td></tr>
            <tr v-if="!sorted.length"><td colspan="6" class="table-empty">暂无对局项目，请新增</td></tr>
          </tbody></table></div>
        </section>

        <section class="card project-editor">
          <div class="st">{{ isNew?'新增项目':`编辑 · ${draft.name||'项目'}` }}</div>
          <label class="field"><span class="fld">项目名称 *</span><input v-model="draft.name" class="inp" maxlength="64" placeholder="请输入项目名称"/></label>
          <div class="people-grid"><label class="field"><span class="fld">人数下限</span><input v-model.number="draft.min" class="inp" type="number" min="0"/></label><label class="field"><span class="fld">上限</span><input v-model.number="draft.max" class="inp" type="number" min="0"/></label></div>
          <label class="field shard-field"><span class="fld">默认碎片值 * <b>向导 Step 3 依赖此值</b></span><input v-model.number="draft.shard" class="inp shard-input" type="number" min="0"/></label>
          <button class="btn pri editor-save" :disabled="saving" @click="save">{{ saving?'保存中…':isNew?'创建项目':'保存' }}</button>
        </section>
      </div>
      <div class="note"><b>快捷值不写死：</b>狼人杀一局 2 小时给 120、台球 20 分钟给 50，差异只有商家知道。改这里，移动端「一键铺满」的快捷值立即变化。<b>停用而非删除</b>，历史记录仍能查。</div>
    </AppAsyncPage>
  </div>
</template>

<style scoped>
.project-config-hdr .hdr-note{position:static;transform:none;margin-left:auto;text-align:right;pointer-events:auto;white-space:normal}.project-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:12px;align-items:start}.project-list-card{padding:14px}.list-head{display:flex;align-items:center;margin-bottom:11px}.list-head b{font-size:14px}.list-head .btn{margin-left:auto}.project-table{min-width:650px}.project-table td b{font-weight:500}.project-table tr.disabled{opacity:.5}.project-table tr.selected td{background:var(--goldbg)}.shard{color:#534AB7}.pill.on{color:var(--green);background:var(--greenbg)}.pill.off{color:var(--ink3);background:var(--bg)}.project-editor{position:sticky;top:0}.field{display:block;margin-bottom:8px}.fld{display:block;margin-bottom:4px;color:var(--ink2);font-size:11px}.fld b{color:#534AB7;font-weight:500}.people-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.shard-input{border-color:#534AB7;color:#534AB7}.editor-save{width:100%}.editor-save:disabled{opacity:.55;cursor:not-allowed}@media(max-width:900px){.project-layout{grid-template-columns:1fr}.project-editor{position:static}.project-config-hdr .hdr-note{margin-left:0;text-align:left;width:100%}}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{ (e: "update:modelValue", value: string): void; (e: "change", value: string): void }>();

const root = ref<HTMLElement | null>(null);
const hourWheel = ref<HTMLElement | null>(null);
const minuteWheel = ref<HTMLElement | null>(null);
const open = ref(false);
const draft = ref(new Date());
const viewYear = ref(new Date().getFullYear());
const viewMonth = ref(new Date().getMonth());
const hour = ref(0);
const minute = ref(0);
const pad = (n: number) => String(n).padStart(2, "0");

function parse(value: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value || "");
  if (!m) return new Date();
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]));
  return Number.isNaN(d.getTime()) ? new Date() : d;
}
function valueOf(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function syncDraft(value = props.modelValue) {
  const d = parse(value);
  draft.value = new Date(d);
  viewYear.value = d.getFullYear();
  viewMonth.value = d.getMonth();
  hour.value = d.getHours();
  minute.value = d.getMinutes();
}
function show() {
  syncDraft();
  open.value = true;
  nextTick(() => {
    root.value?.querySelector<HTMLElement>(".dt-popover")?.focus();
    centerTimeWheels();
  });
}
function close() {
  open.value = false;
}
function confirm() {
  const d = new Date(draft.value);
  d.setHours(hour.value, minute.value, 0, 0);
  const value = valueOf(d);
  emit("update:modelValue", value);
  emit("change", value);
  close();
}
function chooseToday() {
  const now = new Date();
  draft.value = now;
  viewYear.value = now.getFullYear();
  viewMonth.value = now.getMonth();
  hour.value = now.getHours();
  minute.value = now.getMinutes();
  nextTick(centerTimeWheels);
}
function centerWheel(el: HTMLElement | null, value: number) {
  if (!el) return;
  const itemHeight = 32;
  el.scrollTop = Math.max(0, value * itemHeight - (el.clientHeight - itemHeight) / 2);
}
function centerTimeWheels() {
  centerWheel(hourWheel.value, hour.value);
  centerWheel(minuteWheel.value, minute.value);
}
function moveMonth(delta: number) {
  const d = new Date(viewYear.value, viewMonth.value + delta, 1);
  viewYear.value = d.getFullYear();
  viewMonth.value = d.getMonth();
}
function chooseDate(date: Date) {
  const d = new Date(date);
  d.setHours(hour.value, minute.value, 0, 0);
  draft.value = d;
  if (date.getMonth() !== viewMonth.value || date.getFullYear() !== viewYear.value) {
    viewYear.value = date.getFullYear();
    viewMonth.value = date.getMonth();
  }
}
function outside(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) close();
}

const display = computed(() => {
  const d = parse(props.modelValue);
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
});
const days = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value, 1);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(viewYear.value, viewMonth.value, 1 - mondayOffset);
  const today = new Date();
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    return {
      date,
      label: date.getDate(),
      outside: date.getMonth() !== viewMonth.value,
      selected: sameDay(date, draft.value),
      today: sameDay(date, today),
    };
  });
});
const hours = Array.from({ length: 24 }, (_, i) => i);
const minutes = Array.from({ length: 60 }, (_, i) => i);

watch(() => props.modelValue, (value) => { if (!open.value) syncDraft(value); });
onMounted(() => document.addEventListener("pointerdown", outside));
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside));
</script>

<template>
  <div ref="root" class="dt-picker">
    <button type="button" class="dt-trigger" aria-haspopup="dialog" :aria-expanded="open" @click="show">
      <span>{{ display }}</span>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v3M17 2v3M3.5 9h17M5.5 4h13a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M8 13h2M14 13h2M8 17h2M14 17h2"/></svg>
    </button>

    <div v-if="open" class="dt-popover" role="dialog" aria-label="选择对局日期和时间" tabindex="-1" @keydown.esc.prevent="close">
      <div class="dt-calendar">
        <div class="dt-head">
          <button type="button" aria-label="上个月" @click="moveMonth(-1)">‹</button>
          <b>{{ viewYear }} 年 {{ viewMonth + 1 }} 月</b>
          <button type="button" aria-label="下个月" @click="moveMonth(1)">›</button>
        </div>
        <div class="dt-week"><span v-for="w in ['一','二','三','四','五','六','日']" :key="w">{{ w }}</span></div>
        <div class="dt-days">
          <button
            v-for="item in days"
            :key="item.date.toISOString()"
            type="button"
            :class="{ outside: item.outside, selected: item.selected, today: item.today }"
            @click="chooseDate(item.date)"
          >{{ item.label }}</button>
        </div>
      </div>

      <div class="dt-time">
        <div class="dt-time-title">对局时间</div>
        <div class="dt-time-fields">
          <div class="dt-wheel-group"><span>时</span><div ref="hourWheel" class="dt-wheel" role="listbox" aria-label="小时"><button v-for="h in hours" :key="h" type="button" :class="{ selected: hour === h }" @click="hour = h">{{ pad(h) }}</button></div></div>
          <b>:</b>
          <div class="dt-wheel-group"><span>分</span><div ref="minuteWheel" class="dt-wheel" role="listbox" aria-label="分钟"><button v-for="m in minutes" :key="m" type="button" :class="{ selected: minute === m }" @click="minute = m">{{ pad(m) }}</button></div></div>
        </div>
        <div class="dt-preview">{{ pad(hour) }}:{{ pad(minute) }}</div>
        <button type="button" class="dt-today" @click="chooseToday">使用当前时间</button>
      </div>

      <div class="dt-actions">
        <button type="button" class="dt-cancel" @click="close">取消</button>
        <button type="button" class="dt-confirm" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dt-picker{position:relative;width:100%;user-select:none;-webkit-user-select:none}
.dt-trigger{display:flex;align-items:center;justify-content:space-between;width:100%;min-height:38px;padding:8px 11px;border:1px solid rgba(28,27,25,.4);border-radius:8px;background:#F0EDE5;color:var(--ink);font:inherit;text-align:left;cursor:pointer;box-shadow:inset 0 0 0 1px rgba(255,255,255,.65);transition:.16s ease}
.dt-trigger:hover{border-color:var(--gold);background:#FAEEDA}
.dt-trigger:focus-visible,.dt-trigger[aria-expanded="true"]{outline:none;border-color:var(--gold);background:#FFF9EE;box-shadow:0 0 0 3px rgba(186,117,23,.2)}
.dt-trigger svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;flex:none}
.dt-popover{position:absolute;z-index:50;top:calc(100% + 8px);right:0;width:min(460px,calc(100vw - 48px));display:grid;grid-template-columns:minmax(0,1fr) 142px;background:#FFFDF8;border:1px solid rgba(28,27,25,.32);border-radius:14px;box-shadow:0 20px 48px rgba(28,27,25,.24),0 3px 10px rgba(28,27,25,.12);overflow:hidden;outline:none}
.dt-calendar{padding:15px 16px 12px;background:#FFFDF8}
.dt-head{display:grid;grid-template-columns:32px 1fr 32px;align-items:center;margin-bottom:11px}
.dt-head b{text-align:center;font-size:14px}
.dt-head button{width:30px;height:30px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font-size:23px;line-height:1;cursor:pointer}
.dt-head button:hover{border-color:var(--gold);background:var(--goldbg)}
.dt-week,.dt-days{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
.dt-week{margin-bottom:5px;color:var(--ink3);font-size:11px;text-align:center}
.dt-days button{aspect-ratio:1;border:1px solid transparent;border-radius:8px;background:transparent;color:var(--ink);font:inherit;font-size:12px;cursor:pointer}
.dt-days button:hover{border-color:rgba(186,117,23,.45);background:var(--goldbg)}
.dt-days button.outside{color:#B8B5AD}
.dt-days button.today{border-color:var(--gold);color:var(--gold);font-weight:600}
.dt-days button.selected{border-color:#8C5510;background:var(--gold);color:#fff;box-shadow:0 2px 6px rgba(186,117,23,.3);font-weight:700}
.dt-time{display:flex;flex-direction:column;align-items:center;padding:18px 12px;background:#F3F0E8;border-left:1px solid var(--line)}
.dt-time-title{align-self:stretch;color:var(--ink2);font-size:11px;text-align:center}
.dt-time-fields{display:flex;align-items:center;gap:6px;margin-top:10px}
.dt-wheel-group>span{display:block;margin-bottom:4px;color:var(--ink3);font-size:10px;text-align:center}
.dt-wheel{width:48px;height:142px;padding:4px;border:1px solid rgba(28,27,25,.18);border-radius:9px;background:#fff;overflow-y:auto;scrollbar-width:none;-ms-overflow-style:none;scroll-behavior:smooth}
.dt-wheel::-webkit-scrollbar{display:none;width:0;height:0}
.dt-wheel button{display:block;width:100%;height:32px;border:0;border-radius:6px;background:transparent;color:var(--ink2);font:inherit;font-size:12px;cursor:pointer}
.dt-wheel button:hover{background:var(--goldbg);color:var(--ink)}
.dt-wheel button.selected{background:var(--gold);color:#fff;font-weight:700;box-shadow:0 1px 4px rgba(186,117,23,.28)}
.dt-time-fields>b{padding-top:15px;color:var(--ink3)}
.dt-preview{margin-top:10px;color:var(--ink);font-size:22px;font-weight:600;letter-spacing:1px}
.dt-today{margin-top:auto;border:0;background:transparent;color:var(--gold);font-size:11px;cursor:pointer}
.dt-actions{grid-column:1/-1;display:flex;justify-content:flex-end;gap:8px;padding:10px 12px;border-top:1px solid var(--line);background:#FAF8F2}
.dt-actions button{min-width:76px;padding:7px 13px;border-radius:8px;font:inherit;cursor:pointer}
.dt-cancel{border:1px solid var(--line);background:#fff;color:var(--ink2)}
.dt-confirm{border:1px solid #8C5510;background:var(--gold);color:#fff;font-weight:600}
@media(max-width:620px){.dt-popover{left:0;right:auto;grid-template-columns:1fr}.dt-time{border-left:0;border-top:1px solid var(--line)}.dt-time-fields{margin-top:8px}.dt-preview{margin-top:8px}.dt-today{margin-top:10px}}
</style>

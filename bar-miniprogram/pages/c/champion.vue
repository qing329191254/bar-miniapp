<script setup>
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api } from "@/utils/api";

const data = ref({ list: [], total: 0, month: 0 });
const records = computed(() => [...(data.value.list || [])].sort((a, b) => String(b.date).localeCompare(String(a.date))));
onShow(async () => { data.value = await api("/champions"); });
</script>

<template>
  <view class="champ-page">
    <view class="champ-summary">
      <view class="summary-cell"><text class="summary-num number-display">{{ data.total }}</text><text>累计夺冠</text></view>
      <view class="summary-divider"></view>
      <view class="summary-cell"><text class="summary-num number-display">{{ data.month }}</text><text>本月夺冠</text></view>
    </view>
    <view class="section-head"><text>夺冠记录</text><text class="section-sub">店员录入</text></view>
    <view class="record-card">
      <view v-if="!records.length" class="empty">暂无冠军记录，参与对局后由店员录入</view>
      <view v-for="(item, index) in records" :key="item.date + '-' + index" class="record-row">
        <view class="crown">冠</view>
        <view class="record-copy">
          <view class="record-title">{{ item.event || "冠军赛事" }}</view>
          <view class="record-meta">{{ item.date }}<text v-if="item.n"> · 参赛 {{ item.n }} 人</text></view>
          <view class="record-note">获奖时战队：{{ item.teamName || "无战队" }} · 录入店员：{{ item.op || "—" }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<style scoped>
.champ-page{min-height:100vh;box-sizing:border-box;padding:14px 15px 40px;background:#f5f4f0}.champ-summary{display:flex;align-items:center;height:88px;padding:0 18px;margin-bottom:14px;border:1.5px solid #ba7517;border-radius:15px;background:#faeeda;color:#ba7517}.summary-cell{flex:1;display:flex;flex-direction:column;align-items:center;font-size:12px}.summary-num{color:#633806;font-size:30px;line-height:1.25}.summary-divider{width:1px;height:37px;background:rgba(186,117,23,.3)}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:15px;font-weight:700}.section-sub{color:#9c9a93;font-size:12px;font-weight:400}.record-card{padding:0 14px;border:1px solid rgba(28,27,25,.12);border-radius:14px;background:#fff;box-shadow:0 2px 5px rgba(28,27,25,.05)}.record-row{display:flex;gap:10px;align-items:center;padding:14px 0;border-bottom:1px solid rgba(28,27,25,.12)}.record-row:last-child{border-bottom:none}.crown{width:34px;height:34px;flex:none;display:flex;align-items:center;justify-content:center;border-radius:9px;background:#fac775;color:#633806;font-size:12px}.record-copy{min-width:0}.record-title{font-size:14px;color:#1c1b19}.record-meta{margin-top:3px;color:#6b6a65;font-size:12px}.record-note{margin-top:3px;color:#9c9a93;font-size:11px}.empty{padding:36px 4px;color:#9c9a93;font-size:12px;text-align:center}
</style>

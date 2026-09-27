<script setup>
import { computed, ref, watch } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { api, go, hideWxHomeButton, toastText } from "@/utils/api";

const search = ref("");
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);
const loadingMore = ref(false);
const todayOnly = ref(true);

const hasMore = computed(() => rows.value.length < total.value);
const listTitle = computed(() => (search.value.trim() ? "搜索结果" : "今日到店会员"));

let searchTimer = null;

async function load(reset = false) {
  if (reset) {
    page.value = 1;
    loading.value = true;
  } else {
    loadingMore.value = true;
  }
  try {
    const q = search.value.trim();
    const qs = [
      `page=${page.value}`,
      `pageSize=${pageSize}`,
      `today=${q ? 0 : 1}`,
      q ? `q=${encodeURIComponent(q)}` : "",
    ]
      .filter(Boolean)
      .join("&");
    const data = await api(`/staff/members/adjust?${qs}`, { loading: false, silent: true });
    const next = data?.rows || [];
    rows.value = reset ? next : rows.value.concat(next);
    total.value = Number(data?.total || 0);
    todayOnly.value = !!data?.todayOnly;
    // 空列表时自动灌入测试会员，方便看 UI
    if (reset && !q && !rows.value.length) {
      await seedDemo(true);
    }
  } catch (e) {
    if (reset) {
      rows.value = [];
      total.value = 0;
    }
    toastText(e?.message || "加载失败");
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function onSearchInput(e) {
  search.value = e.detail?.value ?? "";
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => load(true), 280);
}

function loadMore() {
  if (!hasMore.value || loading.value || loadingMore.value) return;
  page.value += 1;
  load(false);
}

function openMember(m) {
  go(`/pages/s/member-adjust-form?uid=${m.id}`);
}

async function seedDemo(silent = false) {
  loading.value = true;
  try {
    const data = await api("/staff/members/adjust/demo-today", { method: "POST", loading: false, silent: true });
    rows.value = data?.rows || [];
    total.value = Number(data?.total || 0);
    page.value = 1;
    todayOnly.value = true;
    if (!silent) toastText(`已加载 ${data?.seeded || rows.value.length} 位测试会员`);
  } catch (e) {
    if (!silent) toastText(e?.message || "加载失败");
  } finally {
    loading.value = false;
  }
}

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

onShow(() => {
  hideWxHomeButton();
  load(true);
});

watch(search, () => {});
</script>

<template>
  <view class="page">
    <view class="sticky">
      <view class="search-wrap">
        <input
          class="search"
          :value="search"
          placeholder="搜索手机尾号 4 位 / 会员名 / 会员号..."
          confirm-type="search"
          @input="onSearchInput"
        />
      </view>
      <view class="note">
        店员可直接增减顾客的碎片、积分、卡券；提交立即生效，须填原因并留痕。金币不在本页调整，仍走 Web 端申请由老板审批。
      </view>
    </view>

    <view class="list-head">
      <text class="list-title">{{ listTitle }}</text>
      <text class="list-meta">{{ search.trim() ? `${total} 人` : `今日 ${total} 人 · 点选即进入调整` }}</text>
    </view>

    <scroll-view
      scroll-y
      class="list-scroll"
      :show-scrollbar="false"
      @scrolltolower="loadMore"
      lower-threshold="80"
    >
      <view v-if="loading && !rows.length" class="empty">加载中…</view>
      <view v-else-if="!rows.length" class="empty">
        <view>{{ search.trim() ? "没有匹配的会员" : "今日暂无打开过小程序的会员" }}</view>
        <button v-if="!search.trim()" class="btn ghost demo-btn" @tap="seedDemo">加载测试会员</button>
      </view>
      <view
        v-for="m in rows"
        :key="m.id"
        class="card member"
        @tap="openMember(m)"
      >
        <view class="av">{{ (m.av || m.nick || "?").slice(0, 2) }}</view>
        <view class="mid">
          <view class="name-row">
            <text class="nick">{{ m.nick }}</text>
            <text class="tail">{{ m.tail || "—" }}</text>
          </view>
          <view class="tiny">{{ m.no }} · {{ m.teamName || "无战队" }}</view>
        </view>
        <view class="right">
          <view class="nums">
            <text>碎片 {{ fmt(m.shard?.w) }}</text>
            <text>积分 {{ fmt(m.point?.av) }}</text>
          </view>
          <view class="tiny">卡包 {{ fmt(m.unusedCards) }} 张</view>
        </view>
      </view>
      <view v-if="hasMore" class="more" @tap="loadMore">
        {{ loadingMore ? "加载中…" : "加载更多" }}
      </view>
      <view v-else-if="rows.length" class="more muted">没有更多了</view>
      <view class="safe" />
    </scroll-view>
  </view>
</template>

<style scoped>
.page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f4f0;
  box-sizing: border-box;
}
.sticky {
  flex: none;
  padding: 12px 14px 0;
  background: #f5f4f0;
  z-index: 2;
}
.search-wrap {
  background: #fff;
  border: 1px solid rgba(28, 27, 25, 0.1);
  border-radius: 12px;
  padding: 0 12px;
}
.search {
  height: 40px;
  font-size: 14px;
}
.note {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #e6f1fb;
  color: #185fa5;
  font-size: 12px;
  line-height: 1.65;
}
.list-head {
  flex: none;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 14px 14px 8px;
}
.list-title {
  font-size: 14px;
  font-weight: 600;
}
.list-meta {
  font-size: 11px;
  color: #9c9a93;
}
.list-scroll {
  flex: 1;
  min-height: 0;
  padding: 0 14px;
  box-sizing: border-box;
}
.member {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  margin-bottom: 8px;
}
.av {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1c1b19;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex: none;
}
.mid {
  flex: 1;
  min-width: 0;
}
.name-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.nick {
  font-weight: 600;
  font-size: 14px;
}
.tail {
  font-size: 12px;
  color: #9c9a93;
}
.right {
  text-align: right;
  flex: none;
}
.nums {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
  color: #534ab7;
}
.empty,
.more {
  text-align: center;
  padding: 24px 8px;
  color: #9c9a93;
  font-size: 12px;
}
.demo-btn {
  margin-top: 14px;
  display: inline-block;
  padding: 8px 14px;
  font-size: 13px;
}
.more.muted {
  opacity: 0.7;
}
.safe {
  height: calc(24px + env(safe-area-inset-bottom));
}
</style>

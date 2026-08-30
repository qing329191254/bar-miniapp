const REWARD_DESC: Record<string, string> = {
  NO_SHARD: "本周期无碎片",
};

const SKIP_OP: Record<string, string> = {
  NO_SHARD: "无碎片跳过",
  本周期无碎片: "无碎片跳过",
  规则不允许叠加: "不可叠加",
};

export function settleStatusText(status: string) {
  return (
    { GRANTED: "已发放", REVOKED: "已撤销", SKIPPED: "未通过", BLOCKED: "被拦截" }[status] ||
    status ||
    "—"
  );
}

/** 奖励列：跳过条目展示中文原因，正常条目展示卡券名称 */
export function settleRewardText(row: { status?: string; desc?: string }) {
  const desc = String(row.desc || "").trim();
  if (REWARD_DESC[desc]) return REWARD_DESC[desc];
  if (row.status === "SKIPPED" && !desc) return "未通过校验";
  return desc || "—";
}

/** 操作列：跳过条目说明不可撤销的原因 */
export function settleSkipOpText(row: { status?: string; desc?: string }) {
  if (row.status !== "SKIPPED") return "";
  const desc = String(row.desc || "").trim();
  return SKIP_OP[desc] || "—";
}

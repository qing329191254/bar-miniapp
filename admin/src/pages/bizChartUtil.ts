export type BizMetric = "biz" | "recharge" | "orders" | "guests";
export type ChartMode = "single" | "bar" | "line" | "line-sparse";

export type BizRow = {
  d: string;
  coin: number;
  offline: number;
  recharge: number;
  orders: number;
  guests: number;
};

const MODE_HINT: Record<ChartMode, string> = {
  single: "单日构成",
  bar: "逐日对比",
  line: "趋势折线",
  "line-sparse": "长期趋势",
};

export function chartMode(n: number): ChartMode {
  if (n <= 1) return "single";
  if (n <= 8) return "bar";
  if (n <= 31) return "line";
  return "line-sparse";
}

export function pickChartRows(rows: BizRow[]): BizRow[] {
  const list = [...rows].reverse();
  if (list.length <= 31) return list;
  return list.slice(-60);
}

export function chartModeHint(n: number) {
  return MODE_HINT[chartMode(n)];
}

export type BizMetric = "biz" | "recharge" | "orders" | "guests";
export type ChartMode = "single" | "bar" | "line" | "line-sparse";
export type BizGranularity = "day" | "week";

export type BizRow = {
  d: string;
  dEnd?: string;
  coin: number;
  offline: number;
  recharge: number;
  orders: number;
  guests: number;
};

export type ChartSlice = {
  rows: BizRow[];
  granularity: BizGranularity;
  hint: string;
  totalDays: number;
};

const MODE_HINT: Record<ChartMode, string> = {
  single: "单日构成",
  bar: "逐日对比",
  line: "趋势折线",
  "line-sparse": "长期趋势",
};

function fmtIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function weekStart(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return fmtIso(d);
}

function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return fmtIso(d);
}

function aggregateWeekly(rows: BizRow[]): BizRow[] {
  const map = new Map<string, BizRow>();
  for (const r of rows) {
    const ws = weekStart(r.d);
    const we = addDays(ws, 6);
    const cur = map.get(ws) || { d: ws, dEnd: we, coin: 0, offline: 0, recharge: 0, orders: 0, guests: 0 };
    cur.coin += r.coin || 0;
    cur.offline += r.offline || 0;
    cur.recharge += r.recharge || 0;
    cur.orders += r.orders || 0;
    cur.guests += r.guests || 0;
    map.set(ws, cur);
  }
  return [...map.values()].sort((a, b) => a.d.localeCompare(b.d));
}

export function chartMode(n: number, granularity: BizGranularity = "day"): ChartMode {
  if (granularity === "week") return "line-sparse";
  if (n <= 1) return "single";
  if (n <= 8) return "bar";
  if (n <= 31) return "line";
  return "line-sparse";
}

export function chartModeHint(n: number, granularity: BizGranularity = "day"): string {
  if (granularity === "week") return "按周汇总";
  return MODE_HINT[chartMode(n, granularity)];
}

/** Build chart data: cap at today, daily or weekly by range length. */
export function buildChartSlice(rows: BizRow[], today: string): ChartSlice {
  const daily = rows
    .filter((r) => !today || r.d <= today)
    .slice()
    .reverse();
  const totalDays = daily.length;
  if (!totalDays) return { rows: [], granularity: "day", hint: "", totalDays: 0 };

  if (totalDays <= 31) {
    return { rows: daily, granularity: "day", hint: chartModeHint(totalDays), totalDays };
  }
  if (totalDays <= 90) {
    const sliced = daily.slice(-60);
    const hint = totalDays > 60 ? `${chartModeHint(sliced.length)} · 显示最近 60 天` : chartModeHint(totalDays);
    return { rows: sliced, granularity: "day", hint, totalDays };
  }

  const weekly = aggregateWeekly(daily);
  return { rows: weekly, granularity: "week", hint: "按周汇总", totalDays };
}

/** @deprecated use buildChartSlice */
export function pickChartRows(rows: BizRow[]): BizRow[] {
  return buildChartSlice(rows, "").rows;
}

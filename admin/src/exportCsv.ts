function escapeCell(v: unknown) {
  const s = String(v ?? "");
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function escapeHtml(v: unknown) {
  return String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function downloadCsv(filename: string, headers: string[], rows: string[][]) {
  const lines = [headers.map(escapeCell).join(","), ...rows.map((r) => r.map(escapeCell).join(","))];
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Excel 可直接打开的 HTML 表格，支持列宽与文本列格式（避免时间显示 ####） */
export function downloadExcelTable(
  filename: string,
  headers: string[],
  rows: string[][],
  opts: { colWidths?: number[]; textCols?: number[] } = {},
) {
  const { colWidths = [], textCols = [] } = opts;
  const textSet = new Set(textCols);
  const cols =
    colWidths.length > 0
      ? `<colgroup>${colWidths.map((w) => `<col width="${w}">`).join("")}</colgroup>`
      : "";
  const cell = (value: unknown, idx: number) => {
    const style = textSet.has(idx) ? " style=\"mso-number-format:'\\@';\"" : "";
    return `<td${style}>${escapeHtml(value)}</td>`;
  };
  const head = `<tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
  const body = rows.map((r) => `<tr>${r.map((c, i) => cell(c, i)).join("")}</tr>`).join("");
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><table border="1">${cols}${head}${body}</table></body></html>`;
  const blob = new Blob(["\uFEFF" + html], { type: "application/vnd.ms-excel;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".xls") ? filename : `${filename.replace(/\.csv$/i, "")}.xls`;
  a.click();
  URL.revokeObjectURL(url);
}

export function csvFilename(prefix: string, rangeLabel = "", ext = "csv") {
  const d = new Date();
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
  const slug = rangeLabel.replace(/[^\w\u4e00-\u9fff-]+/g, "_").replace(/_+/g, "_").slice(0, 24);
  return `${prefix}${slug ? `_${slug}` : ""}_${stamp}.${ext}`;
}

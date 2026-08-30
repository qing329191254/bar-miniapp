import * as XLSX from "xlsx";

function escapeCell(v: unknown) {
  const s = String(v ?? "");
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
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

type XlsxExportOpts = {
  colWidths?: number[];
  textCols?: number[];
  sheetName?: string;
};

/** 标准 .xlsx 导出（SheetJS） */
export function downloadXlsx(
  filename: string,
  headers: string[],
  rows: unknown[][],
  opts: XlsxExportOpts = {},
) {
  const { colWidths = [], textCols = [], sheetName = "Sheet1" } = opts;
  const safeSheet = sheetName.replace(/[\\/*?:[\]]/g, "_").slice(0, 31) || "Sheet1";
  const textSet = new Set(textCols);

  const normalized = rows.map((row) =>
    row.map((cell, idx) => {
      if (textSet.has(idx)) return String(cell ?? "");
      if (typeof cell === "number" && Number.isFinite(cell)) return cell;
      return cell ?? "";
    }),
  );

  const ws = XLSX.utils.aoa_to_sheet([headers, ...normalized]);

  for (let r = 0; r <= normalized.length; r++) {
    for (const c of textCols) {
      const addr = XLSX.utils.encode_cell({ r, c });
      const cell = ws[addr];
      if (!cell) continue;
      cell.t = "s";
      cell.v = String(cell.v ?? "");
      cell.z = "@";
    }
  }

  if (colWidths.length) {
    ws["!cols"] = colWidths.map((wch) => ({ wch }));
  }

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, safeSheet);
  const out = filename.endsWith(".xlsx") ? filename : `${filename.replace(/\.(csv|xls|xlsx)$/i, "")}.xlsx`;
  XLSX.writeFile(wb, out);
}

export function csvFilename(prefix: string, rangeLabel = "", ext = "csv") {
  const d = new Date();
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
  const slug = rangeLabel.replace(/[^\w\u4e00-\u9fff-]+/g, "_").replace(/_+/g, "_").slice(0, 24);
  return `${prefix}${slug ? `_${slug}` : ""}_${stamp}.${ext}`;
}

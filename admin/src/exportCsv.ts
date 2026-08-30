function escapeCell(v: unknown) {
  const s = String(v ?? "");
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function escapeXml(v: unknown) {
  return String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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

type ExcelExportOpts = {
  colWidths?: number[];
  textCols?: number[];
  numberCols?: number[];
  sheetName?: string;
};

/** Excel 2003 XML（SpreadsheetML），列宽/文本/数字格式正确，无 HTML 伪 xls 警告 */
export function downloadExcelTable(
  filename: string,
  headers: string[],
  rows: unknown[][],
  opts: ExcelExportOpts = {},
) {
  const { colWidths = [], textCols = [], numberCols = [], sheetName = "Sheet1" } = opts;
  const textSet = new Set(textCols);
  const numberSet = new Set(numberCols);
  const safeSheet = sheetName.replace(/[\\/*?:[\]]/g, "_").slice(0, 31) || "Sheet1";

  const cellXml = (value: unknown, idx: number) => {
    if (numberSet.has(idx)) {
      const n = Number(value);
      const num = Number.isFinite(n) ? n : 0;
      return `<Cell><Data ss:Type="Number">${num}</Data></Cell>`;
    }
    if (textSet.has(idx)) {
      return `<Cell ss:StyleID="Text"><Data ss:Type="String">${escapeXml(value)}</Data></Cell>`;
    }
    return `<Cell><Data ss:Type="String">${escapeXml(value)}</Data></Cell>`;
  };

  const cols = colWidths.map((w) => `<Column ss:Width="${w}"/>`).join("");
  const head = `<Row>${headers.map((h, i) => cellXml(h, i)).join("")}</Row>`;
  const body = rows.map((r) => `<Row>${r.map((c, i) => cellXml(c, i)).join("")}</Row>`).join("");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Styles>
<Style ss:ID="Default" ss:Name="Normal"><Alignment ss:Vertical="Center"/></Style>
<Style ss:ID="Text"><NumberFormat ss:Format="@"/></Style>
</Styles>
<Worksheet ss:Name="${escapeXml(safeSheet)}">
<Table>${cols}${head}${body}</Table>
</Worksheet>
</Workbook>`;

  const blob = new Blob(["\uFEFF" + xml], { type: "application/vnd.ms-excel;charset=utf-8" });
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

import fs from "node:fs";

export type ParseResult = {
  status: "PARSED" | "NEEDS_MANUAL" | "FAILED";
  parsed_json?: any;
  note?: string;
};

function parseCSV(text: string) {
  const lines = text.split(/\r?\n/).filter(Boolean);
  const rows = lines.map((l) => l.split(",").map((x) => x.trim()));
  const headers = rows[0] || [];
  const data = rows.slice(1).map((r) => {
    const obj: any = {};
    headers.forEach((h, i) => (obj[h || `col_${i}`] = r[i]));
    return obj;
  });
  return { headers, data };
}

export function parseFile(filePath: string, fileType: "pdf" | "xlsx" | "csv" | "json"): ParseResult {
  try {
    if (fileType === "json") {
      const raw = fs.readFileSync(filePath, "utf-8");
      return { status: "PARSED", parsed_json: JSON.parse(raw) };
    }
    if (fileType === "csv") {
      const raw = fs.readFileSync(filePath, "utf-8");
      return { status: "PARSED", parsed_json: parseCSV(raw) };
    }
    if (fileType === "xlsx") {
      // XLSX parser qo‘shilmagan bo‘lsa, manual fallback:
      return { status: "NEEDS_MANUAL", note: "XLSX parsing yoqilmagan. Manual totals entry kerak." };
    }
    // PDF OCR yo‘q: manual fallback
    return { status: "NEEDS_MANUAL", note: "PDF OCR yo‘q. Manual totals entry kerak." };
  } catch (e: any) {
    return { status: "FAILED", note: e?.message || "parse_failed" };
  }
}

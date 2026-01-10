import fs from "node:fs";
import path from "node:path";

export type LegalSourceType = "TAX_CODE" | "OFFICIAL_DECISION" | "OFFICIAL_EXPLANATION";
export type Jurisdiction = "UZ";

export type LegalSource = {
  id: string;
  jurisdiction: Jurisdiction;
  source_type: LegalSourceType;
  title: string;
  reference_code: string; // e.g. "SK:243"
  effective_from: string; // ISO
  effective_to?: string; // ISO
  text_content: string;
  metadata_json?: any;
  created_by: string;
  created_at: string;
};

export type LegalCitation = {
  id: string;
  legal_source_id: string;
  article?: string;
  paragraph?: string;
  clause?: string;
  citation_label: string; // e.g. "SK 243-modda, 2-band"
};

export type TaxDocument = {
  id: string;
  org_id?: string;
  filename: string;
  file_type: "pdf" | "xlsx" | "csv" | "json";
  storage_path: string;
  uploaded_by: string;
  uploaded_at: string;
  parsed_json?: any;
  parse_status: "PARSED" | "NEEDS_MANUAL" | "FAILED";
  period_from?: string;
  period_to?: string;
};

export type TaxReport = {
  id: string;
  document_id: string;
  report_type: string;
  period: string;
  totals_json: any;
  validation_results_json: any;
};

export type TaxPayment = {
  id: string;
  date: string;
  amount: number;
  tax_type: string;
  reference?: string;
  source_document_id?: string;
};

export type GuidanceTemplate = {
  id: string;
  topic: string;
  steps: string[];
  warnings: string[];
  updated_at: string;
  updated_by: string;
};

type StoreShape = {
  legal_sources: LegalSource[];
  legal_citations: LegalCitation[];
  tax_documents: TaxDocument[];
  tax_reports: TaxReport[];
  tax_payments: TaxPayment[];
  cabinet_guidance: GuidanceTemplate[];
};

const STORE_DIR = path.join(process.cwd(), "apps", "api", "storage");
const STORE_FILE = path.join(STORE_DIR, "tax_store.json");

function ensureStore() {
  if (!fs.existsSync(STORE_DIR)) fs.mkdirSync(STORE_DIR, { recursive: true });
  if (!fs.existsSync(STORE_FILE)) {
    const empty: StoreShape = {
      legal_sources: [],
      legal_citations: [],
      tax_documents: [],
      tax_reports: [],
      tax_payments: [],
      cabinet_guidance: []
    };
    fs.writeFileSync(STORE_FILE, JSON.stringify(empty, null, 2), "utf-8");
  }
}

export function readStore(): StoreShape {
  ensureStore();
  const raw = fs.readFileSync(STORE_FILE, "utf-8");
  return JSON.parse(raw) as StoreShape;
}

export function writeStore(next: StoreShape) {
  ensureStore();
  fs.writeFileSync(STORE_FILE, JSON.stringify(next, null, 2), "utf-8");
}

export function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export function storagePathFor(filename: string) {
  ensureStore();
  const safe = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
  return path.join(STORE_DIR, "tax_docs", `${Date.now()}_${safe}`);
}

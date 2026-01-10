import type http from "http";
import fs from "node:fs";
import { readStore, writeStore, uuid, nowIso, storagePathFor } from "./tax.store";
import { parseFile } from "./tax.parse";
import { taxRegimeValidator, vatObligationMonitor, penaltyRiskScanner } from "./tax.compute";
import { taxChatReply } from "./tax.chat";
import type { AgentSignal } from "@firmos/shared";
import {
  overpaymentFinder,
  deductibilityAudit,
  vatExitSimulation,
  taxWhatIf,
  cabinetGuidance,
  reportPreparation
} from "./tax.compute";

type RegisterRoute = (method: string, path: string, handler: (req: http.IncomingMessage, res: http.ServerResponse) => any) => void;

function json(res: http.ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(body));
}

function requireHeader(req: http.IncomingMessage, name: string): string | null {
  const v = req.headers[name.toLowerCase()];
  if (!v) return null;
  return Array.isArray(v) ? v[0] : v;
}

function requireAuth(req: http.IncomingMessage) {
  const role = requireHeader(req, "x-role");
  const actorId = requireHeader(req, "x-actor-id");
  const orgId = requireHeader(req, "x-org-id");
  if (!role || !actorId || !orgId) return null;
  return { role, actorId, orgId };
}

function requireRole(auth: { role: string }, min: "ANALYST" | "OPERATOR" | "ADMIN" | "OWNER") {
  const order = ["ANALYST", "OPERATOR", "ADMIN", "OWNER"];
  return order.indexOf(auth.role) >= order.indexOf(min);
}

export function registerTax(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  // -------------------------
  // Uploads (OPERATOR+)
  // POST /api/v1/agents/tax/uploads
  // body: { filename, file_type, base64, period_from?, period_to? }
  // -------------------------
    register("POST", "/api/v1/agents/tax/insights/deductibility", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const expenses = Array.isArray(body?.expenses) ? body.expenses : [];
    const r = deductibilityAudit({ expenses });
    return json(res, 200, r);
  });
    register("GET", "/api/v1/agents/tax/insights/overpayment", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const q = (req as any).query || {};
    const taxType = String(q.taxType || "INCOME");
    const expectedBase = Number(q.expectedBase || 0);
    const r = overpaymentFinder({ taxType, expectedBase });
    return json(res, 200, r);
  });
    register("POST", "/api/v1/agents/tax/insights/vat-exit/simulate", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const r = vatExitSimulation({
      currentVatPaidMonthly: Number(body?.currentVatPaidMonthly || 0),
      projectedNonVatTaxMonthly: Number(body?.projectedNonVatTaxMonthly || 0)
    });
    return json(res, 200, r);
  });
    register("POST", "/api/v1/agents/tax/what-if", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const r = taxWhatIf({ scenario: body?.scenario || body });
    return json(res, 200, r);
  });
    register("POST", "/api/v1/agents/tax/cabinet/guidance", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const topic = String(body?.topic || "");
    if (!topic) return json(res, 400, { error: "BAD_REQUEST" });

    const r = cabinetGuidance(topic);
    return json(res, 200, r);
  });
    register("POST", "/api/v1/agents/tax/reports/prepare", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const documentId = String(body?.document_id || body?.documentId || "");
    const reportType = String(body?.report_type || body?.reportType || "");
    if (!documentId || !reportType) return json(res, 400, { error: "BAD_REQUEST" });

    const r = reportPreparation({ documentId, reportType });
    return json(res, 200, r);
  });
  
  register("POST", "/api/v1/agents/tax/uploads", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    if (!body?.filename || !body?.file_type || !body?.base64) return json(res, 400, { error: "BAD_REQUEST" });

    const file_type = String(body.file_type);
    if (!["pdf", "xlsx", "csv", "json"].includes(file_type)) return json(res, 400, { error: "BAD_FILE_TYPE" });

    const storePath = storagePathFor(String(body.filename));
    fs.mkdirSync(storePath.split("/").slice(0, -1).join("/"), { recursive: true });
    fs.writeFileSync(storePath, Buffer.from(String(body.base64), "base64"));

    const parsed = parseFile(storePath, file_type as any);

    const s = readStore();
    const doc = {
      id: uuid("taxdoc"),
      org_id: auth.orgId,
      filename: String(body.filename),
      file_type,
      storage_path: storePath,
      uploaded_by: auth.actorId,
      uploaded_at: nowIso(),
      parsed_json: parsed.parsed_json,
      parse_status: parsed.status,
      period_from: body.period_from ? String(body.period_from) : undefined,
      period_to: body.period_to ? String(body.period_to) : undefined
    };
    s.tax_documents.push(doc);
    writeStore(s);

    return json(res, 200, { ok: true, document: doc, parse_note: parsed.note || null });
  });

  // GET /api/v1/agents/tax/documents?from=&to= (ANALYST+)
  register("GET", "/api/v1/agents/tax/documents", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");

    const s = readStore();
    const docs = s.tax_documents.filter((d) => {
      if (!from || !to) return true;
      return (d.period_from || "") >= from && (d.period_to || "") <= to;
    });
    return json(res, 200, { documents: docs });
  });

  // GET /api/v1/agents/tax/documents/:id (ANALYST+)
  register("GET", "/api/v1/agents/tax/documents/:id", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const s = readStore();
    const doc = s.tax_documents.find((d) => d.id === id);
    if (!doc) return json(res, 404, { error: "NOT_FOUND" });
    return json(res, 200, { document: doc });
  });

  // POST /api/v1/agents/tax/documents/:id/manual-totals (OPERATOR+)
  register("POST", "/api/v1/agents/tax/documents/:id/manual-totals", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const body = (req as any).body as any;
    const s = readStore();
    const doc = s.tax_documents.find((d) => d.id === id);
    if (!doc) return json(res, 404, { error: "NOT_FOUND" });

    doc.parsed_json = { ...(doc.parsed_json || {}), manual_totals: body?.totals || body };
    doc.parse_status = "PARSED";
    writeStore(s);

    return json(res, 200, { ok: true, document: doc });
  });

  // -------------------------
  // Insights endpoints (ANALYST+ / OPERATOR+ where needed)
  // -------------------------
  register("GET", "/api/v1/agents/tax/insights/regime", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const q = (req as any).query || {};
    const annualTurnover = Number(q.annualTurnover || 0);
    const employees = Number(q.employees || 0);
    const currentRegime = String(q.currentRegime || "");
    const activityCode = String(q.activityCode || "");

    const r = taxRegimeValidator({ annualTurnover, employees, currentRegime, activityCode });
    return json(res, 200, r);
  });

  register("GET", "/api/v1/agents/tax/insights/vat-obligation", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const q = (req as any).query || {};
    const turnover12m = Number(q.turnover12m || 0);
    const r = vatObligationMonitor({ turnover12m });
    return json(res, 200, r);
  });

  register("GET", "/api/v1/agents/tax/insights/penalty-risk", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const q = (req as any).query || {};
    const lateReports = Number(q.lateReports || 0);
    const mismatches = Number(q.mismatches || 0);
    const missingFields = Number(q.missingFields || 0);

    const r = penaltyRiskScanner({ lateReports, mismatches, missingFields });
    return json(res, 200, r);
  });

  // -------------------------
  // Chat (ANALYST+)
  // -------------------------
  register("POST", "/api/v1/agents/tax/chat", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    if (!body?.message) return json(res, 400, { error: "BAD_REQUEST" });

    const reply = taxChatReply(String(body.message));
    return json(res, 200, reply);
  });

  // -------------------------
  // Run (emit signal) (OPERATOR+)
  // -------------------------
  register("POST", "/api/v1/agents/tax/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const s = readStore();
    const hasLegal = s.legal_sources.length > 0;

    const signal: AgentSignal<any> = {
      id: uuid("sig_tax"),
      agent: "TAX",
      createdAt: nowIso(),
      timeframe: { from: nowIso(), to: nowIso() },
      title: "Tax Optimizer: registry-based checks (official-only)",
      summary: hasLegal
        ? `Rasmiy manbalar soni: ${s.legal_sources.length}. Tax checks ishlashga tayyor.`
        : "Legal sources registry bo‘sh. Tax hisob-kitoblari uchun rasmiy asos kiritilishi shart.",
      riskLevel: hasLegal ? "LOW" : "MED",
      confidence: 0.55,
      assumptions: ["Hisob-kitoblar faqat registry’dagi rasmiy qoidalar bo‘lsa ishlaydi. Fabrication taqiqlangan."],
      insight: { legal_sources_count: s.legal_sources.length },
      evidence: [{ source: "tax:legal_sources_registry" }],
      legalBasis: [],
      advisoryNote: "Maslahat xarakterida. Hisobot yuborilmaydi, kabinetga login qilinmaydi. Buxgalter bilan tasdiqlang."
    };

    pushSignal(signal);
    return json(res, 200, { ok: true, signalId: signal.id });
  });

  // -------------------------
  // Admin Legal Sources (ADMIN/OWNER)
  // /api/v1/admin/legal-sources
  // -------------------------
  register("GET", "/api/v1/admin/legal-sources", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ADMIN")) return json(res, 403, { error: "FORBIDDEN" });
    const s = readStore();
    return json(res, 200, { legal_sources: s.legal_sources, legal_citations: s.legal_citations });
  });

  register("POST", "/api/v1/admin/legal-sources", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ADMIN")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    if (!body?.source_type || !body?.title || !body?.reference_code || !body?.text_content) {
      return json(res, 400, { error: "BAD_REQUEST" });
    }

    const s = readStore();
    const ls = {
      id: uuid("legsrc"),
      jurisdiction: "UZ",
      source_type: body.source_type,
      title: String(body.title),
      reference_code: String(body.reference_code),
      effective_from: String(body.effective_from || nowIso()),
      effective_to: body.effective_to ? String(body.effective_to) : undefined,
      text_content: String(body.text_content),
      metadata_json: body.metadata_json || {},
      created_by: auth.actorId,
      created_at: nowIso()
    };

    s.legal_sources.push(ls);
    writeStore(s);
    return json(res, 200, { ok: true, legal_source: ls });
  });

  register("PUT", "/api/v1/admin/legal-sources/:id", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ADMIN")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const body = (req as any).body as any;
    const s = readStore();
    const ls = s.legal_sources.find((x) => x.id === id);
    if (!ls) return json(res, 404, { error: "NOT_FOUND" });

    Object.assign(ls, {
      title: body.title ?? ls.title,
      reference_code: body.reference_code ?? ls.reference_code,
      effective_from: body.effective_from ?? ls.effective_from,
      effective_to: body.effective_to ?? ls.effective_to,
      text_content: body.text_content ?? ls.text_content,
      metadata_json: body.metadata_json ?? ls.metadata_json
    });

    writeStore(s);
    return json(res, 200, { ok: true, legal_source: ls });
  });

  register("DELETE", "/api/v1/admin/legal-sources/:id", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ADMIN")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const s = readStore();
    s.legal_sources = s.legal_sources.filter((x) => x.id !== id);
    s.legal_citations = s.legal_citations.filter((c) => c.legal_source_id !== id);
    writeStore(s);
    return json(res, 200, { ok: true });
  });
}

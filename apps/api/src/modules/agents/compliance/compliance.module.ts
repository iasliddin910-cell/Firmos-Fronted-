import type http from "http";
import type { AgentSignal } from "@firmos/shared";

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

// ---- Official sources registry (mock, manual) ----
// IMPORTANT: Compliance uses ONLY official sources. We store links/refs but do NOT browse here.
type OfficialSource = {
  id: string;
  publisher: "LEX_UZ" | "PRESIDENT_UZ" | "PARLIAMENT_UZ" | "OFFICIAL_EXPLANATION";
  title: string;
  ref: string;            // e.g. lex.uz doc id or decree number
  publishedAt: string;    // ISO
  effectiveFrom?: string; // ISO
  tags: string[];
};

type DeadlineItem = {
  id: string;
  title: string;
  dueDate: string; // ISO
  severity: "LOW" | "MED" | "HIGH";
  note?: string;
};

type ConflictLogItem = {
  id: string;
  at: string;
  agents: string[];
  topic: string;
  note: string;
};

const sources: OfficialSource[] = [];
const deadlines: DeadlineItem[] = [];
const conflictLog: ConflictLogItem[] = [];

function nowIso() {
  return new Date().toISOString();
}

function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function daysFromNow(n: number) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString();
}

// ---- Core compliance computations ----
function computeLawChanges() {
  // Sort by publishedAt desc
  return sources.slice().sort((a, b) => (a.publishedAt < b.publishedAt ? 1 : -1)).slice(0, 20);
}

function computeDeadlines() {
  const now = nowIso();
  const upcoming = deadlines
    .map((d) => ({
      ...d,
      daysLeft: Math.ceil((new Date(d.dueDate).getTime() - new Date(now).getTime()) / (1000 * 60 * 60 * 24))
    }))
    .sort((a, b) => a.daysLeft - b.daysLeft);
  return upcoming;
}

function estimateComplianceRiskScore(lawChangesCount: number, urgentDeadlines: number, conflicts: number) {
  // Deterministic scoring 0..100
  let score = 20;
  score += Math.min(30, lawChangesCount * 3);
  score += Math.min(40, urgentDeadlines * 10);
  score += Math.min(30, conflicts * 10);
  return Math.min(100, score);
}

function activityPermissionCheck(activity: string) {
  // This must be backed by official basis later. For now: "unknown => needs official check".
  // We do NOT fabricate legality.
  return {
    activity,
    status: "UNKNOWN" as const,
    note: "Ruxsat/litsenziya talabi bo‘yicha rasmiy manba kiritilmagan. Tekshirish uchun rasmiy hujjat ref kerak."
  };
}

function contractRiskScan(text: string) {
  // Deterministic heuristic: look for unilateral penalty clauses
  const lower = (text || "").toLowerCase();
  const risky = lower.includes("bir tomonlama") || lower.includes("jarima") || lower.includes("penalty");
  return {
    risky,
    issues: risky
      ? ["Shartnomada bir tomonlama jarima yoki noaniq majburiyat bandlari bo‘lishi mumkin (heuristika)."]
      : []
  };
}

function crossAgentCheck(proposal: { agent: string; text: string }) {
  // We do not decide; we flag potential compliance risk
  const t = proposal.text.toLowerCase();
  const risky =
    t.includes("60%") || t.includes("chegirma 60") || t.includes("discount 60") || t.includes("no limit");
  return {
    proposal,
    status: risky ? "POTENTIAL_CONFLICT" : "OK",
    note: risky
      ? "Taklifda cheklovlar bo‘lishi mumkin. Rasmiy normativ asos bilan solishtirish talab qilinadi."
      : "Aniq ziddiyat topilmadi (hozircha)."
  };
}

function computeComplianceInsights() {
  const changes = computeLawChanges();
  const dls = computeDeadlines();
  const urgent = dls.filter((d) => d.daysLeft <= 21).length;
  const conflicts = conflictLog.length;
  const riskScore = estimateComplianceRiskScore(changes.length, urgent, conflicts);

  return {
    officialSourcesOnly: true,
    sources: changes,
    deadlines: dls,
    conflictLog: conflictLog.slice(-50),
    complianceRiskScore: riskScore
  };
}

// ---- Register module routes ----
export function registerCompliance(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  // Admin-like seed endpoints (still protected by headers)
  register("POST", "/api/v1/agents/compliance/mock/source", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<OfficialSource> | undefined;
    if (!body?.publisher || !body?.title || !body?.ref) return json(res, 400, { error: "BAD_REQUEST" });

    const s: OfficialSource = {
      id: uuid("src"),
      publisher: body.publisher as any,
      title: String(body.title),
      ref: String(body.ref),
      publishedAt: body.publishedAt || nowIso(),
      effectiveFrom: body.effectiveFrom ? String(body.effectiveFrom) : undefined,
      tags: Array.isArray(body.tags) ? (body.tags as any) : []
    };
    sources.push(s);
    return json(res, 200, { ok: true, source: s });
  });

  register("POST", "/api/v1/agents/compliance/mock/deadline", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<DeadlineItem> | undefined;
    if (!body?.title || !body?.dueDate) return json(res, 400, { error: "BAD_REQUEST" });

    const d: DeadlineItem = {
      id: uuid("ddl"),
      title: String(body.title),
      dueDate: String(body.dueDate),
      severity: (body.severity as any) || "MED",
      note: body.note ? String(body.note) : undefined
    };
    deadlines.push(d);
    return json(res, 200, { ok: true, deadline: d });
  });

  register("POST", "/api/v1/agents/compliance/mock/conflict", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<ConflictLogItem> | undefined;
    if (!body?.topic || !body?.note) return json(res, 400, { error: "BAD_REQUEST" });

    const c: ConflictLogItem = {
      id: uuid("conf"),
      at: nowIso(),
      agents: Array.isArray(body.agents) ? (body.agents as any) : ["UNKNOWN"],
      topic: String(body.topic),
      note: String(body.note)
    };
    conflictLog.push(c);
    return json(res, 200, { ok: true, conflict: c });
  });

  // Insights
  register("GET", "/api/v1/agents/compliance/insights", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const data = computeComplianceInsights();
    return json(res, 200, data);
  });

  // Activity permission check (guidance)
  register("POST", "/api/v1/agents/compliance/activity/check", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as { activity?: string } | undefined;
    if (!body?.activity) return json(res, 400, { error: "BAD_REQUEST" });

    const r = activityPermissionCheck(body.activity);
    return json(res, 200, r);
  });

  // Contract risk scan
  register("POST", "/api/v1/agents/compliance/contract/scan", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as { text?: string } | undefined;
    if (!body?.text) return json(res, 400, { error: "BAD_REQUEST" });

    const r = contractRiskScan(body.text);
    return json(res, 200, r);
  });

  // Cross-agent check
  register("POST", "/api/v1/agents/compliance/cross-agent/check", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as { agent?: string; text?: string } | undefined;
    if (!body?.agent || !body?.text) return json(res, 400, { error: "BAD_REQUEST" });

    const r = crossAgentCheck({ agent: body.agent, text: body.text });
    return json(res, 200, r);
  });

  // Run => emit signal
  register("POST", "/api/v1/agents/compliance/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const data = computeComplianceInsights();
    const riskLevel = data.complianceRiskScore >= 75 ? "HIGH" : data.complianceRiskScore >= 45 ? "MED" : "LOW";

    const signal: AgentSignal<any> = {
      id: uuid("sig_cmp"),
      agent: "COMPLIANCE",
      createdAt: nowIso(),
      timeframe: { from: nowIso(), to: nowIso() },
      title: "Compliance: qonun o‘zgarishi, deadline va ziddiyatlar",
      summary: `Yangi rasmiy manbalar: ${data.sources.length}. Deadline: ${data.deadlines.length}. Risk score: ${data.complianceRiskScore}/100.`,
      riskLevel,
      confidence: 0.6,
      assumptions: [
        "Faqat rasmiy manbalar registry ishlatiladi (manual/mock).",
        "Risk score deterministik heuristika (qaror emas)."
      ],
      insight: data,
      evidence: [{ source: "compliance:official-source-registry" }],
      legalBasis: [],
      advisoryNote: "Bu tahlil maslahat xarakterida. Qarorlar va huquqiy bahoni yurist bilan tasdiqlang."
    };

    pushSignal(signal);
    return json(res, 200, { ok: true, signalId: signal.id });
  });
}

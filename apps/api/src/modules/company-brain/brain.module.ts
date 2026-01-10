import type http from "http";
import { readBrainStore, writeBrainStore, uuid, nowIso } from "./brain.store";
import { detectConflicts, priorityScore, enforceProtocol, suggestFromMemory } from "./brain.logic";
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
function requireRole(auth: { role: string }, min: "ANALYST" | "OPERATOR" | "ADMIN" | "OWNER") {
  const order = ["ANALYST", "OPERATOR", "ADMIN", "OWNER"];
  return order.indexOf(auth.role) >= order.indexOf(min);
}

export function registerCompanyBrain(register: RegisterRoute, getSignals: () => AgentSignal<any>[]) {
  // 1) Priority view
  register("GET", "/api/v1/company-brain/priority", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const signals = getSignals();
    const ranked = signals
      .map((s) => ({ ...s, priority: priorityScore(s) }))
      .sort((a, b) => b.priority - a.priority)
      .slice(0, 50);

    return json(res, 200, { items: ranked });
  });

  // 2) Council snapshot (conflicts)
  register("GET", "/api/v1/company-brain/council", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const signals = getSignals();
    const conflicts = detectConflicts(signals);
    return json(res, 200, { signals_count: signals.length, conflicts, signals });
  });

  // 3) Create decision (OPERATOR+)
  register("POST", "/api/v1/company-brain/decisions", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const body = (req as any).body as any;
    const title = String(body?.title || "");
    const proposal = body?.proposal || null;

    const signals = getSignals();
    const conflicts = detectConflicts(signals);

    const decision = {
      id: uuid("decision"),
      created_at: nowIso(),
      created_by: auth.actorId,
      title,
      proposal,
      stage: "SIMULATION",
      signals_snapshot: signals,
      conflicts,
      requires_human_approval: true,
      audit: [{ at: nowIso(), actor: auth.actorId, action: "CREATE_DECISION", payload: { title } }]
    };

    const protocolErrors = enforceProtocol(decision);
    if (protocolErrors.length) return json(res, 400, { error: "PROTOCOL_VIOLATION", protocolErrors });

    const store = readBrainStore();
    store.decisions.push(decision as any);
    writeBrainStore(store);

    const memoryHints = suggestFromMemory(proposal);

    return json(res, 200, { ok: true, decision, memoryHints });
  });

  // 4) Update decision stage (OPERATOR+)
  register("POST", "/api/v1/company-brain/decisions/:id/stage", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OPERATOR")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const body = (req as any).body as any;
    const nextStage = String(body?.stage || "");

    const store = readBrainStore();
    const d = store.decisions.find((x) => x.id === id);
    if (!d) return json(res, 404, { error: "NOT_FOUND" });

    d.stage = nextStage as any;
    if (body?.simulation) d.simulation = body.simulation;
    if (body?.pilot) d.pilot = body.pilot;
    if (body?.result) d.result = body.result;

    d.audit.push({ at: nowIso(), actor: auth.actorId, action: "UPDATE_STAGE", payload: { nextStage } });

    const protocolErrors = enforceProtocol(d);
    if (protocolErrors.length) return json(res, 400, { error: "PROTOCOL_VIOLATION", protocolErrors });

    writeBrainStore(store);
    return json(res, 200, { ok: true, decision: d });
  });

  // 5) Human approval (OWNER only)
  register("POST", "/api/v1/company-brain/decisions/:id/approve", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "OWNER")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const body = (req as any).body as any;
    const approved = Boolean(body?.approved);

    const store = readBrainStore();
    const d = store.decisions.find((x) => x.id === id);
    if (!d) return json(res, 404, { error: "NOT_FOUND" });

    // must be in APPROVAL stage
    if (d.stage !== "APPROVAL") return json(res, 400, { error: "BAD_STAGE", note: "Approval faqat APPROVAL stage’da." });

    d.approved = approved;
    d.approved_by = auth.actorId;
    d.approved_at = nowIso();
    d.audit.push({ at: nowIso(), actor: auth.actorId, action: "HUMAN_APPROVAL", payload: { approved } });

    // store learning if failed
    if (d.result?.outcome === "FAILED") {
      const lessons = d.result?.lessons || [];
      for (const l of lessons) {
        store.memory.push({
          id: uuid("memory"),
          created_at: nowIso(),
          decision_id: d.id,
          lesson: l,
          tag: String(l).slice(0, 32)
        });
      }
    }

    writeBrainStore(store);
    return json(res, 200, { ok: true, decision: d });
  });

  // 6) List decisions (ANALYST+)
  register("GET", "/api/v1/company-brain/decisions", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const store = readBrainStore();
    return json(res, 200, { decisions: store.decisions.slice(-50) });
  });

  // 7) Read decision (ANALYST+)
  register("GET", "/api/v1/company-brain/decisions/:id", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });
    if (!requireRole(auth, "ANALYST")) return json(res, 403, { error: "FORBIDDEN" });

    const id = (req as any).params?.id;
    const store = readBrainStore();
    const d = store.decisions.find((x) => x.id === id);
    if (!d) return json(res, 404, { error: "NOT_FOUND" });
    return json(res, 200, { decision: d });
  });
}

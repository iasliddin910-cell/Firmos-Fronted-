import type http from "http";
import type { AuditEvent } from "@firmos/shared";

type RegisterRoute = (method: string, path: string, handler: (req: http.IncomingMessage, res: http.ServerResponse) => any) => void;

// In-memory storage for now (later DB)
const auditLog: AuditEvent[] = [];
const signals: any[] = [];

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

/**
 * RBAC (minimal): require x-role + x-actor-id + x-org-id on every protected endpoint.
 * We'll enforce properly later, but this keeps the contract stable.
 */
function requireAuth(req: http.IncomingMessage) {
  const role = requireHeader(req, "x-role");
  const actorId = requireHeader(req, "x-actor-id");
  const orgId = requireHeader(req, "x-org-id");
  if (!role || !actorId || !orgId) return null;
  return { role, actorId, orgId };
}

export function registerCore(register: RegisterRoute) {
  // audit: append event
  register("POST", "/api/v1/audit", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as AuditEvent | undefined;
    if (!body?.action || !body?.correlationId) return json(res, 400, { error: "BAD_REQUEST" });

    auditLog.push(body);
    return json(res, 200, { ok: true });
  });

  // audit: list (admin/owner only later)
  register("GET", "/api/v1/audit", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    return json(res, 200, { items: auditLog.slice(-200) });
  });

  // signals: ingest signal (agent writes)
  register("POST", "/api/v1/signals", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body;
    if (!body?.id || !body?.agent || !body?.title) return json(res, 400, { error: "BAD_REQUEST" });

    signals.push(body);
    return json(res, 200, { ok: true });
  });

  // signals: list (company brain reads)
  register("GET", "/api/v1/signals", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");
    const filtered = signals.filter((s) => {
      if (!from || !to) return true;
      return s?.timeframe?.from >= from && s?.timeframe?.to <= to;
    });

    return json(res, 200, { items: filtered.slice(-500) });
  });
}

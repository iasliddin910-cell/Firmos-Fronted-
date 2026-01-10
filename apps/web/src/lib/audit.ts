import { apiPost } from "./api";
import type { AuditAction, AuditEvent } from "@firmos/shared";

function nowIso() {
  return new Date().toISOString();
}

function correlationId() {
  // simple deterministic-ish id
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function audit(action: AuditAction, target?: string, meta?: Record<string, unknown>) {
  if (typeof window === "undefined") return;

  const actorId = localStorage.getItem("firmos_actor_id") || "user-1";
  const orgId = localStorage.getItem("firmos_org_id") || "default-org";

  const evt: AuditEvent = {
    at: nowIso(),
    actorId,
    orgId,
    action,
    target,
    meta,
    correlationId: correlationId()
  };

  await apiPost<{ ok: boolean }>("/api/v1/audit", evt);
}

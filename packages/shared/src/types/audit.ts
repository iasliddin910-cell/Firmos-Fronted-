export type AuditAction =
  | "NAVIGATE"
  | "VIEW_PAGE"
  | "RUN_SIMULATION"
  | "UPLOAD_DOCUMENT"
  | "CHANGE_FEATURE_FLAG"
  | "CHANGE_AGENT_STATUS"
  | "CHANGE_INCIDENT_MODE";

export type AuditEvent = {
  at: string; // ISO timestamp
  actorId: string;
  orgId: string;
  action: AuditAction;
  target?: string;
  meta?: Record<string, unknown>;
  correlationId: string;
};

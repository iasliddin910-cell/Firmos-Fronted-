import type { AgentName } from "./agent";

export type RiskLevel = "LOW" | "MED" | "HIGH";

export type LegalBasisRef = {
  legalSourceId: string;      // points to official registry item in backend
  citationLabel: string;      // human-readable label shown in UI
};

export type EvidenceRef = {
  source: string;             // e.g. "website:funnel", "orders:db", "tax:documents"
  ref?: string;               // optional ID / pointer
};

export type Timeframe = { from: string; to: string };

export type AgentSignal<TInsight = unknown> = {
  id: string;
  agent: AgentName;
  createdAt: string;          // ISO timestamp
  timeframe: Timeframe;

  title: string;
  summary: string;

  riskLevel: RiskLevel;
  confidence: number;         // 0..1
  assumptions?: string[];

  insight: TInsight;

  evidence?: EvidenceRef[];
  legalBasis?: LegalBasisRef[];

  advisoryNote: string;       // MUST include advisory disclaimer
};

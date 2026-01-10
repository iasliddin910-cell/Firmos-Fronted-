import fs from "node:fs";
import path from "node:path";

export type DecisionStage = "SIMULATION" | "PILOT" | "RESULT" | "APPROVAL";
export type ConflictSeverity = "LOW" | "MED" | "HIGH";

export type BrainDecision = {
  id: string;
  created_at: string;
  created_by: string;

  title: string;
  proposal: any; // e.g. { agent:"Sales", action:"price_increase_5", expected_effect:"+8%" }

  stage: DecisionStage;

  signals_snapshot: any[]; // signals from agents at decision time
  conflicts: Array<{ id: string; severity: ConflictSeverity; description: string; involved_agents: string[] }>;

  simulation?: { inputs: any; output: any; notes?: string };
  pilot?: { scope: string; duration_days: number; exit_conditions: string[]; started_at?: string; ended_at?: string };
  result?: { expected_vs_real: any; outcome: "SUCCESS" | "FAILED"; lessons: string[] };

  requires_human_approval: boolean;
  approved?: boolean;
  approved_by?: string;
  approved_at?: string;

  audit: Array<{ at: string; actor: string; action: string; payload?: any }>;
};

type StoreShape = {
  decisions: BrainDecision[];
  memory: Array<{
    id: string;
    created_at: string;
    decision_id: string;
    lesson: string;
    tag: string; // e.g. "elasticity_overestimated"
  }>;
};

const STORE_DIR = path.join(process.cwd(), "apps", "api", "storage");
const STORE_FILE = path.join(STORE_DIR, "company_brain_store.json");

function ensure() {
  if (!fs.existsSync(STORE_DIR)) fs.mkdirSync(STORE_DIR, { recursive: true });
  if (!fs.existsSync(STORE_FILE)) {
    const empty: StoreShape = { decisions: [], memory: [] };
    fs.writeFileSync(STORE_FILE, JSON.stringify(empty, null, 2), "utf-8");
  }
}

export function readBrainStore(): StoreShape {
  ensure();
  return JSON.parse(fs.readFileSync(STORE_FILE, "utf-8")) as StoreShape;
}
export function writeBrainStore(next: StoreShape) {
  ensure();
  fs.writeFileSync(STORE_FILE, JSON.stringify(next, null, 2), "utf-8");
}

export function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}
export function nowIso() {
  return new Date().toISOString();
}

import type http from "http";
import type { AgentSignal, RiskLevel } from "@firmos/shared";

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

type PriorityItem = {
  signalId: string;
  title: string;
  agent: string;
  riskLevel: RiskLevel;
  confidence: number;
  score: number;
  why: string[];
};

type Conflict = {
  aSignalId: string;
  bSignalId: string;
  topic: string;
  note: string;
};

type CompanyBrainAnalysis = {
  timeframe?: { from: string; to: string };
  topProblems: PriorityItem[];
  conflicts: Conflict[];
  notes: string[];
};

function riskWeight(r: RiskLevel): number {
  if (r === "HIGH") return 1.0;
  if (r === "MED") return 0.6;
  return 0.3;
}

function computeScore(s: AgentSignal<any>) {
  const w = riskWeight(s.riskLevel);
  const c = Math.max(0, Math.min(1, Number(s.confidence ?? 0.5)));
  return w * (0.7 + 0.3 * c);
}

function extractTopic(title: string): string {
  const t = (title || "").toLowerCase();
  if (t.includes("vat") || t.includes("qqs")) return "TAX:VAT";
  if (t.includes("security") || t.includes("xavfsiz") || t.includes("leak") || t.includes("sız")) return "CYBER:SECURITY";
  if (t.includes("cash") || t.includes("runway") || t.includes("pul")) return "CASHFLOW";
  if (t.includes("complaint") || t.includes("shikoyat") || t.includes("support")) return "SALES:COMPLAINT";
  if (t.includes("roi") || t.includes("ads") || t.includes("reklama")) return "MARKETING";
  return "GENERAL";
}

/**
 * Conflict logic (simple deterministic):
 * - If same topic has two HIGH signals with opposite directions in summary keywords.
 * We do not fabricate decisions. We just surface "ziddiyat bor".
 */
function findConflicts(items: AgentSignal<any>[]): Conflict[] {
  const conflicts: Conflict[] = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i];
      const b = items[j];
      const ta = extractTopic(a.title);
      const tb = extractTopic(b.title);
      if (ta !== tb) continue;

      const sa = (a.summary || "").toLowerCase();
      const sb = (b.summary || "").toLowerCase();

      const aUp = sa.includes("osh") || sa.includes("+") || sa.includes("increase");
      const aDown = sa.includes("kam") || sa.includes("-") || sa.includes("decrease");
      const bUp = sb.includes("osh") || sb.includes("+") || sb.includes("increase");
      const bDown = sb.includes("kam") || sb.includes("-") || sb.includes("decrease");

      const opposite = (aUp && bDown) || (aDown && bUp);
      if (opposite && a.riskLevel === "HIGH" && b.riskLevel === "HIGH") {
        conflicts.push({
          aSignalId: a.id,
          bSignalId: b.id,
          topic: ta,
          note: "Bir xil mavzu bo‘yicha signal’lar yo‘nalishi qarama-qarshi. Qaror oldidan majlis (AI Council) talab qilinadi."
        });
      }
    }
  }
  return conflicts;
}

export function registerCompanyBrain(register: RegisterRoute, signalSource: () => AgentSignal<any>[]) {
  register("GET", "/api/v1/agents/company-brain/analysis", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");

    const all = signalSource();
    const filtered = all.filter((s) => {
      if (!from || !to) return true;
      return s?.timeframe?.from >= from && s?.timeframe?.to <= to;
    });

    const ranked = filtered
      .map((s) => {
        const score = computeScore(s);
        const why = [
          `risk=${s.riskLevel}`,
          `confidence=${Number(s.confidence ?? 0.5).toFixed(2)}`,
          s.assumptions?.length ? `assumptions=${s.assumptions.length}` : "assumptions=0"
        ];
        return {
          signalId: s.id,
          title: s.title,
          agent: s.agent,
          riskLevel: s.riskLevel,
          confidence: s.confidence,
          score,
          why
        } satisfies PriorityItem;
      })
      .sort((a, b) => b.score - a.score);

    const analysis: CompanyBrainAnalysis = {
      timeframe: from && to ? { from, to } : undefined,
      topProblems: ranked.slice(0, 10),
      conflicts: findConflicts(filtered),
      notes: [
        "Company Brain qaror chiqarmaydi; faqat ustuvorlik va ziddiyatlarni ko‘rsatadi.",
        "Keyingi qadam: har bir top muammo uchun Simulyatsiya → Pilot → Real natija → Inson tasdiqi."
      ]
    };

    return json(res, 200, analysis);
  });
}

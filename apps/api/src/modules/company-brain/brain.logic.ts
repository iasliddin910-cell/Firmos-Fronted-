import { readBrainStore } from "./brain.store";

export function detectConflicts(signals: any[]) {
  // minimal deterministic conflict rules:
  // If any signal has riskLevel HIGH from COMPLIANCE or CYBER and another signal suggests "increase exposure" => conflict HIGH
  const conflicts: any[] = [];

  const byAgent = (a: string) => signals.filter((s) => s.agent === a);

  const complianceHigh = byAgent("COMPLIANCE").some((s) => s.riskLevel === "HIGH");
  const cyberHigh = byAgent("CYBER").some((s) => s.riskLevel === "HIGH");

  const salesSuggestions = byAgent("SALES").map((s) => (s.insight?.action ? String(s.insight.action) : ""));
  const marketingSuggestions = byAgent("MARKETING").map((s) => (s.insight?.action ? String(s.insight.action) : ""));

  const pushingGrowth = [...salesSuggestions, ...marketingSuggestions].some((a) =>
    ["PRICE_INCREASE", "BUDGET_INCREASE", "SCALE", "EXPAND"].some((k) => a.includes(k))
  );

  if ((complianceHigh || cyberHigh) && pushingGrowth) {
    conflicts.push({
      id: "conflict_risk_vs_growth",
      severity: "HIGH",
      description: "Xavf (Compliance/Cyber HIGH) mavjud, lekin Growth taklifi bor. Avval risk bartaraf bo‘lsin.",
      involved_agents: ["COMPLIANCE", "CYBER", "SALES", "MARKETING"]
    });
  }

  return conflicts;
}

export function priorityScore(signal: any) {
  // priority = risk + money impact (if exists)
  const risk = signal.riskLevel === "HIGH" ? 60 : signal.riskLevel === "MED" ? 35 : 10;
  const money = Number(signal.insight?.estimatedLoss || signal.insight?.lost_profit || 0);
  const moneyScore = money > 0 ? Math.min(40, Math.floor(money / 1_000_000) * 5) : 0;
  return risk + moneyScore;
}

export function enforceProtocol(decision: any) {
  // Master Protocol:
  // - No automatic implementation
  // - Must have reason + impact
  // - Must go Simulation -> Pilot -> Result -> Human Approval
  const errors: string[] = [];

  if (!decision.title) errors.push("TITLE_REQUIRED");
  if (!decision.proposal) errors.push("PROPOSAL_REQUIRED");

  // stage gating
  if (decision.stage === "PILOT" && !decision.simulation) errors.push("SIMULATION_REQUIRED_BEFORE_PILOT");
  if (decision.stage === "RESULT" && !decision.pilot) errors.push("PILOT_REQUIRED_BEFORE_RESULT");
  if (decision.stage === "APPROVAL" && !decision.result) errors.push("RESULT_REQUIRED_BEFORE_APPROVAL");

  return errors;
}

export function suggestFromMemory(proposal: any) {
  // Return any prior lessons that match tags in proposal.action
  const store = readBrainStore();
  const action = String(proposal?.action || "");
  const matches = store.memory.filter((m) => action.includes(m.tag));
  return matches.slice(-5);
}

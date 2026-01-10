import { readStore } from "./tax.store";

function findCitationByLabel(label: string) {
  const s = readStore();
  const c = s.legal_citations.find((x) => x.citation_label === label);
  if (!c) return null;
  const src = s.legal_sources.find((ls) => ls.id === c.legal_source_id);
  if (!src) return null;
  return { citation: c, source: src };
}

/**
 * Legal registry rule convention:
 * legal_sources.metadata_json may contain structured rules
 * Example:
 *  { "rule_key":"VAT_THRESHOLD_12M", "threshold": 1000000000 }
 *  { "rule_key":"PENALTY_LATE_REPORT", "formula":"fixed", "amount":4500000 }
 */
function findRule(rule_key: string) {
  const s = readStore();
  const src = s.legal_sources.find((x) => x.metadata_json?.rule_key === rule_key);
  if (!src) return null;
  return src;
}

export function taxRegimeValidator(input: {
  annualTurnover?: number;
  activityCode?: string;
  employees?: number;
  currentRegime?: string;
}) {
  const rule = findRule("TAX_REGIME_THRESHOLDS");
  if (!rule) {
    return {
      status: "BASIS_MISSING",
      risk_level: "MED",
      note: "Tax regime threshold’lar uchun rasmiy manba registry’da yo‘q.",
      legal_basis: []
    };
  }
  // We do not assume structure; use metadata_json
  const thresholds = rule.metadata_json?.thresholds || [];
  const current = input.currentRegime || "UNKNOWN";
  const turnover = Number(input.annualTurnover || 0);

  const eligible = thresholds.find((t: any) => turnover <= Number(t.max_turnover));
  const suggestion = eligible ? eligible.regime : "UNKNOWN";

  const changed = suggestion !== "UNKNOWN" && current !== "UNKNOWN" && suggestion !== current;

  return {
    status: "OK",
    current,
    suggestion,
    changed,
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };
}

export function vatObligationMonitor(input: { turnover12m?: number }) {
  const rule = findRule("VAT_THRESHOLD_12M");
  if (!rule) {
    return {
      status: "BASIS_MISSING",
      risk_level: "MED",
      note: "VAT threshold rasmiy manbasi registry’da yo‘q.",
      legal_basis: []
    };
  }
  const threshold = Number(rule.metadata_json?.threshold || 0);
  const t12 = Number(input.turnover12m || 0);
  const ratio = threshold > 0 ? t12 / threshold : 0;
  const near = ratio >= 0.85 && ratio < 1;
  const over = ratio >= 1;

  return {
    status: "OK",
    threshold,
    turnover12m: t12,
    near_threshold: near,
    mandatory_now: over,
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };
}

export function penaltyRiskScanner(input: { lateReports?: number; mismatches?: number; missingFields?: number }) {
  const rule = findRule("PENALTY_LATE_REPORT");
  const late = Number(input.lateReports || 0);
  const mism = Number(input.mismatches || 0);
  const miss = Number(input.missingFields || 0);

  const risk = late + mism + miss;
  const risk_level = risk >= 3 ? "HIGH" : risk >= 1 ? "MED" : "LOW";

  if (!rule && risk > 0) {
    return {
      status: "BASIS_MISSING",
      risk_level,
      note: "Penalty formula rasmiy manbasi registry’da yo‘q. Jarima summasi hisoblanmadi.",
      legal_basis: []
    };
  }

  const estimate = rule ? Number(rule.metadata_json?.amount || 0) * late : 0;

  return {
    status: "OK",
    risk_level,
    lateReports: late,
    mismatches: mism,
    missingFields: miss,
    estimatedPenalty: estimate,
    legal_basis: rule ? [{ legal_source_id: rule.id, citation_label: rule.reference_code }] : []
  };
}

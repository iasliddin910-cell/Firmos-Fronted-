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
import { readStore } from "./tax.store";

function findRule(rule_key: string) {
  const s = readStore();
  return s.legal_sources.find((x) => x.metadata_json?.rule_key === rule_key) || null;
}

function basisMissing(note: string) {
  return { status: "BASIS_MISSING", risk_level: "MED", note, legal_basis: [] as any[] };
}

// 4) Overpayment Finder
export function overpaymentFinder(input: { taxType: string; expectedBase?: number }) {
  const s = readStore();

  // rule needed: expected tax formula
  const rule = findRule(`TAX_EXPECTED_${input.taxType.toUpperCase()}`); // e.g. TAX_EXPECTED_INCOME
  if (!rule) return basisMissing(`Expected tax rule yo‘q: TAX_EXPECTED_${input.taxType.toUpperCase()}`);

  // actual payments from store.tax_payments
  const actualPaid = s.tax_payments
    .filter((p) => p.tax_type.toUpperCase() === input.taxType.toUpperCase())
    .reduce((a, p) => a + Number(p.amount || 0), 0);

  const rate = Number(rule.metadata_json?.rate || 0);
  const base = Number(input.expectedBase || 0);
  if (rate <= 0) return basisMissing("Expected tax rate metadata_json.rate yo‘q yoki 0.");

  const expected = base * rate;
  const over = Math.max(0, actualPaid - expected);
  const under = Math.max(0, expected - actualPaid);

  return {
    status: "OK",
    taxType: input.taxType,
    actualPaid,
    expected,
    overpayment: over,
    underpayment: under,
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }],
    assumptions: ["expectedBase foydalanuvchi yoki report manual totals’dan olinadi."]
  };
}

// 5) Expense Deductibility Audit
export function deductibilityAudit(input: { expenses: Array<{ id: string; category: string; amount: number; hasContract?: boolean; hasInvoice?: boolean }> }) {
  const rule = findRule("DEDUCTIBILITY_RULES");
  if (!rule) return basisMissing("Deductibility rules registry’da yo‘q: DEDUCTIBILITY_RULES");

  const rules = rule.metadata_json?.rules || [];
  const issues: any[] = [];

  for (const e of input.expenses || []) {
    const catRule = rules.find((r: any) => (r.category || "").toUpperCase() === String(e.category || "").toUpperCase());
    // default: require contract + invoice
    const requireContract = catRule?.requireContract ?? true;
    const requireInvoice = catRule?.requireInvoice ?? true;
    const deductible = catRule?.deductible ?? true;

    const missing: string[] = [];
    if (requireContract && !e.hasContract) missing.push("MISSING_CONTRACT");
    if (requireInvoice && !e.hasInvoice) missing.push("MISSING_INVOICE");
    if (!deductible) missing.push("CATEGORY_NOT_DEDUCTIBLE");

    if (missing.length) {
      issues.push({
        expenseId: e.id,
        category: e.category,
        amount: e.amount,
        reasons: missing,
        impact_estimate: null
      });
    }
  }

  return {
    status: "OK",
    issues,
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };
}

// 6) VAT Exit Simulation
export function vatExitSimulation(input: { currentVatPaidMonthly?: number; projectedNonVatTaxMonthly?: number }) {
  const rule = findRule("VAT_EXIT_RULES");
  if (!rule) return basisMissing("VAT exit rules registry’da yo‘q: VAT_EXIT_RULES");

  const currentVat = Number(input.currentVatPaidMonthly || 0);
  const projected = Number(input.projectedNonVatTaxMonthly || 0);

  const delta = projected - currentVat;

  return {
    status: "OK",
    currentVatPaidMonthly: currentVat,
    projectedNonVatTaxMonthly: projected,
    estimatedMonthlyTaxChange: delta,
    sideEffects: rule.metadata_json?.side_effects || [],
    note: "Bu simulyatsiya. Qarorni buxgalter bilan tasdiqlang.",
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };
}

// 7) What-if Tax Simulator
export function taxWhatIf(input: { scenario: any }) {
  const rule = findRule("TAX_WHATIF_RULES");
  if (!rule) return basisMissing("What-if rules registry’da yo‘q: TAX_WHATIF_RULES");

  // We keep deterministic: scenario is evaluated by registry mapping table
  const mappings = rule.metadata_json?.mappings || [];
  const key = JSON.stringify(input.scenario || {});
  const match = mappings.find((m: any) => JSON.stringify(m.scenario) === key);

  if (!match) {
    return {
      status: "OK",
      canCompute: false,
      note: "Scenario uchun registry mapping topilmadi. Compute qilinmadi.",
      legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
    };
  }

  return {
    status: "OK",
    canCompute: true,
    scenario: input.scenario,
    estimatedTaxChange: match.estimatedTaxChange,
    assumptions: match.assumptions || [],
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };
}

// 8) Guided Cabinet Access (content-only)
export function cabinetGuidance(topic: string) {
  const s = readStore();
  const tpl = s.cabinet_guidance.find((t) => t.topic === topic);
  if (!tpl) {
    return {
      status: "NOT_FOUND",
      topic,
      steps: [],
      warnings: ["Bu topic uchun guidance template yo‘q. Admin qo‘shishi kerak."],
      note: "Bu faqat yo‘naltirish. Kabinetga login qilinmaydi."
    };
  }
  return {
    status: "OK",
    topic,
    steps: tpl.steps,
    warnings: tpl.warnings,
    note: "Bu faqat yo‘naltirish. Kabinetga login qilinmaydi."
  };
}

// 9) Report Preparation Assistance
export function reportPreparation(input: { documentId: string; reportType: string }) {
  const s = readStore();
  const doc = s.tax_documents.find((d) => d.id === input.documentId);
  if (!doc) return { status: "NOT_FOUND", note: "Document topilmadi." };

  // validation rules registry-based
  const rule = findRule("REPORT_VALIDATION_RULES");
  if (!rule) return basisMissing("Report validation rules registry’da yo‘q: REPORT_VALIDATION_RULES");

  const requiredFields: string[] = rule.metadata_json?.required_fields?.[input.reportType] || [];
  const totals = doc.parsed_json?.manual_totals || doc.parsed_json || {};

  const missing = requiredFields.filter((f) => totals[f] === undefined || totals[f] === null || totals[f] === "");
  const errors = missing.map((m) => ({ field: m, error: "MISSING_REQUIRED_FIELD" }));

  const ready = errors.length === 0;

  const prepared = {
    status: "OK",
    documentId: doc.id,
    reportType: input.reportType,
    validation: {
      ready_to_submit: ready,
      errors
    },
    note: "Hisobot tayyorlash yordamidir. Yuborish / imzo yo‘q.",
    legal_basis: [{ legal_source_id: rule.id, citation_label: rule.reference_code }]
  };

  return prepared;
}

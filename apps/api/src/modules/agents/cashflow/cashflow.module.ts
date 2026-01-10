import type http from "http";
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

// ---- In-memory cash ledger (later: bank/payment integrations) ----
type Tx = {
  id: string;
  date: string; // ISO
  type: "IN" | "OUT";
  amount: number;
  category: string;     // e.g. "SALES", "MARKETING", "PAYROLL", "SUBSCRIPTION"
  vendor?: string;      // for detecting repeating leaks
  note?: string;
};

const txs: Tx[] = [];

function nowIso() {
  return new Date().toISOString();
}

function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function inRange(iso: string, from?: string, to?: string) {
  if (from && iso < from) return false;
  if (to && iso > to) return false;
  return true;
}

function sum(list: Tx[], type?: "IN" | "OUT") {
  return list.reduce((acc, t) => acc + (type ? (t.type === type ? t.amount : 0) : t.amount), 0);
}

function avgMonthly(list: Tx[], type: "IN" | "OUT") {
  // approximate: last 180 days -> 6 months
  const from = daysAgo(180);
  const in6m = list.filter((t) => t.type === type && t.date >= from);
  const total = sum(in6m);
  return total / 6;
}

function computeRunway(list: Tx[]) {
  const avgIn = avgMonthly(list, "IN");
  const avgOut = avgMonthly(list, "OUT");
  const monthlyNet = avgIn - avgOut;

  // current cash: sum(in) - sum(out) all-time (mock)
  const cash = sum(list.filter((t) => t.type === "IN")) - sum(list.filter((t) => t.type === "OUT"));

  const burn = Math.max(0, -monthlyNet) || (avgOut > avgIn ? (avgOut - avgIn) : 0);
  const days = burn > 0 ? (cash / burn) * 30 : 9999;

  return {
    cashNow: cash,
    avgMonthlyIn: avgIn,
    avgMonthlyOut: avgOut,
    monthlyNet,
    runwayDays: Math.max(0, Math.floor(days))
  };
}

function computeDailyCashStress(list: Tx[]) {
  const today = new Date().toISOString().slice(0, 10);
  const todayTx = list.filter((t) => t.date.slice(0, 10) === today);
  const todayIn = sum(todayTx.filter((t) => t.type === "IN"));
  const todayOut = sum(todayTx.filter((t) => t.type === "OUT"));

  return {
    date: today,
    todayIn,
    todayOut,
    net: todayIn - todayOut,
    stress: todayIn - todayOut < 0 ? "HIGH" : "LOW"
  };
}

function computeExpenseDrain(list: Tx[]) {
  // expensive categories where OUT is high but IN is not tied (mock)
  const outs = list.filter((t) => t.type === "OUT");
  const byCat = outs.reduce<Record<string, number>>((acc, t) => {
    acc[t.category] = (acc[t.category] || 0) + t.amount;
    return acc;
  }, {});
  const ranked = Object.entries(byCat)
    .map(([category, out]) => ({ category, out }))
    .sort((a, b) => b.out - a.out)
    .slice(0, 10);

  return ranked.map((r) => ({
    category: r.category,
    out: r.out,
    note: "Natija (ROI) mapping hozircha cheklangan. Marketing/Sales mapping qo‘shilganda aniqlash kuchayadi."
  }));
}

function computeHiddenCashLeak(list: Tx[]) {
  // find repeating small vendor payments
  const outs = list.filter((t) => t.type === "OUT" && t.amount > 0);
  const byVendor = outs.reduce<Record<string, { count: number; total: number; sampleAmount: number }>>((acc, t) => {
    const v = t.vendor || t.category || "UNKNOWN";
    if (!acc[v]) acc[v] = { count: 0, total: 0, sampleAmount: t.amount };
    acc[v].count += 1;
    acc[v].total += t.amount;
    return acc;
  }, {});

  return Object.entries(byVendor)
    .filter(([_, v]) => v.count >= 3 && v.sampleAmount <= 500000)
    .map(([vendor, v]) => ({
      vendor,
      count: v.count,
      total: v.total,
      note: "Mayda takroriy to‘lovlar (hidden leak ehtimoli)."
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);
}

function computeForwardRisk(list: Tx[]) {
  const runway = computeRunway(list);
  const risk60 = runway.runwayDays <= 60 ? "HIGH" : runway.runwayDays <= 120 ? "MED" : "LOW";
  const risk30 = runway.runwayDays <= 30 ? "HIGH" : runway.runwayDays <= 60 ? "MED" : "LOW";
  const risk90 = runway.runwayDays <= 90 ? "HIGH" : runway.runwayDays <= 150 ? "MED" : "LOW";

  return {
    risk30,
    risk60,
    risk90,
    note: "Forward risk hozirgi burn-rate asosida hisoblandi (simulyatsiya emas, prognoz)."
  };
}

function computeCashflowInsights(from?: string, to?: string) {
  const inTf = txs.filter((t) => inRange(t.date, from, to));
  const runway = computeRunway(txs); // runway uses last 6 months overall
  const daily = computeDailyCashStress(txs);
  const drain = computeExpenseDrain(inTf.length ? inTf : txs);
  const leak = computeHiddenCashLeak(txs);
  const forward = computeForwardRisk(txs);

  return {
    runway,
    dailyCashStress: daily,
    expenseDrain: drain,
    hiddenCashLeak: leak,
    forwardRisk: forward
  };
}

export function registerCashflow(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  // mock tx ingestion
  register("POST", "/api/v1/agents/cashflow/mock/tx", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<Tx> | undefined;
    if (!body?.type || !body?.amount || !body?.category) return json(res, 400, { error: "BAD_REQUEST" });

    const t: Tx = {
      id: uuid("tx"),
      date: body.date || nowIso(),
      type: body.type as any,
      amount: Number(body.amount),
      category: String(body.category),
      vendor: body.vendor ? String(body.vendor) : undefined,
      note: body.note ? String(body.note) : undefined
    };

    txs.push(t);
    return json(res, 200, { ok: true, tx: t });
  });

  register("GET", "/api/v1/agents/cashflow/insights", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");
    const data = computeCashflowInsights(from || undefined, to || undefined);
    return json(res, 200, data);
  });

  register("POST", "/api/v1/agents/cashflow/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");

    const data = computeCashflowInsights(from || undefined, to || undefined);

    const riskLevel =
      data.runway.runwayDays <= 30 ? "HIGH" : data.runway.runwayDays <= 90 ? "MED" : "LOW";

    const signal: AgentSignal<any> = {
      id: uuid("sig_cash"),
      agent: "CASHFLOW",
      createdAt: nowIso(),
      timeframe: { from: from || nowIso(), to: to || nowIso() },
      title: "Cashflow: runway, cash stress, leak va forward risk",
      summary: `Runway: ${data.runway.runwayDays} kun. Bugungi net: ${data.dailyCashStress.net}. Leak topildi: ${data.hiddenCashLeak.length}.`,
      riskLevel,
      confidence: 0.6,
      assumptions: [
        "CashNow = all-time IN - all-time OUT (mock ledger).",
        "Runway 6 oylik o‘rtacha asosida.",
        "Leak detekti vendor/category repetition asosida."
      ],
      insight: data,
      evidence: [{ source: "cash:mock-ledger" }],
      legalBasis: [],
      advisoryNote: "Bu tahlil maslahat xarakterida. Pul oqimi bo‘yicha qarorlarni buxgalter/CFO bilan tasdiqlang."
    };

    pushSignal(signal);
    return json(res, 200, { ok: true, signalId: signal.id });
  });
}

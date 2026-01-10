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

// ----- Minimal in-memory data stores (later: DB/integrations) -----
type Order = {
  id: string;
  createdAt: string; // ISO
  channel: "TELEGRAM" | "WEBSITE" | "APP" | "MARKETPLACE";
  status: "CREATED" | "PAID" | "CANCELLED" | "DELIVERED" | "FAILED";
  amount: number; // gross
  estCost: number; // estimated cost (for net profit)
  prepaid: boolean;
  customerId: string;
};

type Complaint = {
  id: string;
  createdAt: string;
  channel: "TELEGRAM" | "WEBSITE" | "APP" | "MARKETPLACE";
  topic: "DELIVERY_DELAY" | "PRICE_HIGH" | "NO_RESPONSE" | "QUALITY" | "OTHER";
  text: string;
  customerId?: string;
};

const orders: Order[] = [];
const complaints: Complaint[] = [];

// helper
function nowIso() {
  return new Date().toISOString();
}

function sumNet(ordersList: Order[]) {
  return ordersList.reduce((acc, o) => acc + (o.amount - o.estCost), 0);
}

function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function inRange(iso: string, from?: string, to?: string) {
  if (from && iso < from) return false;
  if (to && iso > to) return false;
  return true;
}

// ----- Sales computations (per spec) -----

function computeLossIntelligence(from?: string, to?: string) {
  const inTf = orders.filter((o) => inRange(o.createdAt, from, to));

  const cancelled = inTf.filter((o) => o.status === "CANCELLED");
  const unpaid = inTf.filter((o) => o.status === "CREATED" && !o.prepaid);
  const failed = inTf.filter((o) => o.status === "FAILED");

  const lostNet = sumNet([...cancelled, ...unpaid, ...failed]);

  // Funnel drop is mocked: we approximate from unpaid created orders
  const checkoutDropCount = unpaid.length;
  const checkoutPotentialLoss = sumNet(unpaid);

  // Channel loss: net profit per channel
  const byChannel = ["TELEGRAM", "WEBSITE", "APP", "MARKETPLACE"].map((ch) => {
    const chOrders = inTf.filter((o) => o.channel === ch);
    const net = sumNet(chOrders);
    const cancelledRate = chOrders.length ? chOrders.filter((o) => o.status === "CANCELLED").length / chOrders.length : 0;
    return { channel: ch, orders: chOrders.length, netProfit: net, cancelledRate };
  });

  // Complaints impact (simple mapping)
  const compInTf = complaints.filter((c) => inRange(c.createdAt, from, to));
  const complaintTopics = compInTf.reduce<Record<string, number>>((acc, c) => {
    acc[c.topic] = (acc[c.topic] || 0) + 1;
    return acc;
  }, {});

  // Loss estimate from complaints: deterministic heuristic (not a decision)
  const complaintLossEst = compInTf.length * 20000; // placeholder currency unit
  const complaintNote =
    compInTf.length === 0
      ? "Shikoyat kuzatilmadi."
      : "Shikoyatlar soni sotuv bosqichlarida chiqib ketish ehtimolini oshiradi (taxminiy baho).";

  return {
    lostNet,
    cancelledCount: cancelled.length,
    unpaidCount: unpaid.length,
    failedCount: failed.length,
    checkoutDropCount,
    checkoutPotentialLoss,
    byChannel,
    complaintsCount: compInTf.length,
    complaintTopics,
    complaintLossEst,
    complaintNote
  };
}

function computeProfitDiscovery(from?: string, to?: string) {
  const inTf = orders.filter((o) => inRange(o.createdAt, from, to));
  // Find best customers: high net, low complaints
  const netByCustomer = inTf.reduce<Record<string, number>>((acc, o) => {
    acc[o.customerId] = (acc[o.customerId] || 0) + (o.amount - o.estCost);
    return acc;
  }, {});
  const complaintByCustomer = complaints.reduce<Record<string, number>>((acc, c) => {
    if (c.customerId) acc[c.customerId] = (acc[c.customerId] || 0) + 1;
    return acc;
  }, {});
  const topCustomers = Object.entries(netByCustomer)
    .map(([customerId, net]) => ({ customerId, net, complaints: complaintByCustomer[customerId] || 0 }))
    .sort((a, b) => b.net - a.net)
    .slice(0, 10);

  // Time & profit (hourly)
  const hourly = Array.from({ length: 24 }).map((_, hour) => {
    const hOrders = inTf.filter((o) => new Date(o.createdAt).getHours() === hour);
    return { hour, orders: hOrders.length, netProfit: sumNet(hOrders) };
  });
  const bestHour = hourly.slice().sort((a, b) => b.netProfit - a.netProfit)[0];

  return {
    topCustomers,
    bestHour,
    hourly
  };
}

// ----- Register module routes -----
export function registerSales(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  // Seed/demo data endpoints (operator-only later). For now, protected by headers.
  register("POST", "/api/v1/agents/sales/mock/orders", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<Order> | undefined;
    if (!body?.amount || !body?.estCost || !body?.channel || !body?.customerId) return json(res, 400, { error: "BAD_REQUEST" });

    const o: Order = {
      id: uuid("ord"),
      createdAt: body.createdAt || nowIso(),
      channel: body.channel as any,
      status: (body.status as any) || "CREATED",
      amount: Number(body.amount),
      estCost: Number(body.estCost),
      prepaid: Boolean(body.prepaid),
      customerId: String(body.customerId)
    };
    orders.push(o);
    return json(res, 200, { ok: true, order: o });
  });

  register("POST", "/api/v1/agents/sales/mock/complaints", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<Complaint> | undefined;
    if (!body?.channel || !body?.topic || !body?.text) return json(res, 400, { error: "BAD_REQUEST" });

    const c: Complaint = {
      id: uuid("cmp"),
      createdAt: body.createdAt || nowIso(),
      channel: body.channel as any,
      topic: body.topic as any,
      text: String(body.text),
      customerId: body.customerId ? String(body.customerId) : undefined
    };
    complaints.push(c);
    return json(res, 200, { ok: true, complaint: c });
  });

  // Insights endpoints (per spec: loss + profit discovery)
  register("GET", "/api/v1/agents/sales/insights/loss", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");
    const data = computeLossIntelligence(from || undefined, to || undefined);
    return json(res, 200, data);
  });

  register("GET", "/api/v1/agents/sales/insights/profit", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");
    const data = computeProfitDiscovery(from || undefined, to || undefined);
    return json(res, 200, data);
  });

  // Signal emitter: Sales Agent produces canonical AgentSignal
  register("POST", "/api/v1/agents/sales/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");

    const loss = computeLossIntelligence(from || undefined, to || undefined);

    const signal: AgentSignal<any> = {
      id: uuid("sig_sales"),
      agent: "SALES",
      createdAt: nowIso(),
      timeframe: { from: from || nowIso(), to: to || nowIso() },
      title: "Sales: Yo‘qotilgan foyda va shikoyat ta’siri",
      summary: `Yo‘qotilgan sof foyda (taxminiy): ${loss.lostNet.toFixed(0)}. Checkout drop: ${loss.checkoutDropCount}. Shikoyatlar: ${loss.complaintsCount}.`,
      riskLevel: loss.lostNet > 0 ? "MED" : "LOW",
      confidence: 0.55,
      assumptions: [
        "Sof foyda amount - estCost bo‘yicha taxminiy hisoblangan",
        "Shikoyat → yo‘qotish bog‘lanishi hozircha deterministik heuristika"
      ],
      insight: loss,
      evidence: [
        { source: "orders:mock-store" },
        { source: "complaints:mock-store" }
      ],
      legalBasis: [],
      advisoryNote: "Bu tahlil maslahat xarakterida. Qaror qabul qilishdan oldin ichki ma’lumotlar va jarayonlar bilan tasdiqlang."
    };

    pushSignal(signal);
    return json(res, 200, { ok: true, signalId: signal.id });
  });
}

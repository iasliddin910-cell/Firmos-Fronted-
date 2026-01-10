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

// ---- Security events (mock logs) ----
type LoginEvent = {
  id: string;
  at: string;
  ip: string;
  country?: string;
  success: boolean;
  actor?: string;
};

type ApiEvent = {
  id: string;
  at: string;
  ip: string;
  path: string;
  status: number;
  bytesOut?: number;
};

type InfraSnapshot = {
  id: string;
  at: string;
  cpu: number; // 0..100
  ram: number; // 0..100
  errorRate: number; // 0..1
  downtimeMinutes?: number;
};

type PaymentEvent = {
  id: string;
  at: string;
  provider: string;
  type: "WEBHOOK" | "REFUND" | "CANCEL";
  suspicious: boolean;
  note?: string;
};

const loginEvents: LoginEvent[] = [];
const apiEvents: ApiEvent[] = [];
const infra: InfraSnapshot[] = [];
const paymentEvents: PaymentEvent[] = [];

let incidentMode = false; // manual switch by owner/admin

function nowIso() {
  return new Date().toISOString();
}

function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function lastN<T>(arr: T[], n: number) {
  return arr.slice(Math.max(0, arr.length - n));
}

// ---- Detection rules (deterministic) ----
function anomalousLoginDetection() {
  const recent = lastN(loginEvents, 200);
  const failed = recent.filter((e) => !e.success);
  const suspiciousCountry = recent.filter((e) => (e.country || "").toLowerCase() === "other").length;
  const bruteForce = failed.length >= 10;

  return {
    bruteForce,
    failedCount: failed.length,
    suspiciousCountryCount: suspiciousCountry,
    note: bruteForce
      ? "Ketma-ket ko‘p login urinish (brute-force ehtimoli)."
      : "Login holati normal yoki signal past."
  };
}

function botTrafficDetection() {
  const recent = lastN(apiEvents, 500);
  const byIp = recent.reduce<Record<string, number>>((acc, e) => {
    acc[e.ip] = (acc[e.ip] || 0) + 1;
    return acc;
  }, {});
  const noisy = Object.entries(byIp).filter(([_, c]) => c >= 200).map(([ip, c]) => ({ ip, count: c }));
  return {
    noisyIps: noisy,
    suspectedBot: noisy.length > 0,
    note: noisy.length > 0 ? "Bir nechta IP’dan juda ko‘p so‘rov (bot trafik ehtimoli)." : "Bot trafik aniqlanmadi."
  };
}

function infraHealthMonitor() {
  const last = infra[infra.length - 1];
  if (!last) return { score: 100, note: "Infra snapshot yo‘q." };

  // score down by cpu/ram/errorRate
  const score = Math.max(0, Math.floor(100 - last.cpu * 0.4 - last.ram * 0.4 - last.errorRate * 100));
  return {
    score,
    cpu: last.cpu,
    ram: last.ram,
    errorRate: last.errorRate,
    downtimeMinutes: last.downtimeMinutes || 0
  };
}

function downtimeMoneyImpact() {
  const last = infra[infra.length - 1];
  const downtime = last?.downtimeMinutes || 0;
  // deterministic: 18,000 per minute
  const loss = downtime * 18000;
  return {
    downtimeMinutes: downtime,
    estimatedLoss: loss,
    note: "Bu taxminiy baho. Real revenue rate bilan moslashtirish kerak."
  };
}

function dataLeakRisk() {
  const recent = lastN(apiEvents, 500);
  const bytesSum = recent.reduce((acc, e) => acc + (e.bytesOut || 0), 0);
  // threshold: >50MB in recent window is suspicious
  const suspicious = bytesSum > 50 * 1024 * 1024;

  return {
    suspicious,
    bytesOut: bytesSum,
    note: suspicious ? "Katta hajmda outbound traffic (data export/leak ehtimoli)." : "Data leak signal yo‘q."
  };
}

function paymentAbuseDetection() {
  const recent = lastN(paymentEvents, 200);
  const suspicious = recent.filter((e) => e.suspicious);
  return {
    suspiciousCount: suspicious.length,
    suspiciousItems: suspicious.slice(-20),
    note: suspicious.length ? "To‘lovlarda shubhali hodisalar bor." : "To‘lovlar normal."
  };
}

function recurringRisks() {
  const recent = lastN(loginEvents, 500);
  const byIp = recent.reduce<Record<string, number>>((acc, e) => {
    acc[e.ip] = (acc[e.ip] || 0) + 1;
    return acc;
  }, {});
  const recurring = Object.entries(byIp).filter(([_, c]) => c >= 3).map(([ip, c]) => ({ ip, count: c }));
  return recurring.slice(0, 20);
}

function riskScoreCompute(det: any) {
  let score = 0;
  if (det.login.bruteForce) score += 25;
  if (det.bot.suspectedBot) score += 20;
  if (det.dataLeak.suspicious) score += 35;
  if (det.payment.suspiciousCount > 0) score += 15;
  if (det.infra.score < 60) score += 20;
  return Math.min(100, score);
}

function computeCyberInsights() {
  const login = anomalousLoginDetection();
  const bot = botTrafficDetection();
  const infraState = infraHealthMonitor();
  const downtime = downtimeMoneyImpact();
  const leak = dataLeakRisk();
  const payment = paymentAbuseDetection();
  const recurring = recurringRisks();
  const riskScore = riskScoreCompute({ login, bot, infra: infraState, dataLeak: leak, payment });

  return {
    incidentMode,
    login,
    bot,
    infra: infraState,
    downtimeImpact: downtime,
    dataLeak: leak,
    payment,
    recurringRisks: recurring,
    securityRiskScore: riskScore
  };
}

// ---- Register module routes ----
export function registerCyber(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  // toggle incident mode (owner/admin in future; now header-protected)
  register("POST", "/api/v1/agents/cyber/incident-mode", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as { enabled?: boolean } | undefined;
    incidentMode = Boolean(body?.enabled);
    return json(res, 200, { ok: true, incidentMode });
  });

  // mock inputs
  register("POST", "/api/v1/agents/cyber/mock/login", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<LoginEvent> | undefined;
    if (!body?.ip || typeof body.success !== "boolean") return json(res, 400, { error: "BAD_REQUEST" });

    const e: LoginEvent = {
      id: uuid("login"),
      at: body.at || nowIso(),
      ip: String(body.ip),
      country: body.country ? String(body.country) : undefined,
      success: Boolean(body.success),
      actor: body.actor ? String(body.actor) : undefined
    };
    loginEvents.push(e);
    return json(res, 200, { ok: true, event: e });
  });

  register("POST", "/api/v1/agents/cyber/mock/api", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<ApiEvent> | undefined;
    if (!body?.ip || !body?.path || typeof body.status !== "number") return json(res, 400, { error: "BAD_REQUEST" });

    const e: ApiEvent = {
      id: uuid("api"),
      at: body.at || nowIso(),
      ip: String(body.ip),
      path: String(body.path),
      status: Number(body.status),
      bytesOut: body.bytesOut ? Number(body.bytesOut) : 0
    };
    apiEvents.push(e);
    return json(res, 200, { ok: true, event: e });
  });

  register("POST", "/api/v1/agents/cyber/mock/infra", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<InfraSnapshot> | undefined;
    if (typeof body?.cpu !== "number" || typeof body?.ram !== "number" || typeof body?.errorRate !== "number")
      return json(res, 400, { error: "BAD_REQUEST" });

    const s: InfraSnapshot = {
      id: uuid("infra"),
      at: body.at || nowIso(),
      cpu: Number(body.cpu),
      ram: Number(body.ram),
      errorRate: Number(body.errorRate),
      downtimeMinutes: body.downtimeMinutes ? Number(body.downtimeMinutes) : 0
    };
    infra.push(s);
    return json(res, 200, { ok: true, snapshot: s });
  });

  register("POST", "/api/v1/agents/cyber/mock/payment", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<PaymentEvent> | undefined;
    if (!body?.provider || !body?.type || typeof body.suspicious !== "boolean") return json(res, 400, { error: "BAD_REQUEST" });

    const e: PaymentEvent = {
      id: uuid("pay"),
      at: body.at || nowIso(),
      provider: String(body.provider),
      type: body.type as any,
      suspicious: Boolean(body.suspicious),
      note: body.note ? String(body.note) : undefined
    };
    paymentEvents.push(e);
    return json(res, 200, { ok: true, event: e });
  });

  // insights
  register("GET", "/api/v1/agents/cyber/insights", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const data = computeCyberInsights();
    return json(res, 200, data);
  });

  // run => emit signal
  register("POST", "/api/v1/agents/cyber/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const data = computeCyberInsights();
    const riskLevel = data.securityRiskScore >= 70 ? "HIGH" : data.securityRiskScore >= 40 ? "MED" : "LOW";

    const baseSignal: AgentSignal<any> = {
      id: uuid("sig_cyber"),
      agent: "CYBER",
      createdAt: nowIso(),
      timeframe: { from: nowIso(), to: nowIso() },
      title: "Cybersecurity: login/bot/infra/data leak/payment risk",
      summary: `Risk score: ${data.securityRiskScore}/100. Leak suspicious: ${data.dataLeak.suspicious}. Bot: ${data.bot.suspectedBot}.`,
      riskLevel,
      confidence: 0.65,
      assumptions: [
        "Deteksiyalar deterministik thresholdlar asosida (mock logs).",
        "Data leak bytesOut summasi bilan taxmin qilinadi."
      ],
      insight: data,
      evidence: [
        { source: "logs:mock-login" },
        { source: "logs:mock-api" },
        { source: "infra:mock-snapshots" },
        { source: "payments:mock-events" }
      ],
      legalBasis: [],
      advisoryNote: "Bu tahlil maslahat xarakterida. Xavf yuqori bo‘lsa, darhol texnik jamoa bilan incident protsedura ishga tushiring."
    };

    pushSignal(baseSignal);

    // ISTISNO: data leak + incident mode => shutdown request signal (NOT automatic shutdown)
    if (incidentMode && data.dataLeak.suspicious) {
      const shutdownReq: AgentSignal<any> = {
        id: uuid("sig_shutdown_req"),
        agent: "CYBER",
        createdAt: nowIso(),
        timeframe: { from: nowIso(), to: nowIso() },
        title: "ISTISNO: Data leak HIGH — shutdown request",
        summary: "Incident mode ON va data leak suspicious. Serverni o‘chirish bo‘yicha tasdiq talab qilinadi (request).",
        riskLevel: "HIGH",
        confidence: 0.7,
        assumptions: ["Bu signal avtomatik shutdown emas; faqat tezkor harakat uchun request."],
        insight: { action: "SHUTDOWN_REQUEST", reason: "DATA_LEAK_SUSPICIOUS", bytesOut: data.dataLeak.bytesOut },
        evidence: [{ source: "cyber:dataLeak" }],
        legalBasis: [],
        advisoryNote: "Owner/Company Brain tasdig‘isiz avtomatik o‘chirish amalga oshirilmaydi. Bu request tezkor incident uchun."
      };
      pushSignal(shutdownReq);
    }

    return json(res, 200, { ok: true });
  });
}

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

// ---- Mock ad/campaign data store (later: Meta/Google/TikTok connectors) ----
type Campaign = {
  id: string;
  createdAt: string;
  platform: "META" | "GOOGLE" | "TIKTOK";
  name: string;
  spend: number;
  clicks: number;
  leads: number;
  paidCustomers: number;
  netProfitFromSales: number; // from Sales Agent mapped conversions (mock)
  landingBounceRate: number;  // 0..1
  avgSessionSeconds: number;
  ctr: number;                // 0..1
};

const campaigns: Campaign[] = [];

function nowIso() {
  return new Date().toISOString();
}

function uuid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function inRange(iso: string, from?: string, to?: string) {
  if (from && iso < from) return false;
  if (to && iso > to) return false;
  return true;
}

// ---- Marketing computations (per spec) ----
function computeROI(c: Campaign) {
  // "Real ROI": netProfitFromSales vs spend
  if (c.spend <= 0) return 0;
  return (c.netProfitFromSales - c.spend) / c.spend;
}

function detectHarmfulCampaigns(list: Campaign[]) {
  // clicks/leads exist but no paid customers => harmful
  return list
    .filter((c) => c.clicks > 0 && c.leads > 0 && c.paidCustomers === 0)
    .map((c) => ({
      campaignId: c.id,
      name: c.name,
      reason: "Klik va lead bor, lekin to‘lov yo‘q (zararli kampaniya ehtimoli).",
      spend: c.spend
    }));
}

function detectFakeLeads(list: Campaign[]) {
  // avg session 5-10 sec, 1 page => we approximate via avgSessionSeconds
  return list
    .filter((c) => c.leads > 0 && c.avgSessionSeconds <= 10)
    .map((c) => ({
      campaignId: c.id,
      name: c.name,
      reason: "Leadlar juda qisqa sessiya bilan kelgan (fake lead ehtimoli).",
      avgSessionSeconds: c.avgSessionSeconds
    }));
}

function detectLandingIssues(list: Campaign[]) {
  return list
    .filter((c) => c.landingBounceRate >= 0.7)
    .map((c) => ({
      campaignId: c.id,
      name: c.name,
      reason: "Landing bounce yuqori (landing muammo ehtimoli).",
      bounceRate: c.landingBounceRate
    }));
}

function detectAdFatigue(list: Campaign[]) {
  // crude: ctr < 1% indicates fatigue
  return list
    .filter((c) => c.ctr < 0.01 && c.spend > 0)
    .map((c) => ({
      campaignId: c.id,
      name: c.name,
      reason: "CTR past (reklama charchashi ehtimoli).",
      ctr: c.ctr
    }));
}

function findPayingAudience(list: Campaign[]) {
  // mocked "best segment" from top ROI campaign
  const best = list.slice().sort((a, b) => computeROI(b) - computeROI(a))[0];
  if (!best) return null;
  return {
    segmentLabel: "31–40 yosh, iOS, Instagram (mock)",
    basedOnCampaign: best.name,
    roi: computeROI(best)
  };
}

function budgetReallocationSim(list: Campaign[]) {
  // Move budget from worst ROI to best ROI
  if (list.length < 2) return null;
  const sorted = list.slice().sort((a, b) => computeROI(a) - computeROI(b));
  const worst = sorted[0];
  const best = sorted[sorted.length - 1];

  const move = Math.min(3000000, worst.spend); // "3 mln"
  const bestROI = computeROI(best);
  // estimate profit change = move * (bestROI - worstROI)
  const delta = move * (computeROI(best) - computeROI(worst));
  return {
    fromCampaign: worst.name,
    toCampaign: best.name,
    moveBudget: move,
    estNetProfitChange: delta,
    note: "Bu simulyatsiya. Buyruq emas."
  };
}

function computeMarketingInsights(from?: string, to?: string) {
  const inTf = campaigns.filter((c) => inRange(c.createdAt, from, to));

  const roiTable = inTf.map((c) => ({
    campaignId: c.id,
    platform: c.platform,
    name: c.name,
    spend: c.spend,
    netProfitFromSales: c.netProfitFromSales,
    realROI: computeROI(c)
  }));

  return {
    roiTable,
    harmfulCampaigns: detectHarmfulCampaigns(inTf),
    fakeLeads: detectFakeLeads(inTf),
    landingIssues: detectLandingIssues(inTf),
    adFatigue: detectAdFatigue(inTf),
    payingAudience: findPayingAudience(inTf),
    budgetSim: budgetReallocationSim(inTf)
  };
}

// ---- Register module routes ----
export function registerMarketing(register: RegisterRoute, pushSignal: (s: AgentSignal<any>) => void) {
  register("POST", "/api/v1/agents/marketing/mock/campaigns", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const body = (req as any).body as Partial<Campaign> | undefined;
    if (!body?.platform || !body?.name) return json(res, 400, { error: "BAD_REQUEST" });

    const c: Campaign = {
      id: uuid("cmpg"),
      createdAt: body.createdAt || nowIso(),
      platform: body.platform as any,
      name: String(body.name),
      spend: Number(body.spend || 0),
      clicks: Number(body.clicks || 0),
      leads: Number(body.leads || 0),
      paidCustomers: Number(body.paidCustomers || 0),
      netProfitFromSales: Number(body.netProfitFromSales || 0),
      landingBounceRate: Number(body.landingBounceRate || 0),
      avgSessionSeconds: Number(body.avgSessionSeconds || 0),
      ctr: Number(body.ctr || 0)
    };

    campaigns.push(c);
    return json(res, 200, { ok: true, campaign: c });
  });

  register("GET", "/api/v1/agents/marketing/insights", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");
    const data = computeMarketingInsights(from || undefined, to || undefined);
    return json(res, 200, data);
  });

  register("POST", "/api/v1/agents/marketing/run", (req, res) => {
    const auth = requireAuth(req);
    if (!auth) return json(res, 401, { error: "UNAUTHORIZED" });

    const q = (req as any).query || {};
    const from = String(q.from || "");
    const to = String(q.to || "");

    const data = computeMarketingInsights(from || undefined, to || undefined);

    const harmfulSpend = data.harmfulCampaigns.reduce((acc: number, x: any) => acc + Number(x.spend || 0), 0);
    const riskLevel = harmfulSpend > 0 ? "MED" : "LOW";

    const signal: AgentSignal<any> = {
      id: uuid("sig_mkt"),
      agent: "MARKETING",
      createdAt: nowIso(),
      timeframe: { from: from || nowIso(), to: to || nowIso() },
      title: "Marketing: ROI, zararli kampaniya va landing muammolari",
      summary: `Zararli kampaniya: ${data.harmfulCampaigns.length}. Fake lead: ${data.fakeLeads.length}. Landing issue: ${data.landingIssues.length}.`,
      riskLevel,
      confidence: 0.55,
      assumptions: [
        "ROI netProfitFromSales va spend asosida hisoblandi (mock mapping).",
        "Fake lead/landing/ad fatigue qoidalari hozircha deterministik thresholdlar."
      ],
      insight: data,
      evidence: [{ source: "ads:mock-campaign-store" }],
      legalBasis: [],
      advisoryNote: "Bu tahlil maslahat xarakterida. Byudjetni o‘zgartirishdan oldin real tracking va sotuv mapping bilan tasdiqlang."
    };

    pushSignal(signal);
    return json(res, 200, { ok: true, signalId: signal.id });
  });
}

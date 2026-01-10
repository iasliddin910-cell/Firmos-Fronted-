"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function MarketingPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function refresh() {
    setErr("");
    try {
      const r = await apiGet<any>("/api/v1/agents/marketing/insights");
      setData(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function seedDemo() {
    setErr("");
    try {
      // best ROI campaign
      await apiPost("/api/v1/agents/marketing/mock/campaigns", {
        platform: "META",
        name: "META iOS 31-40",
        spend: 5000000,
        clicks: 1200,
        leads: 80,
        paidCustomers: 25,
        netProfitFromSales: 9000000,
        landingBounceRate: 0.35,
        avgSessionSeconds: 55,
        ctr: 0.015
      });

      // harmful campaign
      await apiPost("/api/v1/agents/marketing/mock/campaigns", {
        platform: "GOOGLE",
        name: "Search broad (no buyers)",
        spend: 3000000,
        clicks: 900,
        leads: 40,
        paidCustomers: 0,
        netProfitFromSales: 0,
        landingBounceRate: 0.75,
        avgSessionSeconds: 8,
        ctr: 0.008
      });

      // fatigue campaign
      await apiPost("/api/v1/agents/marketing/mock/campaigns", {
        platform: "TIKTOK",
        name: "TikTok old creative",
        spend: 2000000,
        clicks: 400,
        leads: 20,
        paidCustomers: 3,
        netProfitFromSales: 1500000,
        landingBounceRate: 0.6,
        avgSessionSeconds: 18,
        ctr: 0.005
      });

      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function runAgent() {
    setErr("");
    try {
      await apiPost("/api/v1/agents/marketing/run", {});
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Marketing Agent">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={seedDemo}>Demo kampaniyalar qo‘shish</button>
        <button onClick={runAgent}>Marketing Agent’ni ishga tushirish (signal)</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Insights</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Eslatma</div>
        <p>“Run” qilinsa signal yaratiladi va Overview + Company Brain’da ko‘rinadi.</p>
      </section>
    </Page>
  );
}

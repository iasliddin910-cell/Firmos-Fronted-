"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function CompliancePage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function refresh() {
    setErr("");
    try {
      const r = await apiGet<any>("/api/v1/agents/compliance/insights");
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
      await apiPost("/api/v1/agents/compliance/mock/source", {
        publisher: "LEX_UZ",
        title: "Yangi normativ hujjat (mock)",
        ref: "lex.uz/doc/XXXXX",
        effectiveFrom: daysFromNowIso(20),
        tags: ["LAW_CHANGE"]
      });

      await apiPost("/api/v1/agents/compliance/mock/deadline", {
        title: "Litsenziya muddati tugaydi",
        dueDate: daysFromNowIso(18),
        severity: "HIGH",
        note: "Kechiksa faoliyat to‘xtashi mumkin."
      });

      await apiPost("/api/v1/agents/compliance/mock/conflict", {
        agents: ["MARKETING", "COMPLIANCE"],
        topic: "DISCOUNT_POLICY",
        note: "Chegirma bo‘yicha cheklovlar ehtimoli. Rasmiy asos bilan solishtirish kerak."
      });

      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function runAgent() {
    setErr("");
    try {
      await apiPost("/api/v1/agents/compliance/run", {});
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Compliance Agent">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={seedDemo}>Demo rasmiy manba + deadline + conflict</button>
        <button onClick={runAgent}>Compliance Agent’ni ishga tushirish (signal)</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Insights (official-only)</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Eslatma</div>
        <p>Compliance faqat ogohlantiradi va rasmiy manba bo‘lmasa “UNKNOWN” qaytaradi. Qaror yuristda.</p>
      </section>
    </Page>
  );
}

function daysFromNowIso(n: number) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString();
}

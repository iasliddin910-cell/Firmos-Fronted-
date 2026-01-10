"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function CompanyBrainPage() {
  const [err, setErr] = useState("");
  const [priority, setPriority] = useState<any>(null);
  const [council, setCouncil] = useState<any>(null);
  const [decisions, setDecisions] = useState<any>(null);

  const [title, setTitle] = useState("Narxni +5% oshirish (pilot)");
  const [proposal, setProposal] = useState<any>({
    agent: "SALES",
    action: "PRICE_INCREASE_5",
    expected_effect: "+8%"
  });

  async function refreshAll() {
    setErr("");
    try {
      const p = await apiGet("/api/v1/company-brain/priority");
      const c = await apiGet("/api/v1/company-brain/council");
      const d = await apiGet("/api/v1/company-brain/decisions");
      setPriority(p);
      setCouncil(c);
      setDecisions(d);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    refreshAll().catch(() => {});
  }, []);

  async function createDecision() {
    setErr("");
    try {
      await apiPost("/api/v1/company-brain/decisions", { title, proposal });
      await refreshAll();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Company Brain">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={refreshAll}>Refresh</button>
      </div>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Create Decision (Simulation stage)</div>

        <div style={{ display: "grid", gap: 8, maxWidth: 700 }}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>

          <label>
            Proposal (JSON)
            <textarea
              value={JSON.stringify(proposal, null, 2)}
              onChange={(e) => {
                try {
                  setProposal(JSON.parse(e.target.value));
                } catch {}
              }}
              rows={6}
            />
          </label>

          <button onClick={createDecision}>Create decision</button>
        </div>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Priority Queue</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{priority ? JSON.stringify(priority, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Council (Conflicts)</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{council ? JSON.stringify(council, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Decisions</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{decisions ? JSON.stringify(decisions, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Master Protocol eslatma</div>
        <ul>
          <li>Hech qachon avtomatik implementatsiya yo‘q.</li>
          <li>Simulyatsiya → Pilot → Result → Owner tasdig‘i zanjiri shart.</li>
          <li>Ziddiyat bo‘lsa, “resolve” qilinmaguncha oldinga o‘tmaydi.</li>
        </ul>
      </section>
    </Page>
  );
}

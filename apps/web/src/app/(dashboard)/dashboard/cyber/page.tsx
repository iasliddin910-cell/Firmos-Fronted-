"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function CyberPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string>("");
  const [incidentMode, setIncidentMode] = useState<boolean>(false);

  async function refresh() {
    setErr("");
    try {
      const r = await apiGet<any>("/api/v1/agents/cyber/insights");
      setData(r);
      setIncidentMode(Boolean(r?.incidentMode));
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
      // brute-force logins
      for (let i = 0; i < 12; i++) {
        await apiPost("/api/v1/agents/cyber/mock/login", { ip: "1.1.1.1", success: false, country: "other" });
      }

      // bot api traffic
      for (let i = 0; i < 220; i++) {
        await apiPost("/api/v1/agents/cyber/mock/api", { ip: "2.2.2.2", path: "/api/v1/orders", status: 200, bytesOut: 1000 });
      }

      // infra bad
      await apiPost("/api/v1/agents/cyber/mock/infra", { cpu: 90, ram: 85, errorRate: 0.15, downtimeMinutes: 45 });

      // data leak suspicious (bytesOut huge)
      await apiPost("/api/v1/agents/cyber/mock/api", { ip: "3.3.3.3", path: "/api/v1/export", status: 200, bytesOut: 80 * 1024 * 1024 });

      // payment abuse
      await apiPost("/api/v1/agents/cyber/mock/payment", { provider: "Payme", type: "REFUND", suspicious: true, note: "Repeated refund" });

      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function toggleIncident() {
    setErr("");
    try {
      const next = !incidentMode;
      await apiPost("/api/v1/agents/cyber/incident-mode", { enabled: next });
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function runAgent() {
    setErr("");
    try {
      await apiPost("/api/v1/agents/cyber/run", {});
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Cybersecurity Agent">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={seedDemo}>Demo xavfli loglar qo‘shish</button>
        <button onClick={toggleIncident}>Incident Mode: {incidentMode ? "ON" : "OFF"}</button>
        <button onClick={runAgent}>Cyber Agent’ni ishga tushirish (signal)</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Insights</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>ISTISNO izohi</div>
        <p>
          Incident Mode ON va Data Leak suspicious bo‘lsa, agent “shutdown request” signal chiqaradi.
          Bu avtomatik o‘chirish emas — Owner/Company Brain tasdig‘i talab qilinadi.
        </p>
      </section>
    </Page>
  );
}

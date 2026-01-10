"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet } from "../../../../lib/api";

type PriorityItem = {
  signalId: string;
  title: string;
  agent: string;
  riskLevel: string;
  confidence: number;
  score: number;
  why: string[];
};

type Conflict = {
  aSignalId: string;
  bSignalId: string;
  topic: string;
  note: string;
};

type Analysis = {
  timeframe?: { from: string; to: string };
  topProblems: PriorityItem[];
  conflicts: Conflict[];
  notes: string[];
};

export default function CompanyBrainPage() {
  const [data, setData] = useState<Analysis | null>(null);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    apiGet<Analysis>("/api/v1/agents/company-brain/analysis")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <Page title="Company Brain">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}
      {!data ? (
        <div style={{ opacity: 0.7 }}>Loading...</div>
      ) : (
        <div style={{ display: "grid", gap: 14 }}>
          <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Top muammolar (Priority Engine)</div>
            {data.topProblems.length === 0 ? (
              <div style={{ opacity: 0.7 }}>Signal yo‘q. Avval agentlar signal chiqarishi kerak.</div>
            ) : (
              <div style={{ display: "grid", gap: 10 }}>
                {data.topProblems.map((p) => (
                  <div key={p.signalId} style={{ border: "1px solid #eee", borderRadius: 10, padding: 10 }}>
                    <div style={{ fontWeight: 600 }}>{p.title}</div>
                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                      Agent: {p.agent} · Risk: {p.riskLevel} · Score: {p.score.toFixed(3)} · Confidence:{" "}
                      {Number(p.confidence ?? 0.5).toFixed(2)}
                    </div>
                    <div style={{ fontSize: 12, marginTop: 6, opacity: 0.9 }}>
                      Nega: {p.why.join(" · ")}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Ziddiyatlar (Conflict Engine)</div>
            {data.conflicts.length === 0 ? (
              <div style={{ opacity: 0.7 }}>Ziddiyat aniqlanmadi.</div>
            ) : (
              <div style={{ display: "grid", gap: 10 }}>
                {data.conflicts.map((c, idx) => (
                  <div key={idx} style={{ border: "1px solid #eee", borderRadius: 10, padding: 10 }}>
                    <div style={{ fontWeight: 600 }}>{c.topic}</div>
                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                      A: {c.aSignalId} · B: {c.bSignalId}
                    </div>
                    <div style={{ marginTop: 6 }}>{c.note}</div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Protokol eslatmasi</div>
            <ul>
              {data.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </Page>
  );
}

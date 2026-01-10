"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet } from "../../../../lib/api";

type SignalsResponse = { items: any[] };

export default function OverviewPage() {
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    apiGet<SignalsResponse>("/api/v1/signals")
      .then((r) => setItems(r.items || []))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <Page title="Overview">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <p>So‘nggi signal’lar (AgentSignal):</p>
      <div style={{ display: "grid", gap: 10 }}>
        {items.length === 0 ? (
          <div style={{ opacity: 0.7 }}>Hozircha signal yo‘q. Keyingi bosqichda Company Brain birinchi signal chiqaradi.</div>
        ) : (
          items.map((s) => (
            <div
              key={s.id}
              style={{
                border: "1px solid #ddd",
                borderRadius: 10,
                padding: 12
              }}
            >
              <div style={{ fontWeight: 600 }}>{s.title}</div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>
                Agent: {s.agent} · Risk: {s.riskLevel} · Confidence: {s.confidence}
              </div>
              <div style={{ marginTop: 6 }}>{s.summary}</div>
            </div>
          ))
        )}
      </div>
    </Page>
  );
}

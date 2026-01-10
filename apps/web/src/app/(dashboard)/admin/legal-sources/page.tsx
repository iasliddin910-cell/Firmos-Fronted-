"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function LegalSourcesAdminPage() {
  const [err, setErr] = useState("");
  const [data, setData] = useState<any>(null);

  const [title, setTitle] = useState("VAT threshold (mock official)");
  const [sourceType, setSourceType] = useState("TAX_CODE");
  const [refCode, setRefCode] = useState("SK:VAT_THRESHOLD");
  const [text, setText] = useState("Rasmiy matn (mock).");
  const [ruleKey, setRuleKey] = useState("VAT_THRESHOLD_12M");
  const [threshold, setThreshold] = useState("1000000000");

  async function refresh() {
    setErr("");
    try {
      const r = await apiGet("/api/v1/admin/legal-sources");
      setData(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function add() {
    setErr("");
    try {
      await apiPost("/api/v1/admin/legal-sources", {
        source_type: sourceType,
        title,
        reference_code: refCode,
        text_content: text,
        metadata_json: {
          rule_key: ruleKey,
          threshold: Number(threshold)
        }
      });
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Admin: Legal Sources (official-only)">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Add official source</div>

        <div style={{ display: "grid", gap: 8, maxWidth: 700 }}>
          <label>Source type <input value={sourceType} onChange={(e) => setSourceType(e.target.value)} /></label>
          <label>Title <input value={title} onChange={(e) => setTitle(e.target.value)} /></label>
          <label>Reference code <input value={refCode} onChange={(e) => setRefCode(e.target.value)} /></label>
          <label>Text content <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} /></label>

          <div style={{ fontWeight: 600, marginTop: 6 }}>Rule metadata</div>
          <label>rule_key <input value={ruleKey} onChange={(e) => setRuleKey(e.target.value)} /></label>
          <label>threshold (if used) <input value={threshold} onChange={(e) => setThreshold(e.target.value)} /></label>

          <button onClick={add}>Add</button>
        </div>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Registry</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading..."}</pre>
      </section>
    </Page>
  );
}

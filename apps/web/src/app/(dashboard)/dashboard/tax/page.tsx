"use client";

import React, { useMemo, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function TaxPage() {
  const [err, setErr] = useState("");
  const [uploadRes, setUploadRes] = useState<any>(null);
  const [insRegime, setInsRegime] = useState<any>(null);
  const [insVat, setInsVat] = useState<any>(null);
  const [insPenalty, setInsPenalty] = useState<any>(null);
  const [chat, setChat] = useState<any>(null);

  const [msg, setMsg] = useState("QQSdan chiqish mumkinmi?");
  const [annualTurnover, setAnnualTurnover] = useState("100000000");
  const [turnover12m, setTurnover12m] = useState("900000000");

  const [fileName, setFileName] = useState("report.json");
  const [fileType, setFileType] = useState<"json" | "csv" | "pdf" | "xlsx">("json");
  const [base64, setBase64] = useState("");

  const readyUpload = useMemo(() => fileName && fileType && base64, [fileName, fileType, base64]);

  async function upload() {
    setErr("");
    try {
      const r = await apiPost("/api/v1/agents/tax/uploads", {
        filename: fileName,
        file_type: fileType,
        base64
      });
      setUploadRes(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function loadRegime() {
    setErr("");
    try {
      const r = await apiGet(`/api/v1/agents/tax/insights/regime?annualTurnover=${Number(annualTurnover)}`);
      setInsRegime(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function loadVat() {
    setErr("");
    try {
      const r = await apiGet(`/api/v1/agents/tax/insights/vat-obligation?turnover12m=${Number(turnover12m)}`);
      setInsVat(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function loadPenalty() {
    setErr("");
    try {
      const r = await apiGet(`/api/v1/agents/tax/insights/penalty-risk?lateReports=1&mismatches=0&missingFields=1`);
      setInsPenalty(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function sendChat() {
    setErr("");
    try {
      const r = await apiPost("/api/v1/agents/tax/chat", { message: msg });
      setChat(r);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Tax Optimizer">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Upload center</div>

        <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
          <label>
            Filename
            <input value={fileName} onChange={(e) => setFileName(e.target.value)} />
          </label>

          <label>
            File type
            <select value={fileType} onChange={(e) => setFileType(e.target.value as any)}>
              <option value="json">json</option>
              <option value="csv">csv</option>
              <option value="pdf">pdf</option>
              <option value="xlsx">xlsx</option>
            </select>
          </label>

          <label>
            Base64 (iPhone’da faylni base64 qilish oson bo‘lishi uchun keyin helper qo‘shamiz)
            <textarea value={base64} onChange={(e) => setBase64(e.target.value)} rows={4} />
          </label>

          <button disabled={!readyUpload} onClick={upload}>
            Upload
          </button>
        </div>

        <pre style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>{uploadRes ? JSON.stringify(uploadRes, null, 2) : ""}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Insights</div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
          <button onClick={loadRegime}>Tax Regime Validator</button>
          <button onClick={loadVat}>VAT Obligation Monitor</button>
          <button onClick={loadPenalty}>Penalty Risk Scanner</button>
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <div style={{ fontWeight: 600 }}>Regime input</div>
            <input value={annualTurnover} onChange={(e) => setAnnualTurnover(e.target.value)} />
            <pre style={{ whiteSpace: "pre-wrap" }}>{insRegime ? JSON.stringify(insRegime, null, 2) : ""}</pre>
          </div>

          <div>
            <div style={{ fontWeight: 600 }}>VAT input (12m turnover)</div>
            <input value={turnover12m} onChange={(e) => setTurnover12m(e.target.value)} />
            <pre style={{ whiteSpace: "pre-wrap" }}>{insVat ? JSON.stringify(insVat, null, 2) : ""}</pre>
          </div>

          <div>
            <div style={{ fontWeight: 600 }}>Penalty</div>
            <pre style={{ whiteSpace: "pre-wrap" }}>{insPenalty ? JSON.stringify(insPenalty, null, 2) : ""}</pre>
          </div>
        </div>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Tax Chat (3-section)</div>
        <div style={{ display: "grid", gap: 8, maxWidth: 700 }}>
          <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={2} />
          <button onClick={sendChat}>Send</button>
        </div>

        <pre style={{ whiteSpace: "pre-wrap", marginTop: 10 }}>{chat ? JSON.stringify(chat, null, 2) : ""}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Qoidalar</div>
        <ul>
          <li>Faqat rasmiy manbalar (legal_sources registry) ishlatiladi.</li>
          <li>Asos bo‘lmasa: “BASIS_MISSING” deb qaytadi, uylab topmaydi.</li>
          <li>Maslahat: hisobot yuborilmaydi, kabinetga login qilinmaydi.</li>
        </ul>
      </section>
    </Page>
  );
}

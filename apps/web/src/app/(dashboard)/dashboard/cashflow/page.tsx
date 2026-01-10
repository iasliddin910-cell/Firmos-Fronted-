"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function CashflowPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function refresh() {
    setErr("");
    try {
      const r = await apiGet<any>("/api/v1/agents/cashflow/insights");
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
      // incomes
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "IN", amount: 25000000, category: "SALES", vendor: "orders" });
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "IN", amount: 12000000, category: "SALES", vendor: "orders" });

      // expenses
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "OUT", amount: 7800000, category: "MARKETING", vendor: "meta" });
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "OUT", amount: 6000000, category: "PAYROLL", vendor: "salary" });

      // repeating small leak
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "OUT", amount: 350000, category: "SUBSCRIPTION", vendor: "tool-x" });
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "OUT", amount: 350000, category: "SUBSCRIPTION", vendor: "tool-x" });
      await apiPost("/api/v1/agents/cashflow/mock/tx", { type: "OUT", amount: 350000, category: "SUBSCRIPTION", vendor: "tool-x" });

      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function runAgent() {
    setErr("");
    try {
      await apiPost("/api/v1/agents/cashflow/run", {});
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Cashflow Agent">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={seedDemo}>Demo tranzaksiyalar qo‘shish</button>
        <button onClick={runAgent}>Cashflow Agent’ni ishga tushirish (signal)</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Insights</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading..."}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Eslatma</div>
        <p>Run qilinsa signal Overview + Company Brain’da ko‘rinadi.</p>
      </section>
    </Page>
  );
}

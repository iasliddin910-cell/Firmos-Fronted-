"use client";

import React, { useEffect, useState } from "react";
import { Page } from "../../../../components/Page";
import { apiGet, apiPost } from "../../../../lib/api";

export default function SalesPage() {
  const [loss, setLoss] = useState<any>(null);
  const [profit, setProfit] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function refresh() {
    setErr("");
    try {
      const l = await apiGet<any>("/api/v1/agents/sales/insights/loss");
      const p = await apiGet<any>("/api/v1/agents/sales/insights/profit");
      setLoss(l);
      setProfit(p);
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
      // create 3 demo orders + 1 complaint
      await apiPost("/api/v1/agents/sales/mock/orders", {
        channel: "TELEGRAM",
        status: "CREATED",
        amount: 120000,
        estCost: 80000,
        prepaid: false,
        customerId: "c1"
      });
      await apiPost("/api/v1/agents/sales/mock/orders", {
        channel: "WEBSITE",
        status: "CANCELLED",
        amount: 200000,
        estCost: 120000,
        prepaid: true,
        customerId: "c2"
      });
      await apiPost("/api/v1/agents/sales/mock/orders", {
        channel: "APP",
        status: "FAILED",
        amount: 150000,
        estCost: 90000,
        prepaid: false,
        customerId: "c3"
      });
      await apiPost("/api/v1/agents/sales/mock/complaints", {
        channel: "TELEGRAM",
        topic: "DELIVERY_DELAY",
        text: "Yetkazish kechikdi",
        customerId: "c1"
      });
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function runAgent() {
    setErr("");
    try {
      await apiPost("/api/v1/agents/sales/run", {});
      await refresh();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Page title="Sales Agent">
      {err ? <div style={{ color: "red" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={seedDemo}>Demo ma’lumot qo‘shish</button>
        <button onClick={runAgent}>Sales Agent’ni ishga tushirish (signal)</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Loss Intelligence</div>
          <pre style={{ whiteSpace: "pre-wrap" }}>{loss ? JSON.stringify(loss, null, 2) : "Loading..."}</pre>
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Profit Discovery</div>
          <pre style={{ whiteSpace: "pre-wrap" }}>{profit ? JSON.stringify(profit, null, 2) : "Loading..."}</pre>
        </section>

        <section style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Eslatma</div>
          <p>
            “Sales Agent’ni ishga tushirish” tugmasi signal yaratadi va u avtomatik ravishda Overview hamda Company Brain’da
            ko‘rinadi (ulash uchun qayta o‘zgartirish talab qilinmaydi).
          </p>
        </section>
      </div>
    </Page>
  );
}

"use client";

import React, { useEffect } from "react";
import { audit } from "../lib/audit";

export function Page(props: { title: string; children: React.ReactNode }) {
  useEffect(() => {
    audit("VIEW_PAGE", props.title).catch(() => {});
  }, [props.title]);

  return (
    <div style={{ padding: 16, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial" }}>
      <h1 style={{ fontSize: 20, marginBottom: 12 }}>{props.title}</h1>
      <div>{props.children}</div>
    </div>
  );
}

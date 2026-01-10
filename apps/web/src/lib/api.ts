type Headers = Record<string, string>;

function baseUrl() {
  return (process.env["NEXT_PUBLIC_API_BASE"] || "http://localhost:4000").replace(/\/+$/, "");
}

function authHeaders(): Headers {
  // Telefonda demo auth: localStorage-based (keyin real auth qo'yamiz)
  if (typeof window === "undefined") return {};
  const role = localStorage.getItem("firmos_role") || "OWNER";
  const actorId = localStorage.getItem("firmos_actor_id") || "user-1";
  const orgId = localStorage.getItem("firmos_org_id") || "default-org";
  return {
    "x-role": role,
    "x-actor-id": actorId,
    "x-org-id": orgId
  };
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    method: "GET",
    headers: { ...authHeaders() }
  });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...authHeaders() },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

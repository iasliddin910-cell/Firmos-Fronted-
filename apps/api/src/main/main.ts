import http from "http";
import { parse } from "url";

type Handler = (req: http.IncomingMessage, res: http.ServerResponse) => Promise<void> | void;

type RouteKey = `${string} ${string}`; // "GET /path"
const routes = new Map<RouteKey, Handler>();

function json(res: http.ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(body));
}

function notFound(res: http.ServerResponse) {
  json(res, 404, { error: "NOT_FOUND" });
}

function getBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      if (!data) return resolve(undefined);
      try {
        resolve(JSON.parse(data));
      } catch {
        resolve(undefined);
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  const method = (req.method || "GET").toUpperCase();
  const urlObj = parse(req.url || "/", true);
  const pathname = urlObj.pathname || "/";
  const key = `${method} ${pathname}` as RouteKey;

  // simple health
  if (key === "GET /health") return json(res, 200, { ok: true });

  const handler = routes.get(key);
  if (!handler) return notFound(res);

  // attach parsed fields
  (req as any).query = urlObj.query;
  (req as any).body = await getBody(req);

  try {
    await handler(req, res);
  } catch (e: any) {
    json(res, 500, { error: "INTERNAL_ERROR", message: e?.message ?? "unknown" });
  }
});

export function registerRoute(method: string, path: string, handler: Handler) {
  routes.set(`${method.toUpperCase()} ${path}` as RouteKey, handler);
}

export function start(port: number) {
  server.listen(port);
  // eslint-disable-next-line no-console
  console.log(`API listening on http://localhost:${port}`);
}

// ---- register core routes (will be expanded later) ----
import { registerCore } from "../modules/core/core.module";
registerCore(registerRoute);

// If running directly
if (process.env["RUN_MAIN"] === "1") {
  start(Number(process.env["PORT"] || 4000));
}

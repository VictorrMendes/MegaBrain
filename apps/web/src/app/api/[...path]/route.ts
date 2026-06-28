import { NextRequest } from "next/server";

const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://api:8100";

async function proxy(req: NextRequest): Promise<Response> {
  const url = req.nextUrl;
  // strip leading /api prefix and normalize trailing slash
  const upstreamPath = url.pathname
    .replace(/^\/api/, "")
    .replace(/\/$/, "") || "/";
  const upstreamUrl = `${API_INTERNAL_URL}${upstreamPath}${url.search}`;

  const headers = new Headers(req.headers);
  const host = headers.get("host") || "";
  headers.delete("host");
  
  // Pass along real client URL details to FastAPI
  const protocol = req.nextUrl.protocol.replace(":", "");
  headers.set("x-forwarded-proto", protocol);
  headers.set("x-forwarded-host", host);
  headers.set("x-forwarded-prefix", "/api");

  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : req.body;

  const upstream = await fetch(upstreamUrl, {
    method: req.method,
    headers,
    body,
    redirect: "manual",
    // @ts-expect-error — Node fetch duplex required for streaming body
    duplex: "half",
  });

  // Pass the upstream response straight through — this preserves SSE streaming.
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

// Required for SSE and large uploads — disable Next.js body parsing / response buffering.
export const dynamic = "force-dynamic";

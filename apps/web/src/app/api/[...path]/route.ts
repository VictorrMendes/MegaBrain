import { NextRequest } from "next/server";

const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://api:8100";

async function proxy(req: NextRequest): Promise<Response> {
  const url = req.nextUrl;
  // strip leading /api prefix
  const upstreamPath = url.pathname.replace(/^\/api/, "");
  const upstreamUrl = `${API_INTERNAL_URL}${upstreamPath}${url.search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");

  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : req.body;

  const upstream = await fetch(upstreamUrl, {
    method: req.method,
    headers,
    body,
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

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [
      { source: "/", destination: "/chat", permanent: false },
    ];
  },
  async rewrites() {
    const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8100";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/:path*` },
    ];
  },
};

export default nextConfig;

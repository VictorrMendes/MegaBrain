import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async redirects() {
    return [
      { source: "/", destination: "/chat", permanent: false },
    ];
  },
  async rewrites() {
    const apiUrl = process.env.API_INTERNAL_URL ?? "http://api:8100";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/:path*` },
    ];
  },
};

export default nextConfig;

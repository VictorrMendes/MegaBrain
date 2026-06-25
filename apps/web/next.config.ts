import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100",
  },
  async redirects() {
    return [
      { source: "/", destination: "/chat", permanent: false },
    ];
  },
};

export default nextConfig;

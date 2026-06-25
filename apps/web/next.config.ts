import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async redirects() {
    return [
      { source: "/", destination: "/chat", permanent: false },
    ];
  },
};

export default nextConfig;

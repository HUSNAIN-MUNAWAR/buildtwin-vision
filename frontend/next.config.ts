import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: { cpus: 2 }
};
export default nextConfig;

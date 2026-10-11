import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // The repo root sits above this app and contains an unrelated package-lock.json
  // in the user's home directory; pinning the root keeps Turbopack's module
  // resolution and caching inside web/.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;

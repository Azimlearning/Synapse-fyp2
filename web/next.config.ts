import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A second build (the hosted demo, NEXT_DIST_DIR=.next-demo) can live beside the one start-synapse.ps1 runs.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // @arcana/schema ships TypeScript source; Next must transpile it.
  transpilePackages: ["@arcana/schema"],
  // The hosted demo's replay route reads the recorded responses at run time; they must ship with its function.
  outputFileTracingIncludes: { "/demo-api/[...path]": ["./demo-data/**/*"] },
  // Security headers for the public hosted demo only (a local build is unchanged). The app is never framed by another site.
  async headers() {
    if (process.env.NEXT_PUBLIC_DEMO !== "1") return [];
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
        ],
      },
    ];
  },
};

export default nextConfig;

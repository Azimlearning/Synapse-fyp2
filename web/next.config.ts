import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A second build (the hosted demo, NEXT_DIST_DIR=.next-demo) can live beside the one start-synapse.ps1 runs.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // @arcana/schema ships TypeScript source; Next must transpile it.
  transpilePackages: ["@arcana/schema"],
  // The hosted demo's replay route reads the recorded responses at run time; they must ship with its function.
  outputFileTracingIncludes: { "/demo-api/[...path]": ["./demo-data/**/*"] },
};

export default nextConfig;

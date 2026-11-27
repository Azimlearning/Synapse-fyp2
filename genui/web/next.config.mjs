// The Kit is served by the API at /vendor/kit/<semver>/. A srcdoc iframe resolves relative URLs against the PARENT page, so the
// Kit must be same-origin with this app: proxy /vendor/* to the API (a v3 finding; the browser smoke proves it).
const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // A second build (for example one pointed at another API port) can live beside the default one.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // The hosted demo's replay route reads the recorded responses and the Kit at run time; they must ship with its function.
  outputFileTracingIncludes: { "/demo-api/[...path]": ["./demo-data/**/*"] },
  // Security headers for the public hosted demo only (a local build is unchanged). Only the Synapse demo, this site and a local
  // Synapse may frame it (the Simulations tab embeds it); each Environment inside keeps its own strict CSP.
  async headers() {
    if (process.env.NEXT_PUBLIC_DEMO !== "1") return [];
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' https://synapse-fyp2-demo.vercel.app http://localhost:3000 http://localhost:3010; base-uri 'self'; form-action 'self'; object-src 'none'",
          },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
        ],
      },
    ];
  },
  async rewrites() {
    return [{ source: "/vendor/:path*", destination: `${apiBase}/vendor/:path*` }];
  },
};

export default nextConfig;

// The Kit is served by the API at /vendor/kit/<semver>/. A srcdoc iframe resolves relative URLs against the PARENT page, so the
// Kit must be same-origin with this app: proxy /vendor/* to the API (a v3 finding; the browser smoke proves it).
const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // A second build (for example one pointed at another API port) can live beside the default one.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // The hosted demo's replay route reads the recorded responses and the Kit at run time; they must ship with its function.
  outputFileTracingIncludes: { "/demo-api/[...path]": ["./demo-data/**/*"] },
  async rewrites() {
    return [{ source: "/vendor/:path*", destination: `${apiBase}/vendor/:path*` }];
  },
};

export default nextConfig;

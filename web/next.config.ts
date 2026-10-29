import type { NextConfig } from "next";

// Same-origin API (DECISIONS D12): the browser calls /api/*, Next forwards to the FastAPI
// service, so the session cookie stays first-party and no CORS is needed.
// Rewrites are resolved at build time, so API_URL must be set when building.
const apiUrl = process.env.API_URL;
if (!apiUrl) {
  throw new Error("API_URL is not set (e.g. http://api:8000). See docker-compose.yml.");
}

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default config;

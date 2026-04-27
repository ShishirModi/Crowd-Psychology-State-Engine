import type { NextConfig } from "next";

const DJANGO = process.env.DJANGO_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/auth/:path*",   destination: `${DJANGO}/auth/:path*` },
      { source: "/analyze",       destination: `${DJANGO}/analyze` },
      { source: "/result/:path*", destination: `${DJANGO}/result/:path*` },
      { source: "/history",       destination: `${DJANGO}/history` },
      { source: "/latest",        destination: `${DJANGO}/latest` },
    ];
  },
};

export default nextConfig;

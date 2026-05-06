import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ★ Tier 2 D11: Tailscale / 다른 PC 접속 시 dev origin 허용
  // HMR WebSocket + dev request 차단 해제 (★ 본인 PC 무반응 본질 fix)
  allowedDevOrigins: [
    "100.70.109.50",
    ...(process.env.NEXT_DEV_ALLOWED_ORIGINS?.split(",")
      .map((s) => s.trim())
      .filter(Boolean) ?? []),
  ],
};

export default nextConfig;

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WorldFork — 한국어 어드벤처",
  description: "LLM 기반 한국어 인터랙티브 게임",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "BABSHARQII v40.0 — Mamoun AGI",
  description: "Living AGI System — 5 Brains · 3 Providers · NeuralBus · 400+ API Endpoints",
  icons: { icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" className="dark" dir="rtl" suppressHydrationWarning>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&family=Tajawal:wght@300;400;500;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body
        className="antialiased"
        style={{ margin: 0, background: '#080810', color: '#c8d0e0', fontFamily: "'Cairo', 'Tajawal', 'Space Grotesk', system-ui, sans-serif" }}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}

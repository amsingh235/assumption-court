import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assumption Court",
  description: "Five pixel agents put your business assumption on trial: quote-grounded evidence, rubric-scored verdict.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#1a1918" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=Silkscreen&display=swap" rel="stylesheet" />
      </head>
      <body className="flex min-h-full flex-col bg-ink font-sans text-cream">{children}</body>
    </html>
  );
}

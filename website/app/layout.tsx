import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://mise.local"),
  title: "Mise — the agentic kitchen copilot",
  description:
    "Mise watches your stove through any camera, remembers what you cook, and keeps the fire under control. Open source. Runs on your laptop.",
  icons: { icon: "/mise-logo.png" },
  openGraph: {
    title: "Mise — the agentic kitchen copilot",
    description: "Watches the stove. Remembers your cooking. Kills the power if you walk away.",
    images: ["/mise-logo.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased font-sans">{children}</body>
    </html>
  );
}

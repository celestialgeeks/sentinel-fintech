import type { Metadata, Viewport } from "next";
import { Inter, IBM_Plex_Mono, Playfair_Display } from "next/font/google";
import "./globals.css";

// Three faces, three jobs. Inter (300–700) is the interface, IBM Plex Mono keeps
// ids/UTRs/hashes from reflowing, and Playfair Display Italic carries the editorial
// headings — the serif + gold is what makes this read as a luxury artefact rather
// than a dashboard.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Sentinel — Pre-settlement AML guard for Binance P2P merchants",
    template: "%s · Sentinel",
  },
  description:
    "Sentinel screens the buyer before they pay and the rupees before they settle. ALLOW, HOLD or BLOCK in seconds, with the evidence pack that unfreezes an account.",
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${plexMono.variable} ${playfair.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

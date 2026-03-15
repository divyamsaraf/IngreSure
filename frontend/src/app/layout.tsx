import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair" });

export const metadata: Metadata = {
  title: "IngreSure - AI Food Safety & Verification",
  description: "Verify menu ingredients, detect allergens, and eat with confidence using IngreSure's AI-powered platform.",
  openGraph: {
    title: "IngreSure - AI Food Safety",
    description: "Eat with confidence. Know what's inside.",
    type: "website",
  }
};

import Navbar from "@/components/Navbar";
import { ConfigProvider } from "@/context/ConfigContext";
import { ProfileProvider } from "@/context/ProfileContext";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className="antialiased font-sans" suppressHydrationWarning>
        <ConfigProvider>
          <ProfileProvider>
            <Navbar />
            {children}
          </ProfileProvider>
        </ConfigProvider>
      </body>
    </html>
  );
}

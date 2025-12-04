import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IngreSure - AI Food Safety & Verification",
  description: "Verify menu ingredients, detect allergens, and eat with confidence using IngreSure's AI-powered platform.",
  openGraph: {
    title: "IngreSure - AI Food Safety",
    description: "Eat with confidence. Know what's inside.",
    type: "website",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { AppNav } from "@/components/nav/AppNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "KHONSHU",
  description: "Sistema Operacional Cognitivo",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
        <div className="flex h-screen overflow-hidden bg-neutral-950 text-neutral-100">
          <AppNav />
          <div className="flex-1 overflow-hidden">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}

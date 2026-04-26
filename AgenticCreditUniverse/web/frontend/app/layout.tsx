import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const pretendard = localFont({
  src: [
    { path: "./fonts/Pretendard-Regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/Pretendard-Medium.woff2", weight: "500", style: "normal" },
    { path: "./fonts/Pretendard-SemiBold.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-pretendard",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Credit Universe",
  description: "Credit Universe — 26.1H 검토 워크벤치",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={`${pretendard.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}

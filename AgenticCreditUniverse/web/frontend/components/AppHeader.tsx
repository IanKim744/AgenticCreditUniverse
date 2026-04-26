"use client";

import Link from "next/link";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AppHeader({
  periodLabel,
  username = "risk",
}: {
  periodLabel: string;
  username?: string;
}) {
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <header className="sticky top-0 z-40 h-14 border-b bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-full items-center gap-6 px-6">
        <Link href="/" className="flex items-baseline gap-2 font-semibold tracking-tight">
          <span>Credit Universe</span>
          <span className="text-xs font-normal text-muted-foreground">· {periodLabel} 검토</span>
        </Link>
        <div className="flex-1" />
        <Button asChild variant="outline" size="sm">
          <a href="/api/export.xlsx" download>
            <Download className="h-4 w-4" />
            엑셀 다운로드
          </a>
        </Button>
        <span className="text-xs text-muted-foreground truncate max-w-[120px]">{username}</span>
        <button
          type="button"
          onClick={logout}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          로그아웃
        </button>
      </div>
    </header>
  );
}

"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const SECTIONS: { id: string; label: string }[] = [
  { id: "sec-overview", label: "개요" },
  { id: "sec-financials", label: "재무 추이" },
  { id: "sec-opinion", label: "신평사 의견" },
  { id: "sec-comment", label: "AI 코멘트" },
  { id: "sec-news", label: "뉴스" },
  { id: "sec-dart", label: "DART 공시" },
  { id: "sec-history", label: "반기 히스토리" },
];

export function FloatingTOC() {
  const [active, setActive] = useState(SECTIONS[0]!.id);

  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setActive(e.target.id);
            break;
          }
        }
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: 0 },
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  return (
    <nav className="space-y-0.5">
      <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        목차
      </div>
      {SECTIONS.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className={cn(
            "block py-1.5 pl-3 text-xs border-l-2 transition-colors",
            active === s.id
              ? "border-primary text-foreground font-medium"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {s.label}
        </a>
      ))}
    </nav>
  );
}

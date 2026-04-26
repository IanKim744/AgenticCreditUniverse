"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { KpiCard } from "@/components/kpi-card";
import { UniverseChip } from "@/components/universe-chip";
import { Progress } from "@/components/ui/progress";
import { parseWatch } from "@/lib/credit";
import type { CompanyRow, Kpis } from "@/lib/api";

export function KpiBar({
  kpis,
  rows,
  periodLabel,
}: {
  kpis: Kpis;
  rows: CompanyRow[];
  periodLabel: string;
}) {
  const universeCounts = useMemo(() => {
    const c = { O: 0, "△": 0, X: 0 };
    for (const r of rows) {
      // 심사역 최종 우선, 없으면 AI 판단.
      const v = (r.reviewer_final ?? r.universe_curr_ai) as
        | "O"
        | "△"
        | "X"
        | null
        | undefined;
      if (v && v in c) c[v]++;
    }
    return c;
  }, [rows]);

  const negativeCount = useMemo(
    () => rows.filter((r) => parseWatch(r.watch_curr) === "negative").length,
    [rows],
  );
  const negativePct = kpis.total ? (negativeCount / kpis.total) * 100 : 0;

  const cards = [
    <KpiCard
      key="total"
      label={`${periodLabel} 검토`}
      value={kpis.total}
      hint="유니버스 전체"
    >
      <UniverseInlineCounts counts={universeCounts} />
    </KpiCard>,
    <KpiCard
      key="negative"
      label="부정적 전망"
      value={negativeCount}
      hint={`${negativePct.toFixed(1)}% (${negativeCount}/${kpis.total})`}
    />,
    <KpiCard key="move" label="의견 변동">
      <span
        className="flex items-center gap-1 tabular-nums"
        style={{ color: "var(--watch-positive)" }}
      >
        <ArrowUp className="h-3 w-3" />
        {kpis.movement.up}
      </span>
      <span
        className="flex items-center gap-1 tabular-nums"
        style={{ color: "var(--watch-negative)" }}
      >
        <ArrowDown className="h-3 w-3" />
        {kpis.movement.down}
      </span>
      <span className="flex items-center gap-1 text-muted-foreground tabular-nums">
        <Minus className="h-3 w-3" />
        {kpis.movement.flat}
      </span>
    </KpiCard>,
    <KpiCard
      key="review"
      label="검수 진행 현황"
      value={`${kpis.review.done} / ${kpis.total}`}
      hint={`${(kpis.review.pct * 100).toFixed(0)}% 완료`}
    >
      <Progress value={kpis.review.pct * 100} className="h-1.5 w-full" />
    </KpiCard>,
  ];

  return (
    <div className="border-b bg-background/95">
      <div className="mx-auto grid grid-cols-2 gap-3 px-6 py-3 lg:grid-cols-4 items-stretch">
        {cards.map((c, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.05, ease: "easeOut" }}
            className="h-full"
          >
            {c}
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function UniverseInlineCounts({
  counts,
}: {
  counts: { O: number; "△": number; X: number };
}) {
  const items: { v: "O" | "△" | "X"; label: string }[] = [
    { v: "O", label: "가능" },
    { v: "△", label: "조건부" },
    { v: "X", label: "미편입" },
  ];
  return (
    <div className="flex items-center gap-3">
      {items.map((it) => (
        <span key={it.v} className="flex items-center gap-1.5 text-xs">
          <UniverseChip value={it.v} className="!w-5 !h-5 !text-[11px]" />
          <span className="text-muted-foreground">{it.label}</span>
          <span className="font-medium tabular-nums">{counts[it.v]}</span>
        </span>
      ))}
    </div>
  );
}

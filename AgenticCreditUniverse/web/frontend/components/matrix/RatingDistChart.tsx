"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ratingBucket, type RatingBucket } from "@/lib/credit";
import type { CompanyRow } from "@/lib/api";

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
};

// 등급/전망 컬럼과 동일한 8단계 시맨틱 (lib/credit.ts:ratingBucket).
// 단기등급(A1/A2±/A3±) 도 동일 hue 라인의 장기등급 tier 로 자동 매핑됨.
const BUCKETS: { key: RatingBucket; label: string }[] = [
  { key: "tier-1", label: "AA-" },     // AAA, AA+, AA, AA- + 단기 A1, A1+
  { key: "tier-2", label: "A+" },      // A+ + 단기 A2+
  { key: "tier-3", label: "A0" },      // A, A0 + 단기 A2, A20
  { key: "tier-4", label: "A-" },      // A- + 단기 A2-
  { key: "tier-5", label: "BBB+" },    // BBB+ + 단기 A3+
  { key: "tier-6", label: "BBB0" },    // BBB, BBB0 + 단기 A3, A30
  { key: "tier-7", label: "BBB-" },    // BBB- + 단기 A3-
  { key: "tier-8", label: "BB+ 이하" }, // BB+ ↓, B, C, D + 단기 B/C/D
];

export function RatingDistChart({ rows }: { rows: CompanyRow[] }) {
  const data = useMemo(() => {
    const counts: Record<RatingBucket, number> = {
      "tier-1": 0,
      "tier-2": 0,
      "tier-3": 0,
      "tier-4": 0,
      "tier-5": 0,
      "tier-6": 0,
      "tier-7": 0,
      "tier-8": 0,
      nr: 0,
    };
    for (const r of rows) counts[ratingBucket(r.rating_curr)]++;
    return BUCKETS.map((b) => ({
      bucket: b.label,
      key: b.key,
      color: `var(--rating-${b.key})`,
      count: counts[b.key],
    }));
  }, [rows]);

  return (
    <div
      className="flex h-full flex-col rounded-lg border bg-card p-4"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-baseline justify-between">
        <div className="text-sm font-medium">유효신용등급 분포</div>
        <div className="text-[11px] text-muted-foreground">
          단위: 종목 수 · 단기등급은 동급 매핑
        </div>
      </div>
      <div className="mt-3 flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="bucket"
              tickLine={false}
              axisLine={false}
              fontSize={10}
              interval={0}
              stroke="var(--muted-foreground)"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={11}
              stroke="var(--muted-foreground)"
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              cursor={{ fill: "var(--accent)", opacity: 0.4 }}
              formatter={(v) => [`${v ?? 0} 종목`, "건수"]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.key} fill={d.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

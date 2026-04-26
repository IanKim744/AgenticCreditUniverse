"use client";

import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { CompanyRow } from "@/lib/api";
import { bucketWithOthers, othersColor } from "@/lib/dist-chart";

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
};

type Props = {
  title: string;
  unitLabel: string;
  rows: CompanyRow[];
  pickField: (r: CompanyRow) => string | null;
  fallback: string;
};

/**
 * 분포 도넛 카드 (DistBarCard 와 동일 데이터 모델 + 비주얼 형제).
 *  - 중앙 텍스트는 SVG <Label> 의 viewBox 좌표 fallback 버그를 회피하기 위해
 *    ResponsiveContainer 위에 HTML overlay (absolute) 로 렌더.
 *  - 차트 본문에는 개별 카테고리만 (기타 제외, footer 텍스트로 표기).
 */
export function DistDonutCard({
  title,
  unitLabel,
  rows,
  pickField,
  fallback,
}: Props) {
  const { items, others, total, categoryCount } = useMemo(
    () => bucketWithOthers(rows.map(pickField), fallback),
    [rows, pickField, fallback],
  );

  return (
    <div
      className="flex h-full flex-col rounded-lg border bg-card p-4"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-sm font-medium">{title}</div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          총 {total}건 · {categoryCount}개 {unitLabel}
          {others && (
            <span className="ml-1 opacity-70">
              · 상위 {items.length} + 기타 {others.count}
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 grid flex-1 min-h-0 grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-center">
        {/* 도넛 + 중앙 텍스트 (HTML overlay) */}
        <div className="relative h-full min-h-[160px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v, _n, ctx) => {
                  const num = typeof v === "number" ? v : Number(v) || 0;
                  const pct = total ? ((num / total) * 100).toFixed(1) : "0.0";
                  const name =
                    (ctx?.payload as { name?: string } | undefined)?.name ?? "";
                  return [`${num}건 · ${pct}%`, name];
                }}
              />
              <Pie
                data={items}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={95}
                paddingAngle={2}
                stroke="var(--card)"
                strokeWidth={2}
              >
                {items.map((d) => (
                  <Cell key={d.name} fill={d.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-semibold tabular-nums leading-none">
              {total}건
            </span>
            <span className="mt-1 text-[10px] text-muted-foreground">
              {categoryCount}개 {unitLabel}
            </span>
          </div>
        </div>

        {/* 범례 — 좌측 정렬 (color · name · count · pct) */}
        <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] tabular-nums sm:grid-cols-3 lg:grid-cols-1">
          {items.map((d) => {
            const pct = total ? ((d.value / total) * 100).toFixed(1) : "0.0";
            return (
              <li key={d.name} className="flex items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: d.color }}
                />
                <span
                  className="flex-1 truncate text-muted-foreground"
                  title={d.name}
                >
                  {d.name}
                </span>
                <span className="shrink-0 text-foreground/80">{d.value}건</span>
                <span className="w-12 shrink-0 text-right font-medium">
                  {pct}%
                </span>
              </li>
            );
          })}
          {others && (
            <li
              key="__others__"
              className="flex items-center gap-2 opacity-80"
              title={`기타 ${others.count}개 ${unitLabel}`}
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: othersColor() }}
              />
              <span className="flex-1 truncate text-muted-foreground">
                기타 ({others.count}개)
              </span>
              <span className="shrink-0 text-foreground/80">
                {others.value}건
              </span>
              <span className="w-12 shrink-0 text-right font-medium">
                {others.pct.toFixed(1)}%
              </span>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import { Download, FileText } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceDot,
} from "recharts";
import { RATING_ORDER } from "@/lib/credit";

interface TimelinePoint {
  period: string;
  long_grade: string | null;
  short_grade: string | null;
}

interface OpinionMeta {
  agency?: string | null;
  rating_type?: string | null;
  bond_series?: string | null;
  bond_kind?: string | null;
  current_grade?: string | null;
  issued_date?: string | null;
  valid_until?: string | null;
  validity_note?: string | null;
}

interface Props {
  id: string;
  opinionPdfUrl: string | null;
  opinionMeta: OpinionMeta | null;
  timeline: TimelinePoint[];
}

export function Section3Opinion({ id, opinionPdfUrl, opinionMeta, timeline }: Props) {
  // 등급 인덱스 매핑 (낮을수록 우량)
  const data = timeline.map((p) => {
    const longIdx = p.long_grade && p.long_grade !== "-"
      ? RATING_ORDER.indexOf(p.long_grade.toUpperCase() as never)
      : null;
    return {
      period: p.period,
      장기등급: longIdx === -1 ? null : longIdx,
      label: p.long_grade,
    };
  });
  const validPoints = data.filter((p) => p.장기등급 !== null);
  const hasTimeline = validPoints.length > 0;

  // Detect transitions for emphasized markers
  const transitions: { idx: number; direction: "up" | "down" }[] = [];
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1]!.장기등급;
    const curr = data[i]!.장기등급;
    if (prev != null && curr != null && prev !== curr) {
      transitions.push({ idx: i, direction: curr < prev ? "up" : "down" });
    }
  }

  return (
    <section id={id} className="space-y-4 scroll-mt-32">
      <h2 className="text-lg font-semibold">신평사 의견</h2>

      {/* PDF embed (or empty state) */}
      <div
        className="rounded-lg border bg-card p-4"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-0.5">
            <div className="text-sm font-medium">
              {opinionMeta?.agency ?? "신평사"} 의견서
              {opinionMeta?.current_grade && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  · {opinionMeta.current_grade}
                </span>
              )}
            </div>
            {(opinionMeta?.bond_series || opinionMeta?.rating_type) && (
              <div className="text-xs text-muted-foreground">
                {opinionMeta?.bond_series ?? opinionMeta?.rating_type}
                {opinionMeta?.bond_kind && ` (${opinionMeta.bond_kind})`}
              </div>
            )}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 pt-1 text-[11px] text-muted-foreground tabular-nums">
              {opinionMeta?.issued_date && (
                <span>공시일 {opinionMeta.issued_date}</span>
              )}
              {opinionMeta?.valid_until && (
                <span>유효기간 ~ {opinionMeta.valid_until}</span>
              )}
            </div>
          </div>
          {opinionPdfUrl && (
            <a
              href={opinionPdfUrl}
              download
              className="inline-flex items-center gap-1 rounded-md border border-input bg-background px-2.5 py-1 text-xs font-medium hover:bg-accent transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              다운로드
            </a>
          )}
        </div>
        {opinionPdfUrl ? (
          <object
            data={opinionPdfUrl}
            type="application/pdf"
            className="h-[600px] w-full rounded border"
          >
            <a
              href={opinionPdfUrl}
              target="_blank"
              rel="noopener"
              className="text-sm text-primary hover:underline"
            >
              브라우저에서 PDF를 표시할 수 없습니다 — 새 탭에서 열기
            </a>
          </object>
        ) : (
          <EmptyState />
        )}
      </div>

      {/* Rating timeline */}
      <div
        className="rounded-lg border bg-card p-4"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        <div className="mb-2 text-sm font-medium">등급 변동 타임라인</div>
        {hasTimeline ? (
          <motion.div
            className="h-56"
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="period" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  reversed
                  tickFormatter={(i) => RATING_ORDER[i] ?? ""}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    fontSize: 12,
                    backgroundColor: "var(--popover)",
                  }}
                  formatter={(_v, _n, ctx) =>
                    [(ctx.payload as { label: string | null }).label ?? "—", "장기등급"]
                  }
                />
                <Line
                  type="monotone"
                  dataKey="장기등급"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "var(--chart-1)" }}
                  connectNulls
                />
                {transitions.map((t) => (
                  <ReferenceDot
                    key={t.idx}
                    x={data[t.idx]?.period ?? ""}
                    y={data[t.idx]?.장기등급 ?? 0}
                    r={6}
                    strokeWidth={2}
                    fill={
                      t.direction === "up" ? "var(--watch-positive)" : "var(--watch-negative)"
                    }
                    stroke={
                      t.direction === "up" ? "var(--watch-positive)" : "var(--watch-negative)"
                    }
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </motion.div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">
            변동 이력 없음 (등급 미부여 또는 단기물 한정)
          </p>
        )}
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <div className="py-12 text-center">
      <FileText className="mx-auto h-10 w-10 text-muted-foreground/40" />
      <p className="mt-3 text-base font-medium">신평사 의견서 미수집</p>
      <p className="mt-1 text-sm text-muted-foreground">
        PoC 단계에서는 NICE PDF가 수집되지 않았습니다. 다음 빌드 사이클에서 자동 첨부됩니다.
      </p>
    </div>
  );
}

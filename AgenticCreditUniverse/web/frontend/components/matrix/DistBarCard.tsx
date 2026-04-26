"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CompanyRow } from "@/lib/api";
import { bucketWithOthers, othersStroke, type DistItem } from "@/lib/dist-chart";

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
  padding: "8px 10px",
  maxWidth: 320,
};

const ROW_PX = 28;
const RIGHT_MARGIN_PX = 96;
const WATCH_COLOR = "var(--watch-negative)"; // 유의업종 = 적색 (매트릭스 ○ 표기와 동일)

type Props = {
  title: string;
  unitLabel: string;
  rows: CompanyRow[];
  pickField: (r: CompanyRow) => string | null;
  fallback: string;
  /** 유의업종 카테고리명 set — 막대를 적색으로 override + 범례 노출. */
  watchSet?: Set<string>;
};

export function DistBarCard({
  title,
  unitLabel,
  rows,
  pickField,
  fallback,
  watchSet,
}: Props) {
  const { items, others, total, categoryCount } = useMemo(
    () => bucketWithOthers(rows.map(pickField), fallback),
    [rows, pickField, fallback],
  );

  // 유의업종 표시 여부 — 데이터에 실제로 유의업종 카테고리가 있을 때만 범례 노출.
  const hasWatch = !!watchSet && watchSet.size > 0;
  // 기타 그룹에 묶인 유의업종 멤버 (툴팁 강조용)
  const watchInOthers = useMemo(() => {
    if (!watchSet || !others?.members) return [];
    return others.members.filter((m) => watchSet.has(m));
  }, [watchSet, others]);

  const chartHeight = items.length * ROW_PX + 8;

  return (
    <div
      className="flex h-full flex-col rounded-lg border bg-card p-4"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{title}</span>
          {hasWatch && (
            <span
              className="flex items-center gap-1 text-[11px]"
              title="붉은색 막대는 유의업종"
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: WATCH_COLOR }}
              />
              <span className="text-muted-foreground">유의업종</span>
            </span>
          )}
        </div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          총 {total}건 · {categoryCount}개 {unitLabel}
          {others && (
            <span className="ml-1 opacity-70">
              · 상위 {items.length - 1} + 기타 {others.count}
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex-1 min-h-0">
        <div style={{ width: "100%", height: chartHeight }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={items}
              layout="vertical"
              margin={{ top: 0, right: RIGHT_MARGIN_PX, bottom: 0, left: 0 }}
            >
              <XAxis type="number" hide allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="name"
                tickLine={false}
                axisLine={false}
                width={92}
                fontSize={11}
                stroke="var(--muted-foreground)"
                interval={0}
                tick={(props) => {
                  const p = props as {
                    x?: number | string;
                    y?: number | string;
                    payload?: { value?: string };
                  };
                  const name = p.payload?.value ?? "";
                  const isWatch = !!watchSet && watchSet.has(name);
                  return (
                    <text
                      x={p.x}
                      y={p.y}
                      dy={4}
                      textAnchor="end"
                      style={{
                        fontSize: 11,
                        fill: isWatch
                          ? WATCH_COLOR
                          : "var(--muted-foreground)",
                        fontWeight: isWatch ? 500 : 400,
                      }}
                    >
                      {name}
                    </text>
                  );
                }}
              />
              <Tooltip
                cursor={{ fill: "var(--accent)", opacity: 0.4 }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const it = payload[0]?.payload as DistItem | undefined;
                  if (!it) return null;
                  const pct =
                    it.pct ?? (total ? (it.value / total) * 100 : 0);
                  const isWatchItem =
                    !it.isOther && !!watchSet && watchSet.has(it.name);
                  return (
                    <div style={TOOLTIP_STYLE}>
                      <div className="flex items-center gap-1.5 font-medium tabular-nums">
                        {isWatchItem && (
                          <span
                            className="h-1.5 w-1.5 rounded-full"
                            style={{ background: WATCH_COLOR }}
                          />
                        )}
                        <span>
                          {it.isOther
                            ? `기타 ${it.members?.length ?? 0}개 ${unitLabel}`
                            : it.name}
                        </span>
                        {isWatchItem && (
                          <span
                            className="text-[10px] font-normal"
                            style={{ color: WATCH_COLOR }}
                          >
                            유의업종
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 text-[11px] text-muted-foreground tabular-nums">
                        {it.value}건 · {pct.toFixed(1)}%
                        {it.isOther && " · 각 1건"}
                      </div>
                      {it.isOther && it.members && it.members.length > 0 && (
                        <div className="mt-1.5 space-y-1 text-[11px] leading-relaxed">
                          {watchInOthers.length > 0 && (
                            <div>
                              <span style={{ color: WATCH_COLOR, fontWeight: 500 }}>
                                유의:
                              </span>{" "}
                              <span style={{ color: WATCH_COLOR }}>
                                {watchInOthers.join(", ")}
                              </span>
                            </div>
                          )}
                          <div>
                            <span className="text-muted-foreground">기타: </span>
                            {it.members
                              .filter((m) => !watchInOthers.includes(m))
                              .join(", ")}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
                {items.map((d) => {
                  const isWatchBar =
                    !d.isOther && !!watchSet && watchSet.has(d.name);
                  return (
                    <Cell
                      key={d.name}
                      fill={isWatchBar ? WATCH_COLOR : d.color}
                      stroke={d.isOther ? othersStroke() : undefined}
                      strokeWidth={d.isOther ? 1 : 0}
                      strokeDasharray={d.isOther ? "3 3" : undefined}
                    />
                  );
                })}
                <LabelList
                  dataKey="value"
                  position="right"
                  content={({ x, y, width, height, value, index }) => {
                    const i =
                      typeof index === "number" ? index : Number(index ?? 0);
                    const it = items[i];
                    if (!it) return null;
                    const num =
                      typeof value === "number"
                        ? value
                        : Number(value) || it.value;
                    const pct =
                      it.pct ?? (total ? (num / total) * 100 : 0);
                    const text = it.isOther
                      ? `${it.members?.length ?? 0}개 카테고리·${num}건·${pct.toFixed(1)}%`
                      : `${num}건·${pct.toFixed(1)}%`;
                    const tx = Number(x ?? 0) + Number(width ?? 0) + 6;
                    const ty = Number(y ?? 0) + Number(height ?? 0) / 2;
                    return (
                      <text
                        x={tx}
                        y={ty}
                        dominantBaseline="central"
                        style={{
                          fontSize: 10,
                          fill: "var(--muted-foreground)",
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {text}
                      </text>
                    );
                  }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

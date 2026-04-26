"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { Sidebar } from "./Sidebar";
import { MatrixTable } from "./MatrixTable";
import { KpiBar } from "./KpiBar";
import { DistributionRow } from "./DistributionRow";
import { applyFilters, emptyFilters } from "./types";
import type { CompaniesResponse } from "@/lib/api";

export function MatrixView({ data }: { data: CompaniesResponse }) {
  const [filters, setFilters] = useState(emptyFilters);
  const filtered = useMemo(() => applyFilters(data.rows, filters), [data.rows, filters]);
  // 단일 inner scroll 컨테이너 — 가로/세로 모두 이 안에서.
  // 가로 스크롤바가 컨테이너 하단(=viewport 하단)에 항상 위치 → "필요할 때 무조건 떠있음" 충족.
  const scrollRef = useRef<HTMLDivElement>(null);
  // Matrix 가 컨테이너 visible width 보다 넓을 때, KPI/Distribution/CountBar 가 가로 스크롤에
  // 함께 끌려가지 않도록 sticky-left:0 wrapper 로 고정. wrapper width 는 컨테이너 clientWidth 와 동기화.
  const [visibleWidth, setVisibleWidth] = useState(0);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const update = () => setVisibleWidth(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div className="flex flex-1 min-h-0 min-w-0">
      <Sidebar rows={data.rows} filters={filters} onChange={setFilters} />
      <div
        ref={scrollRef}
        className="flex-1 min-w-0 overflow-auto"
        style={{ contain: "strict" }}
      >
        {/* sticky-left:0 wrapper — 가로 스크롤 시에도 viewport 좌측에 고정.
            width 는 컨테이너 visible width 로 강제하여 matrix 의 totalWidth(2000px+)에 끌려가지 않게. */}
        <div
          className="sticky left-0 z-10 bg-background"
          style={{ width: visibleWidth || "100%" }}
        >
          <KpiBar
            kpis={data.kpis}
            rows={data.rows}
            periodLabel={data.period.current}
          />
          <DistributionRow rows={data.rows} />
          <div className="flex h-9 items-center gap-3 border-y bg-background px-4 text-xs text-muted-foreground">
            <span className="tabular-nums">
              {filtered.length} / {data.rows.length} 종목
            </span>
            {filters.query && (
              <span>
                · 검색 <span className="text-foreground">&quot;{filters.query}&quot;</span>
              </span>
            )}
          </div>
        </div>
        <MatrixTable
          rows={filtered}
          period={data.period as { current: string; previous: string }}
          hiddenColumns={filters.hiddenColumns}
        />
      </div>
    </div>
  );
}

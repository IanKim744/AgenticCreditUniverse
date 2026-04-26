"use client";

import { useMemo } from "react";
import { DistBarCard } from "./DistBarCard";
import type { CompanyRow } from "@/lib/api";

/**
 * 업종 분포 — 그룹사와 동일한 가로 바 카드.
 * 유의업종(industry_2026 === "O") 은 붉은색으로 표시 + 범례 노출.
 */
export function IndustryDistChart({ rows }: { rows: CompanyRow[] }) {
  // 데이터에서 유의업종으로 표시된 업종명 set 추출 (build_index 의 자동 판정 결과 그대로 활용).
  const watchSet = useMemo(() => {
    const s = new Set<string>();
    for (const r of rows) {
      if (r.industry_2026 === "O" && r.industry) {
        s.add(r.industry.trim());
      }
    }
    return s;
  }, [rows]);

  return (
    <DistBarCard
      title="업종 분포"
      unitLabel="업종"
      rows={rows}
      pickField={(r) => r.industry}
      fallback="미분류"
      watchSet={watchSet}
    />
  );
}

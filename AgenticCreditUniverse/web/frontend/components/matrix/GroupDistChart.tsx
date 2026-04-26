"use client";

import { DistBarCard } from "./DistBarCard";
import type { CompanyRow } from "@/lib/api";

export function GroupDistChart({ rows }: { rows: CompanyRow[] }) {
  return (
    <DistBarCard
      title="그룹사 분포"
      unitLabel="그룹사"
      rows={rows}
      pickField={(r) => r.group_name}
      fallback="독립계"
    />
  );
}

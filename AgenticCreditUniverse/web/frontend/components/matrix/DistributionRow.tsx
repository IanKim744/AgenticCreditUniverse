"use client";

import { motion } from "framer-motion";
import { RatingDistChart } from "./RatingDistChart";
import { IndustryDistChart } from "./IndustryDistChart";
import { GroupDistChart } from "./GroupDistChart";
import type { CompanyRow } from "@/lib/api";

// 카드 동일 높이.
const ROW_HEIGHT = 340;

export function DistributionRow({ rows }: { rows: CompanyRow[] }) {
  return (
    <div className="border-b bg-background/95">
      {/* KPI 4카드와 정렬 — 등급분포는 ①·② 위에 (col-span-2), 그룹사는 ③(의견변동) 위, 업종은 ④(검수) 위. */}
      <div className="mx-auto grid grid-cols-1 gap-3 px-6 py-3 lg:grid-cols-4">
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2, ease: "easeOut" }}
          style={{ height: ROW_HEIGHT }}
        >
          <RatingDistChart rows={rows} />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.25, ease: "easeOut" }}
          style={{ height: ROW_HEIGHT }}
        >
          <GroupDistChart rows={rows} />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3, ease: "easeOut" }}
          style={{ height: ROW_HEIGHT }}
        >
          <IndustryDistChart rows={rows} />
        </motion.div>
      </div>
    </div>
  );
}

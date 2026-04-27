"use client";

import { Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePrintMode } from "@/lib/print-mode";

export function PrintButton() {
  const { requestPrint } = usePrintMode();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={requestPrint}
      aria-label="인쇄"
      title="이 페이지의 모든 섹션을 인쇄합니다"
      className="print:hidden"
    >
      <Printer className="h-4 w-4" />
      인쇄
    </Button>
  );
}

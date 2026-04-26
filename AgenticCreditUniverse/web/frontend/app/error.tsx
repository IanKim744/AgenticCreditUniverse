"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 max-w-md">
        <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
        <h1 className="mt-3 text-base font-medium text-destructive">
          페이지를 불러오지 못했습니다
        </h1>
        <p className="mt-1 text-sm text-muted-foreground break-words">
          {error.message}
        </p>
        <Button onClick={reset} variant="outline" size="sm" className="mt-4">
          다시 시도
        </Button>
      </div>
    </main>
  );
}

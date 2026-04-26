import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
      <p className="text-4xl font-semibold tracking-tight text-muted-foreground tabular-nums">
        404
      </p>
      <h1 className="mt-2 text-lg font-medium">찾을 수 없는 페이지입니다</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        URL을 다시 확인하거나 매트릭스로 돌아가세요.
      </p>
      <Button asChild className="mt-4" variant="outline">
        <Link href="/">매트릭스로</Link>
      </Button>
    </main>
  );
}

import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="flex flex-col">
      <div className="h-14 border-b" />
      <main className="mx-auto max-w-7xl flex-1 px-6 py-8 space-y-6">
        <Skeleton className="h-24 w-full rounded-lg" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full rounded-lg" />
        ))}
      </main>
    </div>
  );
}

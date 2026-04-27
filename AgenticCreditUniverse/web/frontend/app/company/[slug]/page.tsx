import { notFound } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { DetailHeader } from "@/components/detail/DetailHeader";
import { ReviewActionPanel } from "@/components/detail/ReviewActionPanel";
import { FloatingTOC } from "@/components/detail/FloatingTOC";
import { Section1Overview } from "@/components/detail/Section1Overview";
import { Section2Financials } from "@/components/detail/Section2Financials";
import { Section3Opinion } from "@/components/detail/Section3Opinion";
import { Section4AIComment } from "@/components/detail/Section4AIComment";
import { Section5News } from "@/components/detail/Section5News";
import { Section6Disclosure } from "@/components/detail/Section6Disclosure";
import { Section7History } from "@/components/detail/Section7History";
import { fetchCompanyDetail } from "@/lib/api";
import { PrintModeProvider } from "@/lib/print-mode";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug: rawSlug } = await params;
  const slug = decodeURIComponent(rawSlug);
  const data = await fetchCompanyDetail(slug);
  if (!data) notFound();

  return (
    <PrintModeProvider>
      <AppHeader periodLabel={data.period.current} />
      <main className="mx-auto max-w-7xl flex-1 px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 lg:items-start print:block">
          <div className="min-w-0 space-y-8">
            <DetailHeader data={data} />
            <Section1Overview id="sec-overview" data={data} />
            <Section2Financials
              id="sec-financials"
              cfs={data.nice.cfs}
              ofs={data.nice.ofs}
            />
            <Section3Opinion
              id="sec-opinion"
              opinionPdfUrl={data.nice.opinion_pdf}
              opinionMeta={data.nice.opinion_meta ?? null}
              timeline={data.nice.rating_timeline}
            />
            <Section4AIComment
              id="sec-comment"
              period={data.period}
              commentCurr={data.comment?.comment ?? data.excel.comment_curr ?? null}
              commentPrev={data.excel.comment_prev ?? null}
            />
            <Section5News
              id="sec-news"
              reportMd={data.news.report_md}
              citations={data.news.citations}
            />
            <Section6Disclosure
              id="sec-dart"
              slug={slug}
              metadata={data.dart.metadata}
              reportUrl={data.dart.report_url}
              available={!!data.dart.available}
            />
            <Section7History id="sec-history" history={data.history ?? []} />
          </div>
          <aside className="hidden lg:block lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto space-y-6 print:hidden">
            <ReviewActionPanel
              slug={slug}
              ai={data.excel.universe_curr_ai}
              stage2={data.stage2}
              inversion={data.inversion}
              current={data.review_status}
            />
            <FloatingTOC />
          </aside>
        </div>
      </main>
    </PrintModeProvider>
  );
}

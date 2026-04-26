import { AppHeader } from "@/components/AppHeader";
import { MatrixView } from "@/components/matrix/MatrixView";
import { fetchCompanies } from "@/lib/api";

export default async function MatrixPage() {
  const data = await fetchCompanies();
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <AppHeader periodLabel={data.period.current} />
      <MatrixView data={data} />
    </div>
  );
}

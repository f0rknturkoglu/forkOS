import { PageFrame, PageHeader } from "@/core/ui";
import { StatisticsWidget } from "./StatisticsWidget";

/** Istatistik sayfasi -- widget'in genis gorunumu (Today'dekiyle ayni veri). */
export function StatisticsPage() {
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title="İstatistikler" />
      <StatisticsWidget />
    </PageFrame>
  );
}

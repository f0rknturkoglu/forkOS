import { WIDGETS } from "./widgets";
import { PageFrame, PageHeader } from "@/core/ui";

/** Genel saglik dashboard'u -- widget listesinden beslenir. */
export function HealthPage() {
  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Sistem" title="Sistem Durumu" />
      <p className="text-meta text-muted">Kaynaklar, beslemeler ve yedekler için tek bakışlık genel görünüm.</p>

      <div className="grid items-start gap-6 xl:grid-cols-2">
        {WIDGETS.map(({ name, component: Widget }) => (
          <Widget key={name} />
        ))}
      </div>
    </PageFrame>
  );
}

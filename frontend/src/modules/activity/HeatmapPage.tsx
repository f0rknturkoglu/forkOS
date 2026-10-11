import { useState } from "react";
import { Flame } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { PageFrame, Tabs } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { Heatmap } from "./Heatmap";
import { RANGES, type RangeId } from "./ranges";

/**
 * Isı Haritası sayfası (`/activity/heatmap`).
 *
 * Kullanıcı yıl/ay haritasını görmek için Etkinlik sayfasında aşağı kaydırmak
 * zorunda kalmasın diye ayrı ve derin bağlantılanabilir bir yüzey. Harita
 * bileşeni YENİDEN YAZILMADI: `Heatmap` (aynı sorgu anahtarı, aynı kare
 * davranışı) burada da kullanılır.
 *
 * Aralık seçimi Etkinlik sayfasıyla AYNI kaynaktan gelir (`RANGES`) ve URL'de
 * taşınır (`?range=6m`): bağlantı paylaşılabilir, geri/ileri çalışır.
 */
export function HeatmapPage() {
  const route = useHashRoute();
  const requested = route.params.get("range");
  const initial = RANGES.find((item) => item.id === requested)?.id ?? "1y";
  const [range, setRange] = useState<RangeId>(initial);
  const active = RANGES.find((item) => item.id === range) ?? RANGES[2];

  function changeRange(next: RangeId) {
    setRange(next);
    navigate(`/activity/heatmap?range=${next}`, { replace: true });
  }

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Etkinlik"
          title="Isı Haritası"
          hint={`${active.label} · kare tıklaması günü açar`}
          action={
            <a href="#/activity" className="text-meta text-accent hover:underline">
              Etkinlik akışı →
            </a>
          }
        >
          <Tabs
            value={range}
            onChange={(next) => changeRange(next as RangeId)}
            items={RANGES.map((item) => ({ id: item.id, label: item.label }))}
            ariaLabel="Harita aralığı"
          />
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="stack-y-3 p-3">
          <Heatmap days={active.days} />
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

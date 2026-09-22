import { allTodayStats, useTodayWidgetViews } from "@/core/registry";
import type { TodayWidgetView } from "@/core/registry";
import type { TodayPlacement } from "@/core/types";
import { Empty } from "@/core/ui";
import { WorkspaceBody, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { TodayHero } from "./TodayHero";

/** Widget kimlikleri ve görünürlük tercihleri registry'de kalır. */
function placement(view: TodayWidgetView): TodayPlacement {
  return view.widget.core ?? view.widget.placement ?? "context";
}

function widget(view: TodayWidgetView) {
  const Widget = view.widget.component;
  return (
    <div key={view.id} data-today-widget={view.id} className="min-w-0 empty:hidden">
      <Widget />
    </div>
  );
}

export function TodayPage() {
  const stats = allTodayStats();
  const views = useTodayWidgetViews();

  return (
    <WorkspaceScrollArea className="bg-canvas">
      <WorkspaceBody mode="full" className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
        <TodayHero />
        {stats.length > 0 && (
          <section
            aria-label="Günlük kısa özet"
            className="my-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-subtle pb-3 [&_.numeral]:font-sans [&_.numeral]:text-body [&_.numeral]:font-medium [&_.group]:flex [&_.group]:items-baseline [&_.group]:gap-1 [&_.group]:px-0 [&_.group]:py-0 [&_.text-meta]:mt-0 [&_.text-meta]:text-meta"
          >
            {stats.map((Tile, index) => (
              <Tile key={index} />
            ))}
          </section>
        )}
        {stats.length + views.length === 0 ? (
          <Empty variant="page" title="Bugün için yüzey yok">
            Ayarlar'dan modülleri açarak günün planını ve bağlamını görebilirsin.
          </Empty>
        ) : (
          <>
            <HomeGrid views={views} />
          </>
        )}
      </WorkspaceBody>
    </WorkspaceScrollArea>
  );
}

/** Ana iş solda, dikkat sağda; 850px'te aynı DOM sırası tek kolondur. */
export function HomeGrid({ views }: { views: TodayWidgetView[] }) {
  const by = (zone: TodayPlacement) => views.filter((view) => placement(view) === zone);
  const now = by("now");
  const plan = by("plan");
  const attention = by("attention");
  const context = by("context");

  return (
    <div className="space-y-7">
      {now.length > 0 && (
        <section aria-label="Şimdi" className="space-y-3">
          {now.map(widget)}
        </section>
      )}
      <div className="today-primary-grid grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.46fr)]">
        <section aria-label="Bugünün işi" className="min-w-0 max-w-4xl space-y-4">
          {plan.map(widget)}
        </section>
        {attention.length > 0 && (
          <aside
            aria-label="Dikkat isteyenler"
            className="today-attention min-w-0 space-y-4 lg:border-l lg:border-subtle lg:pl-6"
          >
            <h2 className="text-meta font-medium text-secondary">Dikkat isteyenler</h2>
            {attention.map(widget)}
          </aside>
        )}
      </div>
      {context.length > 0 && (
        <section aria-label="Bağlam" className="border-t border-subtle pt-5">
          <h2 className="mb-4 text-meta font-medium text-secondary">Bağlam</h2>
          <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(18rem,0.7fr)]">
            {context.map(widget)}
          </div>
        </section>
      )}
    </div>
  );
}

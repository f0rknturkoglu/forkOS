import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarPlus, Plus } from "lucide-react";
import { api } from "@/core/api";
import { Empty, Section, cx, identityClasses } from "@/core/ui";
import { navigate } from "@/app/router";
import { invalidateAfter } from "@/core/invalidation";
import { todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { consumptionBody } from "./MediaProgressActions";
import { Cover, KIND_LABELS, kindBg, mediaCoverUrl, progressPct, statusLabel } from "./shared";
import type { MediaItem, MediaPage } from "@/core/types";

export function MediaContinueWidget() {
  const online = useOnline();
  const { data } = useQuery({
    queryKey: ["media", "in_progress", "widget"],
    queryFn: () => api.get<MediaPage>("/media?status=in_progress&limit=8"),
  });
  const plan = useMutation({
    // PlanSlotIn.day ZORUNLU: gün gönderilmezse API 422 döner (regresyon testi var).
    mutationFn: (item: { id: string; title: string }) => api.post("/plan", { entity_id: item.id, day: todayKey() }),
    onSuccess: () => invalidateAfter("plan.write"),
  });
  // Widget'tan tek dokunusla +1 ilerleme; measure kaydin kendi olcusu.
  const quick = useMutation({
    mutationFn: (item: MediaItem) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, consumptionBody("quick", item)),
    onSuccess: () => invalidateAfter("media.write"),
  });
  const active = data?.items ?? [];

  return (
    <Section
      title="Devam eden medya"
      action={
        <button onClick={() => navigate("/media")} className="text-meta text-muted hover:text-primary">
          tümü →
        </button>
      }
    >
      {active.length === 0 ? (
        <Empty>Devam eden film/dizi/kitap yok.</Empty>
      ) : (
        <div className="flex gap-2.5 overflow-x-auto pb-1">
          {active.map((item) => {
            const pct = progressPct(item);
            // Backend cover_path'i "/api/media/assets/<dosya>" tam yoluyla saklar (sync._cache_artwork);
            // ham birleştirme çift prefix üretir — shared.mediaCoverUrl güvenli adı sıyırıp doğrular.
            const cover = mediaCoverUrl(item);
            return (
              <div key={item.id} className="w-28 shrink-0">
                <a
                  href={`#/media/${encodeURIComponent(item.id)}`}
                  aria-label={`${item.title} ayrıntısını aç`}
                  className="group block text-left"
                >
                  <span className="block overflow-hidden rounded-card border border-subtle bg-surface-sunken shadow-card transition group-hover:border-strong">
                    <span className="relative block aspect-[2/3] w-full overflow-hidden">
                      <span className="block h-full w-full transition-transform duration-300 group-hover:scale-[1.04]">
                        <Cover url={cover} title={item.title} size="h-full w-full" />
                      </span>
                      <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                      <span
                        className={cx(
                          "absolute left-1 top-1 rounded px-1 py-px text-micro bg-surface",
                          identityClasses("kind-" + item.kind),
                        )}
                      >
                        {statusLabel(item.kind, item.status)}
                      </span>
                      {pct !== null && (
                        <span className="absolute inset-x-1.5 bottom-1.5">
                          <span className="block h-[3px] w-full overflow-hidden rounded-full bg-white/25">
                            <span
                              className={cx("block h-full rounded-full", kindBg(item.kind))}
                              style={{ width: pct + "%" }}
                            />
                          </span>
                        </span>
                      )}
                    </span>
                  </span>
                  <span className="mt-1.5 block truncate text-meta text-primary">{item.title}</span>
                  <span className="block truncate text-micro text-muted">
                    {KIND_LABELS[item.kind] ?? item.kind}
                    {pct !== null && <> · %{pct}</>}
                  </span>
                </a>
                <button
                  type="button"
                  aria-label={`${item.title} kaydını bugüne ekle`}
                  title="Bugüne ekle"
                  disabled={!online || plan.isPending}
                  onClick={() => plan.mutate(item)}
                  className="mt-1.5 flex h-6 w-full items-center justify-center gap-1 rounded-control border border-subtle text-micro text-secondary transition hover:border-strong hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <CalendarPlus size={12} aria-hidden="true" /> Bugüne ekle
                </button>
                <button
                  type="button"
                  aria-label={`${item.title} için hızlı tüketim kaydet`}
                  title="Hızlı tüketim kaydet"
                  disabled={!online || quick.isPending}
                  onClick={() => quick.mutate(item)}
                  className="mt-1 flex h-6 w-full items-center justify-center gap-1 rounded-control border border-subtle text-micro text-secondary transition hover:border-strong hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Plus size={12} aria-hidden="true" /> Hızlı kaydet
                </button>
              </div>
            );
          })}
        </div>
      )}
    </Section>
  );
}

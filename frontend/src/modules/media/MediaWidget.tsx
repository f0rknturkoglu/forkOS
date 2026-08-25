import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import {Empty, Section, cx, identityClasses} from "@/core/ui";
import { navigate } from "@/app/router";
import {Cover, KIND_LABELS, kindBg, progressPct, statusLabel} from "./shared";
import type { MediaPage } from "@/core/types";

export function MediaContinueWidget() {
  const { data } = useQuery({
    queryKey: ["media", "in_progress", "widget"],
    queryFn: () => api.get<MediaPage>("/media?status=in_progress&limit=8"),
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
            const cover = item.cover_path
              ? `/api/media/assets/${item.cover_path}`
              : (item.cover_url ?? null);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => navigate(`/media?focus=${item.id}`)}
                className="group w-28 shrink-0 text-left"
              >
                <span className="block overflow-hidden rounded-card border border-subtle bg-surface-sunken shadow-card transition group-hover:border-strong">
                  <span className="relative block aspect-[2/3] w-full overflow-hidden">
                    <span className="block h-full w-full transition-transform duration-300 group-hover:scale-[1.04]">
                      <Cover url={cover} title={item.title} size="h-full w-full" />
                    </span>
                    <span className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                    <span className={cx("absolute left-1 top-1 rounded px-1 py-px text-micro bg-surface", identityClasses("kind-" + item.kind))}>
                      {statusLabel(item.kind, item.status)}
                    </span>
                    {pct !== null && (
                      <span className="absolute inset-x-1.5 bottom-1.5">
                        <span className="block h-[3px] w-full overflow-hidden rounded-full bg-white/25">
                          <span className={cx("block h-full rounded-full", kindBg(item.kind))} style={{ width: pct + "%" }} />
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
              </button>
            );
          })}
        </div>
      )}
    </Section>
  );
}

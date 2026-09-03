import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Bookmark, Pause, Pencil, Play, X } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { MediaDetail, MediaItem } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { Button, Chip, Field, Input, PageFrame, Section, Surface, Textarea, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { RelatedPanel } from "@/core/RelatedPanel";
import {
  KIND_LABELS,
  SiteLinks,
  externalLinks,
  mediaCoverUrl,
  mediaProvider,
  providerChip,
  providerLabel,
  statusLabel,
} from "./shared";
import { MediaProgressActions, measureLabel } from "./MediaProgressActions";

type MediaUnit = components["schemas"]["MediaUnitOut"];
type MediaCollection = components["schemas"]["MediaCollectionOut"];
type MediaConsumption = components["schemas"]["MediaConsumptionOut"];

function DetailCover({ item }: { item: MediaItem }) {
  const [broken, setBroken] = useState(false);
  const cover = mediaCoverUrl(item);
  const className = "aspect-[2/3] w-full rounded-card border border-subtle object-cover shadow-card";
  if (cover && !broken) {
    return <img src={cover} alt={`${item.title} kapağı`} onError={() => setBroken(true)} className={className} />;
  }
  return (
    <div
      role="img"
      aria-label={`${item.title} kapağı`}
      className={cx(
        className,
        "flex items-center justify-center bg-surface-sunken  text-display text-secondary",
      )}
    >
      {(item.title.trim().charAt(0) || "?").toUpperCase()}
    </div>
  );
}

function MetadataEditor({ item, online, onChanged }: { item: MediaItem; online: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [score, setScore] = useState(item.score == null ? "" : String(item.score));
  const [notes, setNotes] = useState(item.notes ?? "");
  const mutation = useMutation({
    mutationFn: (body: { score: number | null; notes: string | null }) =>
      api.patch(`/media/${encodeURIComponent(item.id)}`, body),
    onSuccess: () => {
      setEditing(false);
      onChanged();
    },
  });
  const disabled = !online || mutation.isPending;

  if (!editing) {
    return (
      <div className="space-y-3">
        <div>
          <p className="label-caps">Puan</p>
          <p className="mt-1 text-heading text-primary">{item.score == null ? "Puanlanmadı" : `${item.score} / 10`}</p>
        </div>
        <div>
          <p className="label-caps">Notlar</p>
          <p className="mt-1 whitespace-pre-wrap text-body text-secondary">{item.notes || "Not yok."}</p>
        </div>
        <Button size="sm" disabled={!online} onClick={() => setEditing(true)}>
          <Pencil size={13} aria-hidden="true" /> Puan ve notu düzenle
        </Button>
      </div>
    );
  }

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const parsedScore = score === "" ? null : Number(score);
        if (parsedScore !== null && (!Number.isInteger(parsedScore) || parsedScore < 0 || parsedScore > 10)) return;
        mutation.mutate({ score: parsedScore, notes: notes.trim() || null });
      }}
    >
      <Field label="Puan">
        <Input type="number" value={score} onChange={setScore} disabled={disabled} className="w-28" />
      </Field>
      <Field label="Notlar">
        <Textarea rows={4} value={notes} onChange={setNotes} />
      </Field>
      <div className="flex gap-2">
        <Button type="submit" size="sm" variant="primary" disabled={disabled}>
          Puan ve notu kaydet
        </Button>
        <Button size="sm" disabled={mutation.isPending} onClick={() => setEditing(false)}>
          Vazgeç
        </Button>
      </div>
      {mutation.error && (
        <p role="alert" className="text-meta text-danger">
          Puan ve notlar kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </form>
  );
}

const SUFFIX_BY_VOWEL: Record<string, string> = {
  a: "ı",
  e: "i",
  ı: "ı",
  i: "i",
  o: "u",
  ö: "ü",
  u: "u",
  ü: "ü",
};

function lastVowelSuffix(word: string): string {
  for (let index = word.length - 1; index >= 0; index -= 1) {
    const suffix = SUFFIX_BY_VOWEL[word[index]];
    if (suffix) return suffix;
  }
  return "i";
}

/** "bölüm" → "bölümü" (belirtme hali) — "Birinci bölümü tamamla" etiketi için. */
function accusative(word: string): string {
  return word + lastVowelSuffix(word);
}

/** "bölüm" → "bölümün" (tamlayan hali) — "…tamamlamasını geri al" etiketi için. */
function genitive(word: string): string {
  return word + lastVowelSuffix(word) + "n";
}

function UnitsSection({
  item,
  units,
  consumptions,
  online,
}: {
  item: MediaItem;
  units: MediaUnit[];
  consumptions: MediaConsumption[];
  online: boolean;
}) {
  const completedUnitIds = new Set(
    consumptions
      .filter((entry) => entry.action === "complete_unit" && entry.unit_id != null)
      .map((entry) => String(entry.unit_id)),
  );
  const mutation = useMutation({
    mutationFn: ({ unit, completed }: { unit: MediaUnit; completed: boolean }) =>
      api.post(`/media/${encodeURIComponent(item.id)}/consumptions`, {
        action: completed ? "uncomplete_unit" : "complete_unit",
        unit_id: unit.id,
        measure: unit.progress_measure ?? item.progress_measure ?? "item",
        client_uuid: crypto.randomUUID(),
      }),
    onSuccess: () => invalidateAfter("media.write"),
  });
  const topLevel = units.filter((unit) => !unit.parent_id);
  if (topLevel.length === 0) return null;

  return (
    <Section title="Bölümler">
      <ul className="divide-y divide-subtle">
        {topLevel.map((unit) => {
          const completed = completedUnitIds.has(unit.id);
          return (
            <li key={unit.id} className="flex flex-wrap items-center gap-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="truncate text-body font-medium text-primary">
                  {unit.number != null ? `${unit.number}. ` : ""}
                  {unit.title}
                </p>
                <p className="mt-0.5 text-meta text-muted">
                  {unit.unit_type}
                  {unit.duration_min != null ? ` · ${unit.duration_min} dk` : ""}
                </p>
              </div>
              <Button
                size="sm"
                variant={completed ? "secondary" : "primary"}
                disabled={!online || mutation.isPending}
                onClick={() => mutation.mutate({ unit, completed })}
              >
                {completed ? `${genitive(unit.title)} tamamlamasını geri al` : `${accusative(unit.title)} tamamla`}
              </Button>
            </li>
          );
        })}
      </ul>
      {mutation.error && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Bölüm durumu güncellenemedi: {mutation.error.message}
        </p>
      )}
    </Section>
  );
}

function CollectionMembership({
  itemId,
  collections,
  online,
}: {
  itemId: string;
  collections: MediaCollection[];
  online: boolean;
}) {
  const remove = useMutation({
    mutationFn: (collectionId: string) =>
      api.del(`/media/collections/${encodeURIComponent(collectionId)}/items/${encodeURIComponent(itemId)}`),
    onSuccess: () => invalidateAfter("media.write"),
  });
  if (collections.length === 0) return null;

  return (
    <Section title="Koleksiyonlar">
      <ul className="flex flex-wrap gap-2">
        {collections.map((collection) => (
          <li key={collection.id} className="flex items-center gap-1.5">
            <Chip variant="outline">{collection.title}</Chip>
            <button
              type="button"
              aria-label={`${collection.title} koleksiyonundan çıkar`}
              disabled={!online || remove.isPending}
              onClick={() => remove.mutate(collection.id)}
              className="flex h-6 w-6 items-center justify-center rounded border border-subtle text-muted transition hover:border-danger-border hover:bg-danger-surface hover:text-danger disabled:cursor-not-allowed disabled:opacity-50"
            >
              <X size={12} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      {remove.error && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Koleksiyondan çıkarılamadı: {remove.error.message}
        </p>
      )}
    </Section>
  );
}

export function MediaDetailPage() {
  const route = useHashRoute("/media/:id");
  const itemId = route.params.get("id");
  const online = useOnline();
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["media-detail", itemId],
    queryFn: () => api.get<MediaDetail>(`/media/${encodeURIComponent(itemId ?? "")}`),
    enabled: Boolean(itemId),
  });
  const refresh = () => invalidateAfter("media.write");
  const save = useSaveToLibrary();
  const startCycle = useMutation({
    mutationFn: () => api.post(`/media/${encodeURIComponent(itemId ?? "")}/cycles`, {}),
    onSuccess: () => invalidateAfter("media.write"),
  });
  // Aktif döngü duraklatma/devam ettirme: status PATCH'i cycle'ı backend'de
  // paused/active ile senkron tutar (service.update_item -> _synchronize_status).
  const setCycleStatus = useMutation({
    mutationFn: (status: "paused" | "in_progress") =>
      api.patch(`/media/${encodeURIComponent(itemId ?? "")}`, { status }),
    onSuccess: () => invalidateAfter("media.write"),
  });

  useEffect(() => {
    if (!itemId) return;
    const previousTitle = document.title;
    document.title = data?.item.title ? `${data.item.title} — forkOS` : "Medya detayı — forkOS";
    return () => {
      document.title = previousTitle;
    };
  }, [data?.item.title, itemId]);

  if (!itemId) {
    return (
      <PageFrame>
        <p className="text-body text-danger">Medya kimliği bulunamadı.</p>
      </PageFrame>
    );
  }
  if (isLoading) {
    return (
      <PageFrame>
        <p role="status" className="text-body text-muted">
          Medya yükleniyor…
        </p>
      </PageFrame>
    );
  }
  if (error || !data) {
    return (
      <PageFrame>
        <div role="alert" className="space-y-3 text-body text-danger">
          <p>Medya detayı yüklenemedi: {error?.message}</p>
          <Button
            disabled={isFetching}
            onClick={() => {
              void refetch();
            }}
          >
            Yeniden dene
          </Button>
        </div>
      </PageFrame>
    );
  }

  const item = data.item;
  const openCycle = data.cycles.find((cycle) => !cycle.completed_at) ?? null;
  const provider = mediaProvider(item);
  const sites = externalLinks(
    item.kind,
    item.title,
    item.meta ?? {},
    item.provider,
    item.provider_id,
    item.provider_ids,
  );
  const externalUrl = typeof item.meta?.url === "string" && item.meta.url ? item.meta.url : null;
  const progress = item.progress ?? 0;
  const progressText =
    item.total == null
      ? `${progress} ${measureLabel(item.progress_measure)}`
      : `${progress} / ${item.total} ${measureLabel(item.progress_measure)}`;

  return (
    <PageFrame className="space-y-5">
      <a href="#/media" className="inline-flex items-center gap-1.5 text-meta text-secondary hover:text-primary">
        <ArrowLeft size={14} aria-hidden="true" /> Medyaya dön
      </a>
      <div className="grid gap-6 lg:grid-cols-[minmax(220px,340px)_minmax(0,1fr)]">
        <div className="mx-auto w-full max-w-[340px] lg:mx-0">
          <DetailCover item={item} />
        </div>
        <div className="min-w-0 space-y-5">
          <header>
            <div className="flex flex-wrap items-center gap-2 text-meta">
              <Chip identity={"kind-" + item.kind} variant="outline">
                {KIND_LABELS[item.kind] ?? item.kind}
              </Chip>
              <span className="rounded border border-subtle px-2 py-0.5 text-secondary">
                {statusLabel(item.kind, item.status)}
              </span>
              {provider && (
                <span className={cx("rounded border px-2 py-0.5", providerChip(provider))}>
                  {providerLabel(provider)}
                </span>
              )}
            </div>
            <h1 className="mt-3  text-display text-primary">{item.title}</h1>
            {item.summary && <p className="mt-3 max-w-3xl text-body leading-6 text-secondary">{item.summary}</p>}
          </header>

          <div data-mobile-media-actions>
            <Surface className="p-4">
              <p className="label-caps">İlerleme</p>
              <p className="mt-1 numeral text-title text-primary">{progressText}</p>
              <div className="mt-4">
                <MediaProgressActions item={item} online={online} onChanged={() => undefined} />
              </div>
              {item.status !== "completed" && item.status !== "dropped" && (
                <div className="mt-3 border-t border-subtle pt-3">
                  {openCycle ? (
                    <>
                      <Button
                        size="sm"
                        disabled={!online || setCycleStatus.isPending}
                        onClick={() =>
                          setCycleStatus.mutate(openCycle.status === "paused" ? "in_progress" : "paused")
                        }
                      >
                        {openCycle.status === "paused" ? (
                          <>
                            <Play size={14} aria-hidden="true" /> Devam et
                          </>
                        ) : (
                          <>
                            <Pause size={14} aria-hidden="true" /> Duraklat
                          </>
                        )}
                      </Button>
                      {setCycleStatus.error && (
                        <p role="alert" className="mt-2 text-meta text-danger">
                          Döngü güncellenemedi: {setCycleStatus.error.message}
                        </p>
                      )}
                    </>
                  ) : (
                    <>
                      <Button
                        size="sm"
                        disabled={!online || startCycle.isPending}
                        onClick={() => startCycle.mutate()}
                      >
                        <Play size={14} aria-hidden="true" /> İzlemeye başla
                      </Button>
                      {startCycle.error && (
                        <p role="alert" className="mt-2 text-meta text-danger">
                          İzleme başlatılamadı: {startCycle.error.message}
                        </p>
                      )}
                    </>
                  )}
                </div>
              )}
            </Surface>
          </div>

          <Section title="Puan ve notlar">
            <MetadataEditor item={item} online={online} onChanged={refresh} />
          </Section>

          <UnitsSection item={item} units={data.units} consumptions={data.consumptions} online={online} />

          <CollectionMembership itemId={item.id} collections={data.collections} online={online} />

          <Section
            title="Kaynaklarda aç"
            action={
              externalUrl ? (
                <Button
                  size="sm"
                  disabled={!online}
                  onClick={() => {
                    void save.save({ url: externalUrl, title: item.title, collection: "reference" });
                  }}
                >
                  <Bookmark size={13} aria-hidden="true" /> Kaydet
                </Button>
              ) : undefined
            }
          >
            {sites.length ? (
              <SiteLinks links={sites} />
            ) : (
              <p className="text-body text-muted">Bu tür için kaynak kısayolu yok.</p>
            )}
          </Section>

          <RelatedPanel entityId={item.id} title="Bağlı kayıtlar" />
        </div>
      </div>
    </PageFrame>
  );
}

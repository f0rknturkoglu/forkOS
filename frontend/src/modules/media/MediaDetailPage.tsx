import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Pencil } from "lucide-react";
import { useHashRoute } from "@/app/router";
import { api } from "@/core/api";
import type { MediaDetail, MediaItem } from "@/core/types";
import {Button, Chip, Field, Input, PageFrame, Section, Surface, Textarea, cx} from "@/core/ui";
import {useOnline} from "@/lib/hooks";
import {KIND_LABELS, SiteLinks, externalLinks, mediaCoverUrl, mediaProvider, providerChip, providerLabel, statusLabel} from "./shared";
import { MediaProgressActions, measureLabel } from "./MediaProgressActions";

function DetailCover({ item }: { item: MediaItem }) {
  const [broken, setBroken] = useState(false);
  const cover = mediaCoverUrl(item);
  const className = "aspect-[2/3] w-full rounded-card border border-subtle object-cover shadow-card";
  if (cover && !broken) {
    return (
      <img
        src={cover}
        alt={`${item.title} kapağı`}
        onError={() => setBroken(true)}
        className={className}
      />
    );
  }
  return (
    <div role="img" aria-label={`${item.title} kapağı`} className={cx(className, "flex items-center justify-center bg-surface-sunken font-serif text-display text-secondary")}>
      {(item.title.trim().charAt(0) || "?").toUpperCase()}
    </div>
  );
}

function MetadataEditor({ item, online, onChanged }: {
  item: MediaItem;
  online: boolean;
  onChanged: () => void;
}) {
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
        <Input
          type="number"
          value={score}
          onChange={setScore}
          disabled={disabled}
          className="w-28"
        />
      </Field>
      <Field label="Notlar">
        <Textarea rows={4} value={notes} onChange={setNotes} />
      </Field>
      <div className="flex gap-2">
        <Button type="submit" size="sm" variant="primary" disabled={disabled}>Puan ve notu kaydet</Button>
        <Button size="sm" disabled={mutation.isPending} onClick={() => setEditing(false)}>Vazgeç</Button>
      </div>
      {mutation.error && (
        <p role="alert" className="text-meta text-danger">
          Puan ve notlar kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </form>
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

  useEffect(() => {
    if (!itemId) return;
    const previousTitle = document.title;
    document.title = data?.item.title ? `${data.item.title} — forkOS` : "Medya detayı — forkOS";
    return () => { document.title = previousTitle; };
  }, [data?.item.title, itemId]);

  if (!itemId) {
    return <PageFrame><p className="text-body text-danger">Medya kimliği bulunamadı.</p></PageFrame>;
  }
  if (isLoading) {
    return <PageFrame><p role="status" className="text-body text-muted">Medya yükleniyor…</p></PageFrame>;
  }
  if (error || !data) {
    return (
      <PageFrame>
        <div role="alert" className="space-y-3 text-body text-danger">
          <p>Medya detayı yüklenemedi: {error?.message}</p>
          <Button disabled={isFetching} onClick={() => { void refetch(); }}>Yeniden dene</Button>
        </div>
      </PageFrame>
    );
  }

  const item = data.item;
  const provider = mediaProvider(item);
  const sites = externalLinks(item.kind, item.title, item.meta ?? {}, item.provider, item.provider_id, item.provider_ids);
  const progress = item.progress ?? 0;
  const progressText = item.total == null
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
              <Chip identity={"kind-" + item.kind} variant="outline">{KIND_LABELS[item.kind] ?? item.kind}</Chip>
              <span className="rounded border border-subtle px-2 py-0.5 text-secondary">{statusLabel(item.kind, item.status)}</span>
              {provider && <span className={cx("rounded border px-2 py-0.5", providerChip(provider))}>{providerLabel(provider)}</span>}
            </div>
            <h1 className="mt-3 font-serif text-display text-primary">{item.title}</h1>
            {item.summary && <p className="mt-3 max-w-3xl text-body leading-6 text-secondary">{item.summary}</p>}
          </header>

          <Surface className="p-4">
            <p className="label-caps">İlerleme</p>
            <p className="mt-1 numeral text-title text-primary">{progressText}</p>
            <div className="mt-4">
              <MediaProgressActions item={item} online={online} onChanged={() => undefined} />
            </div>
          </Surface>

          <Section title="Puan ve notlar">
            <MetadataEditor item={item} online={online} onChanged={refresh} />
          </Section>

          <Section title="Kaynaklarda aç">
            {sites.length ? <SiteLinks links={sites} /> : <p className="text-body text-muted">Bu tür için kaynak kısayolu yok.</p>}
          </Section>
        </div>
      </div>
    </PageFrame>
  );
}

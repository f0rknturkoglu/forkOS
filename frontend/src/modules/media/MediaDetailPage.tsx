import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bookmark,
  Heart,
  ListChecks,
  Pause,
  Play,
  Quote,
  RefreshCw,
  StickyNote,
  Timer,
  X,
} from "lucide-react";

import { navigate, useHashRoute } from "@/app/router";
import { api, qs } from "@/core/api";
import { linkEntities } from "@/core/links";
import { createTask, invalidateTaskWrite } from "@/core/tasks";
import type { MediaDetail, MediaItem, MediaProviderStatus, Note } from "@/core/types";
import type { components } from "@/generated/api-schema";
import {
  Button,
  Checkbox,
  Chip,
  Field,
  IconButton,
  Input,
  Modal,
  PageFrame,
  Section,
  Surface,
  Textarea,
  cx,
  relativeTime,
  useToast,
} from "@/core/ui";
import { formatTrDate } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { BacklinksPanel } from "@/core/BacklinksPanel";
import { RelatedPanel } from "@/core/RelatedPanel";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { openPomodoro } from "@/modules/pomodoro/dock";
import {
  KIND_LABELS,
  SiteLinks,
  externalLinks,
  mediaCoverUrl,
  mediaProvider,
  progressPct,
  providerChip,
  providerLabel,
  statusLabel,
} from "./shared";
import { MediaProgressActions, kindLanguage, measureLabel } from "./MediaProgressActions";
import { RatingPicker } from "./RatingPicker";
import { UnitTree } from "./UnitTree";
import { ConsumptionHistory } from "./ConsumptionHistory";
import { HighlightDialog } from "./HighlightDialog";
import { CollectionPicker } from "./CollectionPicker";

type MediaCollection = components["schemas"]["MediaCollectionOut"];

const OWNERSHIP_LABELS: Record<string, string> = {
  condition: "Durum",
  edition: "Baskı",
  format: "Biçim",
  location: "Konum",
  physical: "Fiziksel kopya",
  platform: "Platform",
  price: "Fiyat",
  purchased_at: "Alındığı tarih",
  store: "Mağaza",
};

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
      className={cx(className, "flex items-center justify-center bg-surface-sunken  text-display text-secondary")}
    >
      {(item.title.trim().charAt(0) || "?").toUpperCase()}
    </div>
  );
}

/**
 * Dekoratif backdrop: sayfayi itmez (`absolute`, negatif katman), okunurluk
 * icin alta dogru saydamlasan katman tasir. Gorsel yoksa hic cizilmez.
 */
function Backdrop({ item }: { item: MediaItem }) {
  const [broken, setBroken] = useState(false);
  // `backdrop_path` cover_path ile ayni kurallara tabidir (ciplak ad ya da
  // hazir asset URL'i); cozumleme tek yerde kalsin diye kapak cozucu kullanilir.
  const url = mediaCoverUrl({ cover_path: item.backdrop_path ?? null, cover_url: item.backdrop_url ?? null, meta: {} });
  if (!url || broken) return null;
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-40 overflow-hidden sm:h-56">
      <img src={url} alt="" onError={() => setBroken(true)} className="h-full w-full object-cover opacity-40" />
      {/* Okunurluk katmani: token renkleriyle asagi dogru saydamlasir.
          Token renkleri `var(--x)` oldugu icin `/opaklik` eki DERLENMEZ;
          iki duraklı gradyan kullanilir. */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-canvas" />
    </div>
  );
}

function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="label-caps">{label}</dt>
      <dd className="mt-0.5 break-words text-body text-secondary">{children}</dd>
    </div>
  );
}

/** Not ve inceleme alanlari ayni davranisi paylasir: yaz, kaydet, bosalt. */
function EditableText({
  itemId,
  field,
  label,
  saveLabel,
  value,
  rows,
  online,
}: {
  itemId: string;
  field: "notes" | "review";
  label: string;
  saveLabel: string;
  value: string | null | undefined;
  rows: number;
  online: boolean;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState(value ?? "");
  const mutation = useMutation({
    mutationFn: (next: string | null) => api.patch(`/media/${encodeURIComponent(itemId)}`, { [field]: next }),
    onSuccess: () => invalidateAfter("media.write"),
    onError: (error: Error) => toast.push(error.message, { tone: "danger" }),
  });

  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);

  const dirty = draft.trim() !== (value ?? "").trim();

  return (
    <div className="space-y-2">
      <Textarea
        rows={rows}
        value={draft}
        onChange={setDraft}
        disabled={!online || mutation.isPending}
        ariaLabel={label}
        placeholder={label}
      />
      <Button
        size="sm"
        disabled={!online || mutation.isPending || !dirty}
        onClick={() => mutation.mutate(draft.trim() || null)}
      >
        {saveLabel}
      </Button>
      {mutation.error && (
        <p role="alert" className="text-meta text-danger">
          {label} kaydedilemedi: {mutation.error.message}
        </p>
      )}
    </div>
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

  return (
    <Section
      title="Koleksiyonlar"
      action={
        <CollectionPicker
          itemId={itemId}
          currentIds={collections.map((collection) => collection.id)}
          onChanged={() => undefined}
        />
      }
    >
      {collections.length === 0 ? (
        <p className="text-body text-muted">Bu kayıt henüz bir koleksiyonda değil.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {collections.map((collection) => (
            <li key={collection.id} className="flex items-center gap-1.5">
              <Chip variant="outline">{collection.title}</Chip>
              <IconButton
                title={`${collection.title} koleksiyonundan çıkar`}
                disabled={!online || remove.isPending}
                onClick={() => remove.mutate(collection.id)}
              >
                <X size={12} aria-hidden="true" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}
      {remove.error && (
        <p role="alert" className="mt-2 text-meta text-danger">
          Koleksiyondan çıkarılamadı: {remove.error.message}
        </p>
      )}
    </Section>
  );
}

/**
 * "Not oluştur": medyada IKINCI bir editor acmadan baslangic metnini alir,
 * notu kayda baglar ve Notlar modulunde acar (`/notes?focus=<id>`).
 */
function NoteComposer({ item, open, onClose }: { item: MediaItem; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const online = useOnline();
  const [title, setTitle] = useState("");
  const [firstLine, setFirstLine] = useState("");
  const body = [title.trim(), firstLine.trim()].filter(Boolean).join("\n\n");
  const create = useMutation({
    mutationFn: () => api.post<Note>("/notes", { body, relate_to: item.id }),
    onSuccess: (note) => {
      invalidateAfter("note.write");
      onClose();
      navigate(`/notes?focus=${encodeURIComponent(note.id)}`);
    },
    onError: (error: Error) => toast.push(error.message, { tone: "danger" }),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Not oluştur"
      hint={item.title}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button size="sm" onClick={onClose} disabled={create.isPending}>
            Vazgeç
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={!online || create.isPending || body.length === 0}
            onClick={() => create.mutate()}
          >
            Notu oluştur ve aç
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        <Field label="Not başlığı">
          <Input
            value={title}
            onChange={setTitle}
            autoFocus
            disabled={create.isPending}
            ariaLabel="Not başlığı"
            placeholder={`${item.title} notları`}
            className="w-full"
          />
        </Field>
        <Field label="İlk satır" hint="Başlık ve ilk satır boşsa not oluşturulamaz.">
          <Textarea
            rows={4}
            value={firstLine}
            onChange={setFirstLine}
            disabled={create.isPending}
            ariaLabel="İlk satır"
            placeholder="Aklında kalan ilk şey…"
          />
        </Field>
      </div>
    </Modal>
  );
}

/** "Görev oluştur": gorev ortak intent katmanindan gecer (Faz 17), sonra kayda baglanir. */
function TodoComposer({ item, open, onClose }: { item: MediaItem; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const online = useOnline();
  const [title, setTitle] = useState(`${item.title} — `);
  const description = `${KIND_LABELS[item.kind] ?? item.kind} · ${item.title}`;
  const create = useMutation({
    mutationFn: async () => {
      const todo = await createTask({ title: title.trim(), description });
      // Ortak iliski yardimcisi: tazeleme tek yerden (kural 14).
      await linkEntities(todo.id, item.id);
      return todo;
    },
    onSuccess: () => {
      invalidateTaskWrite();
      toast.push("Görev oluşturuldu ve kayda bağlandı.", { tone: "ok" });
      onClose();
    },
    onError: (error: Error) => toast.push(error.message, { tone: "danger" }),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Görev oluştur"
      hint={item.title}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button size="sm" onClick={onClose} disabled={create.isPending}>
            Vazgeç
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={!online || create.isPending || title.trim().length === 0}
            onClick={() => create.mutate()}
          >
            Görevi oluştur
          </Button>
        </div>
      }
    >
      <Field label="Görev başlığı">
        <Input
          value={title}
          onChange={setTitle}
          autoFocus
          disabled={create.isPending}
          ariaLabel="Görev başlığı"
          placeholder="ör. Dune: Prophecy 4. bölümü izle"
          className="w-full"
        />
      </Field>
    </Modal>
  );
}

export function MediaDetailPage() {
  const route = useHashRoute("/media/:id");
  const itemId = route.params.get("id");
  const online = useOnline();
  const toast = useToast();
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["media-detail", itemId],
    queryFn: () => api.get<MediaDetail>(`/media/${encodeURIComponent(itemId ?? "")}`),
    enabled: Boolean(itemId),
  });
  const providers = useQuery({
    queryKey: ["media-providers"],
    queryFn: () => api.get<MediaProviderStatus[]>("/media/providers"),
  });
  const refresh = () => invalidateAfter("media.write");
  const save = useSaveToLibrary();
  const [noteOpen, setNoteOpen] = useState(false);
  const [todoOpen, setTodoOpen] = useState(false);
  const [highlightOpen, setHighlightOpen] = useState(false);

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
  const favorite = useMutation({
    mutationFn: (next: boolean) => api.patch(`/media/${encodeURIComponent(itemId ?? "")}`, { favorite: next }),
    onSuccess: () => invalidateAfter("media.write"),
    onError: (mutationError: Error) => toast.push(mutationError.message, { tone: "danger" }),
  });
  const tracking = useMutation({
    mutationFn: (next: boolean) => api.patch(`/media/${encodeURIComponent(itemId ?? "")}`, { monitored: next }),
    onSuccess: () => invalidateAfter("media.write"),
    onError: (mutationError: Error) => toast.push(mutationError.message, { tone: "danger" }),
  });
  const sync = useMutation({
    mutationFn: () => api.post(`/media/sync${qs({ item_id: itemId })}`),
    onSuccess: () => {
      invalidateAfter("media.write");
      toast.push("Metadata yenileme kuyruğa alındı.", { tone: "ok" });
    },
    onError: (mutationError: Error) => toast.push(mutationError.message, { tone: "danger" }),
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
  const language = kindLanguage(item.kind);
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
  const pct = progressPct(item);
  const originalTitle = typeof item.meta?.original_title === "string" ? item.meta.original_title : null;
  const year = item.release_date ? item.release_date.slice(0, 4) : null;
  const unitTitles = Object.fromEntries(data.units.map((unit) => [unit.id, unit.title]));
  const ownership = Object.entries(item.ownership ?? {});
  const providerStatus = (providers.data ?? []).find((entry) => entry.id === provider) ?? null;
  const trackingReason = !provider
    ? "Bu kayıtta sağlayıcı yok; yeni yayın takibi açılamaz."
    : providerStatus?.capabilities.upcoming === false
      ? `${providerLabel(provider)} yeni yayın bilgisi sağlamıyor.`
      : null;
  const syncReason = !online
    ? "Çevrimdışıyken metadata yenilenemez."
    : !item.monitored
      ? "Önce yeni yayın takibini aç"
      : !provider
        ? "Bu kayıtta sağlayıcı tanımlı değil."
        : null;
  const syncStatus = data.sync;
  const syncText = !syncStatus
    ? "Bu kayıt için henüz yenileme kaydı yok."
    : syncStatus.status === "running"
      ? "Yenileme sürüyor…"
      : syncStatus.status === "ok"
        ? `Son yenileme başarılı${syncStatus.items_found != null ? ` · ${syncStatus.items_found} kayıt bulundu` : ""}`
        : syncStatus.status === "empty"
          ? "Son yenileme boş döndü."
          : syncStatus.status === "error"
            ? "Son yenileme hatalı."
            : "Henüz yenilenmedi.";

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Medya"
          title={item.title}
          hint="Kayıt ayrıntısı"
          wrapTitle
          action={
            <a href="#/media" className="inline-flex items-center gap-1.5 text-meta text-secondary hover:text-primary">
              <ArrowLeft size={14} aria-hidden="true" /> Kütüphaneye dön
            </a>
          }
        />
        <WorkspaceScrollArea className="p-3">
          <div className="relative space-y-5">
            <Backdrop item={item} />

            <div className="grid gap-5 sm:grid-cols-[180px_minmax(0,1fr)] lg:grid-cols-[220px_minmax(0,1fr)]">
              {/* Mobilde tek sutun; baslik/ilerleme/eylemler ilk ekranda kalsin
                  diye kapak ALTTA kalir (sm ve uzerinde solda durur). */}
              <div className="order-2 mx-auto w-[180px] sm:order-1 sm:mx-0 sm:w-full">
                <DetailCover item={item} />
              </div>
              <div className="order-1 min-w-0 space-y-4 sm:order-2">
                <header className="space-y-2">
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      {originalTitle && <p className="text-meta text-muted">{originalTitle}</p>}
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-meta">
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
                        {year && (
                          <span className="rounded border border-subtle px-2 py-0.5 text-secondary">{year}</span>
                        )}
                      </div>
                    </div>
                    <IconButton
                      title={item.favorite ? "Favorilerden çıkar" : "Favorilere ekle"}
                      disabled={!online || favorite.isPending}
                      onClick={() => favorite.mutate(!item.favorite)}
                      className={cx(item.favorite && "border-danger-border text-danger")}
                    >
                      <Heart size={15} aria-hidden="true" fill={item.favorite ? "currentColor" : "none"} />
                    </IconButton>
                  </div>
                  {item.summary && <p className="max-w-3xl text-body leading-6 text-secondary">{item.summary}</p>}
                </header>

                <div data-mobile-media-actions>
                  <Surface className="p-4">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <p className="label-caps">İlerleme</p>
                      <p className="numeral text-title text-primary">{progressText}</p>
                    </div>
                    {pct != null && (
                      <div
                        role="progressbar"
                        aria-label={`${item.title} ilerlemesi`}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={pct}
                        className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-sunken"
                      >
                        <span className="block h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
                      </div>
                    )}
                    <div className="mt-4">
                      <MediaProgressActions item={item} online={online} onChanged={refresh} />
                    </div>
                    {item.status !== "completed" && item.status !== "dropped" && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-subtle pt-3">
                        {openCycle ? (
                          <Button
                            size="sm"
                            disabled={!online || setCycleStatus.isPending}
                            onClick={() =>
                              setCycleStatus.mutate(openCycle.status === "paused" ? "in_progress" : "paused")
                            }
                          >
                            {openCycle.status === "paused" ? (
                              <>
                                <Play size={14} aria-hidden="true" /> {language.resume}
                              </>
                            ) : (
                              <>
                                <Pause size={14} aria-hidden="true" /> Duraklat
                              </>
                            )}
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            disabled={!online || startCycle.isPending}
                            onClick={() => startCycle.mutate()}
                          >
                            <Play size={14} aria-hidden="true" /> {language.start}
                          </Button>
                        )}
                      </div>
                    )}
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-subtle pt-3">
                      <Button
                        size="sm"
                        disabled={!online}
                        onClick={() => openPomodoro({ context: item.id, topic: item.title })}
                      >
                        <Timer size={13} aria-hidden="true" /> {language.session}
                      </Button>
                    </div>
                    {setCycleStatus.error && (
                      <p role="alert" className="mt-2 text-meta text-danger">
                        Döngü güncellenemedi: {setCycleStatus.error.message}
                      </p>
                    )}
                    {startCycle.error && (
                      <p role="alert" className="mt-2 text-meta text-danger">
                        İzleme başlatılamadı: {startCycle.error.message}
                      </p>
                    )}
                  </Surface>
                </div>
              </div>
            </div>

            <Section title="Kayıt bilgileri">
              <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                <InfoRow label="Ölçü">{measureLabel(item.progress_measure)}</InfoRow>
                <InfoRow label="Toplam">
                  {item.total == null ? "—" : `${item.total} ${measureLabel(item.progress_measure)}`}
                </InfoRow>
                <InfoRow label="Çıkış tarihi">{item.release_date ? formatTrDate(item.release_date) : "—"}</InfoRow>
                <InfoRow label="Başlandı">{item.started_at ? formatTrDate(item.started_at) : "—"}</InfoRow>
                <InfoRow label="Tamamlandı">{item.finished_at ? formatTrDate(item.finished_at) : "—"}</InfoRow>
                <InfoRow label="Son eşitleme">{item.last_synced_at ? relativeTime(item.last_synced_at) : "—"}</InfoRow>
                <InfoRow label="Sağlayıcı">
                  {provider ? `${providerLabel(provider)}${item.provider_id ? ` · ${item.provider_id}` : ""}` : "—"}
                </InfoRow>
                <InfoRow label="Yeni yayın takibi">{item.monitored ? "Açık" : "Kapalı"}</InfoRow>
              </dl>
            </Section>

            <Section title="Puan ve notlar">
              <div className="space-y-4">
                <RatingPicker item={item} online={online} />
                <div className="border-t border-subtle pt-4">
                  <EditableText
                    itemId={item.id}
                    field="notes"
                    label="Notlar"
                    saveLabel="Notları kaydet"
                    value={item.notes}
                    rows={4}
                    online={online}
                  />
                </div>
                <div className="border-t border-subtle pt-4">
                  <EditableText
                    itemId={item.id}
                    field="review"
                    label="İnceleme"
                    saveLabel="İncelemeyi kaydet"
                    value={item.review}
                    rows={3}
                    online={online}
                  />
                </div>
              </div>
            </Section>

            <Section title="Sahiplik">
              <div className="flex flex-wrap items-center gap-2">
                <Chip variant="outline" tone={item.owned ? "ok" : "neutral"}>
                  {item.owned ? "Elimde" : "Elimde değil"}
                </Chip>
              </div>
              {ownership.length === 0 ? (
                <p className="mt-2 text-body text-muted">—</p>
              ) : (
                <dl className="mt-3 grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                  {ownership.map(([key, entry]) => (
                    <InfoRow key={key} label={OWNERSHIP_LABELS[key] ?? key}>
                      {typeof entry === "object" && entry !== null ? JSON.stringify(entry) : String(entry ?? "—")}
                    </InfoRow>
                  ))}
                </dl>
              )}
            </Section>

            <UnitTree item={item} units={data.units} consumptions={data.consumptions} online={online} />

            <ConsumptionHistory itemId={item.id} unitTitles={unitTitles} />

            <CollectionMembership itemId={item.id} collections={data.collections} online={online} />

            <Section title="Takip ve senkronizasyon">
              <div className="space-y-3">
                <div>
                  <Checkbox
                    checked={item.monitored}
                    onChange={(next) => tracking.mutate(next)}
                    disabled={!online || tracking.isPending || Boolean(trackingReason)}
                    label="Yeni yayınları takip et"
                  />
                  <p className="mt-1 text-meta text-muted">
                    {trackingReason ?? "Açıkken yeni bölüm/parça yayınları Yaklaşanlar listesine düşer."}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 border-t border-subtle pt-3">
                  <Button
                    size="sm"
                    disabled={!online || sync.isPending || Boolean(syncReason)}
                    onClick={() => sync.mutate()}
                  >
                    <RefreshCw size={13} aria-hidden="true" /> Metadata'yı yenile
                  </Button>
                  <p role="status" className="text-meta text-muted">
                    {syncStatus?.last_run_at ? `${syncText} · ${relativeTime(syncStatus.last_run_at)}` : syncText}
                  </p>
                </div>
                {syncReason && <p className="text-meta text-muted">{syncReason}</p>}
                {syncStatus?.last_error && (
                  <p role="alert" className="text-meta text-danger">
                    Son hata: {syncStatus.last_error}
                  </p>
                )}
              </div>
            </Section>

            <Section title="Eylemler">
              <div className="flex flex-wrap gap-2">
                <Button size="sm" disabled={!online} onClick={() => setNoteOpen(true)}>
                  <StickyNote size={13} aria-hidden="true" /> Not oluştur
                </Button>
                <Button size="sm" disabled={!online} onClick={() => setHighlightOpen(true)}>
                  <Quote size={13} aria-hidden="true" /> Alıntı ekle
                </Button>
                <Button size="sm" disabled={!online} onClick={() => setTodoOpen(true)}>
                  <ListChecks size={13} aria-hidden="true" /> Görev oluştur
                </Button>
              </div>
            </Section>

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

            <BacklinksPanel entityId={item.id} />

            <RelatedPanel entityId={item.id} title="Bağlı kayıtlar" />
          </div>
        </WorkspaceScrollArea>
      </Workspace>

      <NoteComposer item={item} open={noteOpen} onClose={() => setNoteOpen(false)} />
      <TodoComposer item={item} open={todoOpen} onClose={() => setTodoOpen(false)} />
      <HighlightDialog item={item} open={highlightOpen} onClose={() => setHighlightOpen(false)} />
    </PageFrame>
  );
}

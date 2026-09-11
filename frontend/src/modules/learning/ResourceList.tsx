/**
 * Konunun kaynaklari: ekle / duzenle / sil / sirala / tamamla + ilerleme.
 *
 * Ilerleme yuzdesi BURADA HESAPLANMAZ -- backend kaynak sayacindan turetir
 * (alt konular dahil). Boylece agactaki yuzde ile detaydaki yuzde ayrisamaz.
 * Ayni sozlesme `TopicProgressBar` ile konu detayinin olcu seridinde de
 * kullanilir; bar tek yerden cizilir ki iki yuzey ayrisamasin.
 *
 * Sirala: surukle-birak YOK. Iki komsu satirin `position`'i tek adimda takas
 * edilir (klavye erisilebilir yukari/asagi dugmeleri).
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  BookmarkPlus,
  Dumbbell,
  ExternalLink,
  FileText,
  GraduationCap,
  Link2,
  Pencil,
  Plus,
  Trash2,
  Video,
} from "lucide-react";
import { api, qs } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { safeHref } from "@/core/markdownParser";
import { useHashRoute } from "@/app/router";
import {
  Button,
  Chip,
  Empty,
  Field,
  IconButton,
  Input,
  Modal,
  NumberInput,
  RowList,
  SectionHeader,
  Select,
  SkeletonRows,
  Textarea,
  cx,
  hostOf,
  useToast,
} from "@/core/ui";
import type { Bookmark } from "@/core/types";
import type { components } from "@/generated/api-schema";
import { useDebounced, useOnline } from "@/lib/hooks";

type ResourceOut = components["schemas"]["ResourceOut"];
type TopicProgressOut = components["schemas"]["TopicProgressOut"];

/** Backend `RESOURCE_KINDS` ile ayni kume (schemas.py). */
const RESOURCE_KINDS = [
  { id: "link", label: "Bağlantı", icon: Link2 },
  { id: "video", label: "Video", icon: Video },
  { id: "article", label: "Makale", icon: FileText },
  { id: "course", label: "Kurs", icon: GraduationCap },
  { id: "book", label: "Kitap", icon: BookOpen },
  { id: "doc", label: "Doküman", icon: FileText },
  { id: "exercise", label: "Alıştırma", icon: Dumbbell },
] as const;

const NO_KIND = RESOURCE_KINDS[0];

/** Konu kaynak ilerlemesi; backend `progress_pct` degeri cizilir. */
export function TopicProgressBar({
  done,
  total,
  pct,
  label,
}: {
  done: number;
  total: number;
  pct: number;
  label: string;
}) {
  const complete = total > 0 && done === total;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3 text-meta">
        <span className="text-secondary">{label}</span>
        <span className={cx("numeral font-medium", complete ? "text-ok" : "text-primary")}>
          {done}/{total} · %{pct}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={`${done}/${total} kaynak`}
        className="h-2 overflow-hidden rounded-control bg-surface-sunken"
      >
        <div
          className={cx(
            "h-full rounded-control transition-all motion-reduce:transition-none",
            complete ? "bg-ok" : "bg-accent",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

interface ResourceForm {
  title: string;
  url: string;
  kind: string;
  note: string;
  estimatedMin: number;
}

const EMPTY_FORM: ResourceForm = { title: "", url: "", kind: "link", note: "", estimatedMin: 0 };

/** Formu API govdesine cevirir. Bos alanlar `null` gider (bos string degil). */
export function resourceBody(form: ResourceForm) {
  return {
    title: form.title.trim(),
    url: form.url.trim() || null,
    kind: form.kind,
    note: form.note.trim() || null,
    estimated_min: form.estimatedMin > 0 ? form.estimatedMin : null,
  };
}

/**
 * Iki komsu kaynagin `position` takasi. Konumlar esitse (eski veri) hedefin
 * bir adim otesine yazilir -- aksi halde takas gorunurde hicbir sey degistirmez.
 */
export function swapPositions(
  items: { id: string; position: number }[],
  index: number,
  delta: number,
): { id: string; position: number }[] {
  const item = items[index];
  const neighbour = items[index + delta];
  if (!item || !neighbour) return [];
  if (item.position === neighbour.position) {
    return [
      { id: item.id, position: neighbour.position + delta },
      { id: neighbour.id, position: neighbour.position },
    ];
  }
  return [
    { id: item.id, position: neighbour.position },
    { id: neighbour.id, position: item.position },
  ];
}

/** Ekleme/duzenleme formu. Yer imi secimi yalnizca EKLEME modunda cikar. */
function ResourceFormFields({
  form,
  onChange,
  locked,
  bookmarkPicker,
}: {
  form: ResourceForm;
  onChange: (next: ResourceForm) => void;
  /** Yer imine bagli kaynakta baslik/url yer iminden gelir; burada kilitli. */
  locked?: boolean;
  bookmarkPicker?: React.ReactNode;
}) {
  const patch = (part: Partial<ResourceForm>) => onChange({ ...form, ...part });
  return (
    <div className="space-y-3">
      <Field label="Başlık">
        <Input
          value={form.title}
          onChange={(value) => patch({ title: value })}
          placeholder="MIT 18.06 ders 1"
          disabled={locked}
          className="w-full"
        />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="URL" hint={locked ? "Yer imine bağlı kaynağın adresi yer iminden gelir." : undefined}>
          <Input
            value={form.url}
            onChange={(value) => patch({ url: value })}
            placeholder="https://…"
            disabled={locked}
            className="w-full"
          />
        </Field>
        <Field label="Tür">
          <Select value={form.kind} onChange={(kind) => patch({ kind })} ariaLabel="Kaynak türü" className="w-full">
            {RESOURCE_KINDS.map((kind) => (
              <option key={kind.id} value={kind.id}>
                {kind.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-[8rem_1fr]">
        <Field label="Tahmini süre (dk)">
          <NumberInput
            value={form.estimatedMin}
            onChange={(estimatedMin) => patch({ estimatedMin })}
            min={0}
            step={5}
            placeholder="0"
            ariaLabel="Tahmini süre (dakika)"
            className="w-full"
          />
        </Field>
        <Field label="Not">
          <Textarea
            value={form.note}
            onChange={(value) => patch({ note: value })}
            rows={2}
            placeholder="Neden bu kaynak, hangi bölüm…"
            className="w-full"
          />
        </Field>
      </div>
      {bookmarkPicker}
    </div>
  );
}

/** Yer imi aramasi: sonucu tiklayinca kaynak olarak baglanir (kopya olmaz). */
function BookmarkPicker({
  topicId,
  existingIds,
  onAttached,
}: {
  topicId: string;
  existingIds: string[];
  onAttached: (message: string, tone: "ok" | "warn") => void;
}) {
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 250);
  const { data: bookmarks = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "learning", debounced],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "learning", q: debounced })}`),
  });

  const attach = useMutation({
    mutationFn: (bookmarkId: string) =>
      api.post<ResourceOut>("/study/resources/attach-bookmark", { topic_id: topicId, bookmark_id: bookmarkId }),
    onSuccess: (resource) => {
      const already = existingIds.includes(resource.id);
      onAttached(
        already ? "Bu yer imi zaten bu konuya bağlı." : `"${resource.title}" yer iminden eklendi.`,
        already ? "warn" : "ok",
      );
    },
  });

  return (
    <div className="rounded-card border border-subtle bg-surface-sunken p-3">
      <p className="mb-2 flex items-center gap-1.5 text-meta font-medium text-secondary">
        <BookmarkPlus size={13} /> Yer iminden seç
      </p>
      <Input value={query} onChange={setQuery} placeholder="Yer imlerinde ara…" className="w-full" />
      <div className="mt-2 max-h-40 overflow-y-auto">
        {isLoading ? (
          <SkeletonRows rows={2} />
        ) : bookmarks.length === 0 ? (
          <p className="py-3 text-center text-meta text-muted">
            {query ? "Eşleşen yer imi yok." : "Öğrenme koleksiyonunda yer imi yok."}
          </p>
        ) : (
          <ul className="space-y-1">
            {bookmarks.map((bookmark) => (
              <li key={bookmark.id}>
                <button
                  type="button"
                  disabled={!bookmark.url || attach.isPending}
                  onClick={() => attach.mutate(bookmark.id)}
                  className="flex w-full items-center gap-2 rounded-control px-2 py-1.5 text-left text-meta text-primary transition hover:bg-surface-hover disabled:opacity-50"
                >
                  <BookmarkPlus size={13} className="shrink-0 text-muted" />
                  <span className="min-w-0 flex-1 truncate">{bookmark.title}</span>
                  <span className="shrink-0 text-micro text-muted">{hostOf(bookmark.url)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function ResourceList({ topicId, addSignal = 0 }: { topicId: string; addSignal?: number }) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<ResourceOut | null>(null);
  const [addForm, setAddForm] = useState<ResourceForm>(EMPTY_FORM);
  const [editForm, setEditForm] = useState<ResourceForm>(EMPTY_FORM);
  const online = useOnline();
  const toast = useToast();
  /* Deep-link: ?resource={id} ilgili satiri vurgular (URL sozlesmesi, LF1). */
  const focusedResource = useHashRoute().params.get("resource") ?? "";

  /* Dis aksiyon ("Kaynak ekle") formu acar. Sayaç artisi ile tetiklenir:
     sekme zaten acikken de calisir (prop yalnizca ilk mount'ta okunmaz). */
  useEffect(() => {
    if (addSignal > 0) setAdding(true);
  }, [addSignal]);

  const { data: resources = [], isLoading } = useQuery({
    queryKey: ["topic-resources", topicId],
    queryFn: () => api.get<ResourceOut[]>(`/study/topics/${topicId}/resources`),
  });
  const { data: progress } = useQuery({
    queryKey: ["topic-progress", topicId],
    queryFn: () => api.get<TopicProgressOut>(`/study/topics/${topicId}/progress`),
  });

  // learning.write konu kaynaklarini tazeler; detaydaki olcu seridi (study-topic)
  // de ayni yazmadan beslenir -- ikisi ayrisirsa iki ilerleme celisir.
  const refresh = () => invalidateAfter("learning.write", "study.write");

  const add = useMutation({
    mutationFn: (form: ResourceForm) => api.post(`/study/topics/${topicId}/resources`, resourceBody(form)),
    onSuccess: () => {
      setAddForm(EMPTY_FORM);
      setAdding(false);
      refresh();
    },
  });
  const save = useMutation({
    mutationFn: ({ id, form }: { id: string; form: ResourceForm }) =>
      api.patch(`/learning/resources/${id}`, resourceBody(form)),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
      api.patch(`/learning/resources/${id}`, { completed }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/learning/resources/${id}`),
    onSuccess: refresh,
  });
  const move = useMutation({
    mutationFn: async ({ index, delta }: { index: number; delta: number }) => {
      const patches = swapPositions(resources, index, delta);
      await Promise.all(
        patches.map((patch) => api.patch(`/learning/resources/${patch.id}`, { position: patch.position })),
      );
    },
    onSuccess: refresh,
  });

  const confirmRemove = async (resource: ResourceOut) => {
    const ok = await confirmDialog({
      title: `"${resource.title}" silinsin mi?`,
      body: "Kaynak konudan kaldırılır; ilerleme sayacı yeniden hesaplanır.",
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(resource.id);
  };

  const done = progress?.done ?? 0;
  const total = progress?.total ?? 0;

  return (
    <div className="space-y-4">
      <SectionHeader
        label="Kaynaklar"
        hint={total ? `${done}/${total} tamamlandı` : undefined}
        action={
          <Button size="sm" variant="primary" disabled={!online} onClick={() => setAdding(true)}>
            <Plus size={13} /> Kaynak ekle
          </Button>
        }
      />

      {total > 0 && progress && (
        <TopicProgressBar done={progress.done} total={progress.total} pct={progress.pct} label="Öğrenme ilerlemesi" />
      )}

      {isLoading ? (
        <SkeletonRows rows={3} />
      ) : resources.length === 0 ? (
        <Empty>
          Henüz kaynak yok. "Kaynak ekle" ile bir URL ekle ya da bir yer imini bağla — tamamladıkça ilerleme dolar.
        </Empty>
      ) : (
        <RowList>
          {resources.map((resource, index) => {
            const meta = RESOURCE_KINDS.find((kind) => kind.id === resource.kind) ?? NO_KIND;
            const Icon = meta.icon;
            const isDone = resource.completed_at !== null;
            const href = resource.url ? safeHref(resource.url) : null;
            return (
              <div
                key={resource.id}
                data-resource-id={resource.id}
                className={cx(
                  "flex items-start gap-2.5 py-2.5 text-body",
                  focusedResource === resource.id && "bg-accent-surface",
                )}
              >
                {/* Tamamlama: dokunma hedefi 28px (>= 24px). Ilerlemeyi bu belirler. */}
                <button
                  type="button"
                  aria-label={
                    isDone
                      ? `${resource.title} tamamlanmadı olarak işaretle`
                      : `${resource.title} tamamlandı olarak işaretle`
                  }
                  aria-pressed={isDone}
                  title={isDone ? "Tamamlanmadı olarak işaretle" : "Tamamlandı olarak işaretle"}
                  disabled={!online || toggle.isPending}
                  onClick={() => toggle.mutate({ id: resource.id, completed: !isDone })}
                  className={cx(
                    "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-control border text-meta transition",
                    isDone ? "border-ok bg-ok text-canvas" : "border-strong hover:border-accent",
                    (!online || toggle.isPending) && "cursor-not-allowed opacity-40",
                  )}
                >
                  {isDone ? "✓" : ""}
                </button>

                <Icon size={14} className="mt-1.5 shrink-0 text-muted" />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cx(
                        "min-w-0 truncate font-medium",
                        isDone ? "text-muted line-through" : "text-primary",
                      )}
                    >
                      {resource.title}
                    </span>
                    <Chip size="xs">{meta.label}</Chip>
                    <Chip size="xs" tone={isDone ? "ok" : "neutral"}>
                      {isDone ? "Tamamlandı" : "Bekliyor"}
                    </Chip>
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-meta text-muted">
                    {resource.url && <span className="truncate">{hostOf(resource.url)}</span>}
                    {resource.estimated_min ? <span className="numeral">{resource.estimated_min} dk</span> : null}
                    {resource.source === "bookmark" && <span>Yer iminden</span>}
                  </div>
                  {resource.note && (
                    <p className="mt-1 whitespace-pre-line text-meta text-secondary">{resource.note}</p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-0.5">
                  <IconButton
                    title="Yukarı taşı"
                    disabled={!online || index === 0 || move.isPending}
                    onClick={() => move.mutate({ index, delta: -1 })}
                  >
                    <ArrowUp size={13} />
                  </IconButton>
                  <IconButton
                    title="Aşağı taşı"
                    disabled={!online || index === resources.length - 1 || move.isPending}
                    onClick={() => move.mutate({ index, delta: 1 })}
                  >
                    <ArrowDown size={13} />
                  </IconButton>
                  {href && (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={resource.url ?? ""}
                      aria-label={`${resource.title} kaynağını yeni sekmede aç`}
                      /* Dis baglanti acilisi `last_opened_at` damgasini atar; kaynak
                         detay ucu (GET) damgayi kendisi yazar -- PATCH'te alan yok. */
                      onClick={() => void api.get(`/learning/resources/${resource.id}`).catch(() => undefined)}
                      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-transparent text-muted transition hover:bg-surface-hover hover:text-accent"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                  <IconButton
                    title="Kaynağı düzenle"
                    disabled={!online}
                    onClick={() => {
                      setEditForm({
                        title: resource.title,
                        url: resource.url ?? "",
                        kind: resource.kind,
                        note: resource.note ?? "",
                        estimatedMin: resource.estimated_min ?? 0,
                      });
                      setEditing(resource);
                    }}
                  >
                    <Pencil size={13} />
                  </IconButton>
                  <IconButton
                    title="Kaynağı sil"
                    tone="danger"
                    disabled={!online}
                    onClick={() => confirmRemove(resource)}
                  >
                    <Trash2 size={13} />
                  </IconButton>
                </div>
              </div>
            );
          })}
        </RowList>
      )}

      <Modal
        open={adding}
        onClose={() => setAdding(false)}
        title="Kaynak ekle"
        hint="URL, tür ve tahmini süre ilerleme sayacını besler."
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setAdding(false)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !addForm.title.trim() || add.isPending}
              onClick={() => add.mutate(addForm)}
            >
              <Plus size={14} /> Ekle
            </Button>
          </div>
        }
      >
        <ResourceFormFields
          form={addForm}
          onChange={setAddForm}
          bookmarkPicker={
            <BookmarkPicker
              topicId={topicId}
              existingIds={resources.map((resource) => resource.id)}
              onAttached={(message, tone) => {
                toast.push(message, { tone });
                refresh();
              }}
            />
          }
        />
      </Modal>

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title="Kaynağı düzenle"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEditing(null)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || !editForm.title.trim() || save.isPending}
              onClick={() => editing && save.mutate({ id: editing.id, form: editForm })}
            >
              Kaydet
            </Button>
          </div>
        }
      >
        <ResourceFormFields form={editForm} onChange={setEditForm} locked={Boolean(editing?.bookmark_id)} />
      </Modal>
    </div>
  );
}

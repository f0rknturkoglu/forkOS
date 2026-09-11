/**
 * Kurslar gorunumu (Faz 8).
 *
 * Kurs = dis kaynakli ogrenme taahhudu (platform kursu, kampanya, program).
 * Durum/tarih/ilerleme iliskisi TEK noktadan yonetilir: backend
 * `progress_pct == 100` <-> `status == "done"` eslesmesini kurar ve
 * `started_at`/`completed_at` alanlarini doldurur; bu ekran onlari gosterir
 * ve kullaniciya tarihin neden bos/dolu oldugunu satirda soyler.
 *
 * Olcek: 500 kurs olabilir -> liste dilimlenir ("daha fazla goster") ve konu
 * adlari yalnizca GORUNEN satirlar icin cozulur.
 *
 * Derin baglanti: `?course=<id>` secili kursu isaretler ve gorunur alana
 * kaydirir (widget ve bugun paneli bu adrese gider).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ExternalLink, Pencil, Plus, Search, Trash2 } from "lucide-react";
import type { components } from "@/generated/api-schema";
import { api, qs } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { entityRoute } from "@/core/entityRegistry";
import { invalidateAfter } from "@/core/invalidation";
import {
  Button,
  Checkbox,
  Chip,
  Empty,
  Field,
  Input,
  Modal,
  Range,
  RowList,
  SectionHeader,
  Select,
  SkeletonRows,
  Textarea,
  Toolbar,
  cx,
} from "@/core/ui";
import { useDebounced, useOnline } from "@/lib/hooks";
import { navigate, useHashRoute } from "@/app/router";

type Course = components["schemas"]["CourseOut"];
type StudyArea = components["schemas"]["StudyAreaOut"];
type StudyTopicDetail = components["schemas"]["StudyTopicDetailOut"];
type EntityOut = components["schemas"]["EntityOut"];

/** Yerel arama sonucu satiri (`/search` govdesi semada tipli degil). */
interface SearchHit {
  id: string;
  type: string;
  title: string;
}

/** Kurs durum sozlugu — backend COURSE_STATUSES ile ayni kume. */
const COURSE_STATUSES = ["planned", "in_progress", "done", "dropped"] as const;

const STATUS_LABEL: Record<string, string> = {
  planned: "Planlandı",
  in_progress: "Devam ediyor",
  done: "Bitti",
  dropped: "Bırakıldı",
};

const STATUS_TONE: Record<string, "neutral" | "accent" | "ok" | "warn"> = {
  planned: "neutral",
  in_progress: "accent",
  done: "ok",
  dropped: "warn",
};

/** Ilk boyada cizilen satir sayisi ve "daha fazla goster" adimi. */
const FIRST_PAGE = 25;
const PAGE_STEP = 25;

/** Kaydirici birakildiktan sonra tek PATCH atilsin diye bekleme suresi.
 *  Tick basina istek atmak (eski davranis) sunucuyu gereksiz boguyordu. */
const PROGRESS_COMMIT_MS = 400;

/** Konu adi cozumu icin ust sinir: yalnizca gorunen satirlarin konulari. */
const TOPIC_RESOLVE_LIMIT = 24;

/** Form taslagi — modal kapaninca kaybolan gecici durum. */
interface CourseDraft {
  title: string;
  platform: string;
  url: string;
  status: string;
  notes: string;
  area_ids: string[];
}

export function CoursesView() {
  const route = useHashRoute();
  const selectedId = route.params.get("course") ?? "";
  const online = useOnline();

  const [showArchived, setShowArchived] = useState(false);
  const [areaFilter, setAreaFilter] = useState("");
  const [visibleCount, setVisibleCount] = useState(FIRST_PAGE);
  /** Kaydirici oynatilirken gosterilen gecici degerler (id -> yuzde). */
  const [drafts, setDrafts] = useState<Record<string, number>>({});
  const [editing, setEditing] = useState<{ id: string | null; draft: CourseDraft } | null>(null);
  const [certificateFor, setCertificateFor] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const timers = useRef(new Map<string, number>());

  useEffect(
    () => () => {
      timers.current.forEach((timer) => window.clearTimeout(timer));
      timers.current.clear();
    },
    [],
  );

  useEffect(() => setVisibleCount(FIRST_PAGE), [showArchived, areaFilter]);

  // Secili kurs gorunur alana gelsin (widget derin baglantisi).
  useEffect(() => {
    if (!selectedId) return;
    document.getElementById(`course-${selectedId}`)?.scrollIntoView({ block: "center" });
  }, [selectedId, visibleCount]);

  const courses = useQuery({
    queryKey: ["courses", showArchived, areaFilter],
    queryFn: () =>
      api.get<Course[]>(
        `/courses${qs({
          include_archived: showArchived || undefined,
          area_id: areaFilter || undefined,
        })}`,
      ),
  });

  // Alan adlari ve alan filtresi ayni listeden beslenir (ek istek yok).
  const areas = useQuery({
    queryKey: ["study-areas", "stats"],
    queryFn: () => api.get<StudyArea[]>("/study/areas?include_stats=true"),
  });

  const rows = courses.data ?? [];
  const shown = rows.slice(0, visibleCount);
  const areaTitles = useMemo(() => new Map((areas.data ?? []).map((area) => [area.id, area.title])), [areas.data]);

  // Konu adlari yalnizca gorunen satirlar icin cozulur; ilk boyada ek istek yok.
  const topicIds = useMemo(
    () => [...new Set(shown.flatMap((course) => course.topic_ids ?? []))].slice(0, TOPIC_RESOLVE_LIMIT),
    [shown],
  );
  const topicQueries = useQueries({
    queries: topicIds.map((id) => ({
      queryKey: ["study-topic", id],
      queryFn: () => api.get<StudyTopicDetail>(`/study/topics/${id}`),
      staleTime: 60_000,
    })),
  });
  const topicTitles = new Map(topicIds.map((id, index) => [id, topicQueries[index]?.data?.topic.title ?? "…"]));

  function withParams(mutate: (params: URLSearchParams) => void): void {
    const params = new URLSearchParams(route.params);
    mutate(params);
    navigate(`/learning?${params.toString()}`);
  }

  const openEditor = (course: Course | null) =>
    setEditing({
      id: course?.id ?? null,
      draft: {
        title: course?.title ?? "",
        platform: course?.platform ?? "",
        url: course?.url ?? "",
        status: course?.status ?? "planned",
        notes: course?.notes ?? "",
        area_ids: course?.area_ids ?? [],
      },
    });

  const save = useMutation({
    mutationFn: (payload: { id: string | null; draft: CourseDraft }) => {
      // Bos metinler kayda `null` gider (bos dize arama metnini kirletmesin).
      const body = {
        title: payload.draft.title.trim(),
        platform: payload.draft.platform.trim() || null,
        url: payload.draft.url.trim() || null,
        status: payload.draft.status,
        notes: payload.draft.notes.trim() || null,
        area_ids: payload.draft.area_ids,
      };
      return payload.id ? api.patch<Course>(`/courses/${payload.id}`, body) : api.post<Course>("/courses", body);
    },
    onSuccess: () => {
      setEditing(null);
      setDrafts({});
      invalidateAfter("learning.write");
    },
  });

  const progress = useMutation({
    mutationFn: (payload: { id: string; value: number }) =>
      api.patch<Course>(`/courses/${payload.id}`, { progress_pct: payload.value }),
    onSuccess: (_data, variables) => {
      // Yalnizca bu commit'in degeri hala ekrandaysa taslagi birak; kullanici
      // bu arada tekrar oynattiysa yeni taslak korunur.
      setDrafts((previous) => {
        if (previous[variables.id] !== variables.value) return previous;
        const next = { ...previous };
        delete next[variables.id];
        return next;
      });
      invalidateAfter("learning.write");
    },
    onError: (cause: Error) => setActionError(cause.message),
  });

  const archive = useMutation({
    mutationFn: (payload: { id: string; archived: boolean }) =>
      api.patch<Course>(`/courses/${payload.id}`, { archived: payload.archived }),
    onSuccess: () => invalidateAfter("learning.write"),
    onError: (cause: Error) => setActionError(cause.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/courses/${id}`),
    onSuccess: (_data, id) => {
      if (id === selectedId) withParams((params) => params.delete("course"));
      invalidateAfter("learning.write");
    },
    onError: (cause: Error) => setActionError(cause.message),
  });

  /** Kaydiriciyi oynatirken yalnizca yerel deger degisir; tek PATCH commit eder. */
  const queueProgress = (id: string, value: number) => {
    setDrafts((previous) => ({ ...previous, [id]: value }));
    const pending = timers.current.get(id);
    if (pending !== undefined) window.clearTimeout(pending);
    timers.current.set(
      id,
      window.setTimeout(() => {
        timers.current.delete(id);
        progress.mutate({ id, value });
      }, PROGRESS_COMMIT_MS),
    );
  };

  const askRemove = async (course: Course) => {
    const ok = await confirmDialog({
      title: "Kurs silinsin mi?",
      body: `"${course.title}" silinir; bu kursa bağlı bağlantılar da kalkar.`,
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(course.id);
  };

  if (courses.isLoading) {
    return (
      <div className="space-y-3">
        <p role="status" className="text-meta text-muted">
          Kurslar yükleniyor…
        </p>
        <SkeletonRows rows={4} />
      </div>
    );
  }

  if (courses.isError) {
    return (
      <div role="alert">
        <Empty
          variant="page"
          title="Kurslar yüklenemedi"
          action={
            <Button disabled={courses.isFetching} onClick={() => void courses.refetch()}>
              Yeniden dene
            </Button>
          }
        >
          Sunucudan yanıt alamadım: {courses.error.message}
        </Empty>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        label="Kurslar"
        hint={`${rows.length} kurs`}
        action={
          <Button variant="primary" size="sm" disabled={!online} onClick={() => openEditor(null)}>
            <Plus size={14} /> Kurs ekle
          </Button>
        }
      />

      <Toolbar className="border-t-0 pt-0">
        <Select value={areaFilter} onChange={setAreaFilter} ariaLabel="Alana göre süz" className="min-w-40">
          <option value="">Tüm alanlar</option>
          {(areas.data ?? []).map((area) => (
            <option key={area.id} value={area.id}>
              {area.title}
            </option>
          ))}
        </Select>
        <Checkbox checked={showArchived} onChange={setShowArchived} label="Arşivlenenleri göster" />
      </Toolbar>

      {actionError && (
        <p role="alert" className="text-meta text-danger">
          {actionError}
        </p>
      )}

      {rows.length === 0 ? (
        <Empty
          variant="page"
          title="Henüz kurs yok"
          action={
            <Button variant="primary" disabled={!online} onClick={() => openEditor(null)}>
              <Plus size={14} /> Kurs ekle
            </Button>
          }
        >
          Takip ettiğin bir kursu ekle; ilerlemesini, tarihlerini ve sertifikasını buradan yönet.
        </Empty>
      ) : (
        <>
          <RowList>
            {shown.map((course) => {
              const selected = course.id === selectedId;
              const value = drafts[course.id] ?? course.progress_pct;
              return (
                <div
                  key={course.id}
                  id={`course-${course.id}`}
                  aria-current={selected ? "true" : undefined}
                  className={cx("py-3", selected && "bg-surface-selected")}
                >
                  <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
                    <button
                      type="button"
                      onClick={() =>
                        selected
                          ? withParams((params) => params.delete("course"))
                          : withParams((params) => {
                              params.set("view", "courses");
                              params.set("course", course.id);
                            })
                      }
                      className="min-w-0 flex-1 text-left"
                    >
                      <span className="block whitespace-normal break-words text-body text-primary">{course.title}</span>
                      <span className="block truncate text-meta text-muted">{course.platform ?? "Platform yok"}</span>
                    </button>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Chip tone={STATUS_TONE[course.status] ?? "neutral"}>
                        {STATUS_LABEL[course.status] ?? course.status}
                      </Chip>
                      {course.archived && <Chip tone="warn">Arşivli</Chip>}
                      <span className="numeral text-meta text-secondary">%{value}</span>
                      {course.url && (
                        <a
                          href={course.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-meta text-accent"
                        >
                          <ExternalLink size={13} /> Kurs sayfası
                        </a>
                      )}
                    </div>
                  </div>

                  <p className="mt-1 text-meta text-muted">
                    Başlangıç: {course.started_at ? new Date(course.started_at).toLocaleDateString("tr-TR") : "—"} ·
                    Bitiş: {course.completed_at ? new Date(course.completed_at).toLocaleDateString("tr-TR") : "—"}
                    {course.status === "planned" && " · durum değişince tarihler kendiliğinden dolar"}
                    {course.status === "done" && " · tamamlanma tarihi bitiş tarihidir"}
                  </p>

                  {course.notes && <p className="mt-1 whitespace-pre-wrap text-meta text-secondary">{course.notes}</p>}

                  {(course.area_ids?.length ?? 0) > 0 || (course.topic_ids?.length ?? 0) > 0 ? (
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      {(course.area_ids ?? []).map((id) => (
                        <Chip key={id} size="xs" tone="neutral">
                          {areaTitles.get(id) ?? "Alan"}
                        </Chip>
                      ))}
                      {(course.topic_ids ?? []).map((id) => (
                        <Chip key={id} size="xs" tone="accent">
                          {topicTitles.get(id) ?? "…"}
                        </Chip>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <label className="flex min-w-60 flex-1 items-center gap-2 text-meta text-muted">
                      <span className="shrink-0">İlerleme</span>
                      <Range
                        value={value}
                        min={0}
                        max={100}
                        disabled={!online}
                        ariaLabel={`İlerleme: ${course.title}`}
                        ariaValueText={`%${value}`}
                        onChange={(next) => queueProgress(course.id, next)}
                        className="min-w-0 flex-1"
                      />
                    </label>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Button size="sm" disabled={!online} onClick={() => openEditor(course)}>
                        <Pencil size={13} /> Düzenle
                      </Button>
                      <Button
                        size="sm"
                        disabled={!online}
                        ariaExpanded={certificateFor === course.id}
                        onClick={() => setCertificateFor(certificateFor === course.id ? null : course.id)}
                      >
                        {course.certificate_entity_id ? "Sertifikayı değiştir" : "Sertifika bağla"}
                      </Button>
                      <Button
                        size="sm"
                        disabled={!online}
                        onClick={() => archive.mutate({ id: course.id, archived: !course.archived })}
                      >
                        {course.archived ? (
                          <>
                            <ArchiveRestore size={13} /> Geri aç
                          </>
                        ) : (
                          <>
                            <Archive size={13} /> Arşivle
                          </>
                        )}
                      </Button>
                      <Button size="sm" variant="danger" disabled={!online} onClick={() => void askRemove(course)}>
                        <Trash2 size={13} /> Sil
                      </Button>
                    </div>
                  </div>

                  {course.certificate_entity_id && certificateFor !== course.id && (
                    <p className="mt-1.5 text-meta text-muted">
                      Sertifika: <CertificateLink entityId={course.certificate_entity_id} />
                    </p>
                  )}

                  {certificateFor === course.id && (
                    <CertificatePicker courseId={course.id} online={online} onClose={() => setCertificateFor(null)} />
                  )}
                </div>
              );
            })}
          </RowList>

          {rows.length > shown.length && (
            <div className="flex justify-center">
              <Button onClick={() => setVisibleCount((count) => count + PAGE_STEP)}>
                Daha fazla göster ({rows.length - shown.length} kurs daha)
              </Button>
            </div>
          )}
        </>
      )}

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing?.id ? "Kursu düzenle" : "Kurs ekle"}
        hint="İlerleme %100 olunca durum kendiliğinden “Bitti” olur."
        className="sm:max-w-xl"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEditing(null)}>Vazgeç</Button>
            <Button
              variant="primary"
              disabled={!online || save.isPending || !editing?.draft.title.trim()}
              onClick={() => editing && save.mutate({ id: editing.id, draft: editing.draft })}
            >
              {editing?.id ? "Kaydet" : "Ekle"}
            </Button>
          </div>
        }
      >
        {editing && (
          <div className="space-y-3">
            <Field label="Başlık">
              <Input
                value={editing.draft.title}
                autoFocus
                onChange={(title) => setEditing({ ...editing, draft: { ...editing.draft, title } })}
                placeholder="Kurs adı"
                className="w-full"
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Platform">
                <Input
                  value={editing.draft.platform}
                  onChange={(platform) => setEditing({ ...editing, draft: { ...editing.draft, platform } })}
                  placeholder="Udemy, Coursera…"
                  className="w-full"
                />
              </Field>
              <Field label="Durum">
                <Select
                  value={editing.draft.status}
                  onChange={(status) => setEditing({ ...editing, draft: { ...editing.draft, status } })}
                  ariaLabel="Kurs durumu"
                  className="w-full"
                >
                  {COURSE_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_LABEL[status]}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Adres" hint="http(s) ile başlamalı">
              <Input
                value={editing.draft.url}
                onChange={(url) => setEditing({ ...editing, draft: { ...editing.draft, url } })}
                placeholder="https://…"
                className="w-full"
              />
            </Field>
            <Field label="Not">
              <Textarea
                value={editing.draft.notes}
                onChange={(notes) => setEditing({ ...editing, draft: { ...editing.draft, notes } })}
                rows={3}
                placeholder="Kurs hakkında notlar"
              />
            </Field>
            <div>
              <span className="mb-1 block text-meta text-secondary">Bağlı alanlar</span>
              {(areas.data ?? []).length === 0 ? (
                <p className="text-meta text-muted">Henüz çalışma alanı yok.</p>
              ) : (
                <div className="flex flex-wrap gap-x-4 gap-y-2">
                  {(areas.data ?? []).map((area) => (
                    <Checkbox
                      key={area.id}
                      checked={editing.draft.area_ids.includes(area.id)}
                      onChange={(checked) =>
                        setEditing({
                          ...editing,
                          draft: {
                            ...editing.draft,
                            area_ids: checked
                              ? [...editing.draft.area_ids, area.id]
                              : editing.draft.area_ids.filter((id) => id !== area.id),
                          },
                        })
                      }
                      label={area.title}
                    />
                  ))}
                </div>
              )}
            </div>
            {save.isError && (
              <p role="alert" className="text-meta text-danger">
                {save.error.message}
              </p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

/** Sertifika entity'sinin tipi bilinmedigi icin kayittan cozulur; boylece
 *  baglanti kayit defterindeki rotaya (kural 13) gider. */
function CertificateLink({ entityId }: { entityId: string }) {
  const entity = useQuery({
    queryKey: ["entity", entityId],
    queryFn: () => api.get<EntityOut>(`/entities/${entityId}`),
    staleTime: 60_000,
  });
  if (entity.isError) return <span className="text-muted">bulunamadı</span>;
  if (!entity.data) return <span className="text-muted">yükleniyor…</span>;
  return (
    <a href={entityRoute(entity.data.type, entity.data.id)} className="text-accent">
      {entity.data.title}
    </a>
  );
}

/**
 * Sertifika secici: yalnizca belge ve notlar sertifika olabilir (backend
 * `_validate_entities` ayni kumeyi dogrular), o yuzden arama sonucu bu
 * tiplere suzulur.
 */
function CertificatePicker({ courseId, online, onClose }: { courseId: string; online: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const term = useDebounced(query.trim(), 250);
  const [error, setError] = useState<string | null>(null);

  const search = useQuery({
    queryKey: ["search", term, "certificate"],
    queryFn: () => api.get<Record<string, SearchHit[]>>(`/search${qs({ q: term, limit: 8, grouped: true })}`),
    enabled: term.length >= 2,
  });

  const attach = useMutation({
    mutationFn: (entityId: string | null) =>
      api.patch<Course>(`/courses/${courseId}`, { certificate_entity_id: entityId }),
    onSuccess: () => {
      invalidateAfter("learning.write");
      onClose();
    },
    onError: (cause: Error) => setError(cause.message),
  });

  const hits = Object.values(search.data ?? {})
    .flat()
    .filter((hit) => hit.type === "document" || hit.type === "note");

  return (
    <div className="mt-2 space-y-2 rounded-card border border-subtle bg-surface-sunken p-3">
      <Field label="Sertifika bağla" hint="Yalnızca belge ve notlar sertifika olabilir">
        <Input
          value={query}
          autoFocus
          onChange={setQuery}
          placeholder="Belge ya da not ara (en az 2 harf)"
          className="w-full"
        />
      </Field>
      {term.length < 2 ? (
        <p className="text-meta text-muted">Aramak için en az 2 harf yaz.</p>
      ) : search.isLoading ? (
        <p role="status" className="text-meta text-muted">
          Aranıyor…
        </p>
      ) : search.isError ? (
        <p role="alert" className="text-meta text-danger">
          Arama başarısız: {search.error.message}
        </p>
      ) : hits.length === 0 ? (
        <p className="text-meta text-muted">Eşleşen belge ya da not yok.</p>
      ) : (
        <ul className="space-y-1">
          {hits.map((hit) => (
            <li key={hit.id}>
              <Button
                size="sm"
                disabled={!online || attach.isPending}
                onClick={() => attach.mutate(hit.id)}
                className="w-full justify-start"
              >
                <Search size={13} /> {hit.title}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex justify-end gap-2">
        <Button size="sm" disabled={!online || attach.isPending} onClick={() => attach.mutate(null)}>
          Sertifikayı kaldır
        </Button>
        <Button size="sm" onClick={onClose}>
          Kapat
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-meta text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

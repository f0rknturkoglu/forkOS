import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileJson } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { ApiError, api, qs } from "@/core/api";
import { confirmDialog } from "@/core/dialog";
import { invalidateAfter } from "@/core/invalidation";
import { planDayForToday } from "@/core/tasks";
import type {
  LearningResource,
  LearningView,
  StudyAreaStats,
  StudyTopicDetail,
  StudyTopicSummary,
  StudyTree,
  StudyTreeNode,
  TabId,
} from "@/core/types";
import { Button, Chip, Empty, PageFrame, Skeleton, Tabs } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceRailContent, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useDebounced, useOnline } from "@/lib/hooks";
import { localDateKey } from "@/lib/date";
import { openPomodoro } from "@/modules/pomodoro/dock";
import { CoursesView } from "./CoursesView";
import { ImportDialog } from "./ImportDialog";
import { LearningRail } from "./LearningRail";
import { ReviewView } from "./ReviewView";
import { StatsView } from "./StatsView";
import { TopicDetail } from "./TopicDetail";
import { LEARNING_TAB_IDS, LEARNING_VIEW_IDS, LEARNING_VIEWS } from "./learningLabels";
import type { TopicQuickFilter, TopicStatusFilter } from "./learningLabels";

/** Genis yerlesim esigi: 1024px ustunde ray + panel yan yana. */
const WIDE_LAYOUT = "(min-width: 1024px)";

/** Derin baglantidaki kayit silinmis/masinmis: bos ekran yerine acik durum. */
function notFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

function useWideLayout(): boolean {
  const [wide, setWide] = useState(
    () => typeof window === "undefined" || !window.matchMedia || window.matchMedia(WIDE_LAYOUT).matches,
  );
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const query = window.matchMedia(WIDE_LAYOUT);
    const onChange = () => setWide(query.matches);
    onChange();
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return wide;
}

/**
 * Ogrenme modulu — TEK orkestrator.
 *
 * Secim URL'de tutulur (`?view=`, `?area=`, `?focus=`, `?resource=`, `?tab=`);
 * bileşenler arasi sozlesme donmustur (Faz 0 kararlari). Yerel state yalnizca
 * gecici girdiler icindir (arama kutusu, filtre cipleri, yeni konu basligi).
 */
export function LearningPage() {
  const route = useHashRoute();
  const params = route.params;
  const view: LearningView = LEARNING_VIEW_IDS[params.get("view") ?? ""] ?? "topics";
  const areaParam = params.get("area") ?? "";
  const focusParam = params.get("focus") ?? "";
  const resourceParam = params.get("resource") ?? "";
  // Kaynak derin baglantisi kaynak listesini hedefler; acik `?tab=` her zaman kazanir.
  const tab: TabId = LEARNING_TAB_IDS[params.get("tab") ?? ""] ?? (resourceParam ? "kaynaklar" : "genel");
  const online = useOnline();
  const wide = useWideLayout();

  const [areaQuery, setAreaQuery] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [topicQuery, setTopicQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<TopicStatusFilter>("all");
  const [quickFilter, setQuickFilter] = useState<TopicQuickFilter>("none");
  const [newTopicTitle, setNewTopicTitle] = useState("");
  const [newTopicRoot, setNewTopicRoot] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const debouncedQuery = useDebounced(topicQuery, 250);

  /** URL tek kaynak: secim yazmalari buradan gecer, bilinmeyen parametreler korunur. */
  const writeUrl = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(params);
      for (const [key, value] of Object.entries(patch)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }
      const query = next.toString();
      navigate(`/learning${query ? `?${query}` : ""}`);
    },
    [params],
  );

  const areasQuery = useQuery({
    queryKey: ["study-areas", "stats"],
    queryFn: () => api.get<StudyAreaStats[]>("/study/areas?include_stats=true"),
  });
  const resourceQuery = useQuery({
    // Ortak anahtar: kaynak yazmalari `learning.write`, konu yazmalari `study.write`
    // uzerinden `topic-resources`i tazeler (invalidation haritasi).
    queryKey: ["topic-resources", "single", resourceParam],
    enabled: Boolean(resourceParam),
    retry: false,
    queryFn: () => api.get<LearningResource>(`/learning/resources/${resourceParam}`),
  });
  const resource = resourceQuery.data;
  const focusId = focusParam || resource?.topic_id || "";
  const detailQuery = useQuery({
    // TopicDetail ile AYNI anahtar: tek istek, tek tazeleme (`study-topic`).
    queryKey: ["study-topic", focusId],
    enabled: Boolean(focusId),
    retry: false,
    queryFn: () => api.get<StudyTopicDetail>(`/study/topics/${focusId}`),
  });
  const detail = detailQuery.data;
  const areas = useMemo(() => areasQuery.data ?? [], [areasQuery.data]);
  // Alan: konunun kendi alani > URL > ilk alan. Derin baglanti cozulurken
  // yanlis alanin agaci cekilmesin diye bilincli olarak bos birakilir.
  const areaId = detail?.topic.area_id || areaParam || (focusParam || resourceParam ? "" : (areas[0]?.id ?? ""));
  const treeQuery = useQuery({
    queryKey: ["study-tree", areaId, debouncedQuery, statusFilter],
    enabled: Boolean(areaId),
    queryFn: () =>
      api.get<StudyTree>(
        `/study/areas/${areaId}/tree${qs({
          q: debouncedQuery.trim() || undefined,
          status: statusFilter === "all" ? undefined : statusFilter,
        })}`,
      ),
  });
  const tree = treeQuery.data;

  /* Hizli filtreler: tek gecis hem ciplerin sayisini hem gorunur dugumleri
     uretir; eslesen dugumun ata zinciri agacta kalir. */
  const { visibleNodes, quickCounts } = useMemo(() => {
    const nodes = tree?.nodes ?? [];
    const counts = { today: 0, studying: 0, due: 0 };
    if (nodes.length === 0) return { visibleNodes: nodes, quickCounts: counts };
    const todayKey = localDateKey(new Date());
    const ids = new Set(nodes.map((node) => node.id));
    const keep = new Set<string>();
    for (const node of nodes) {
      const due = node.review_due;
      const studiedToday = node.last_studied_at ? localDateKey(new Date(node.last_studied_at)) === todayKey : false;
      const studying = node.status === "in_progress";
      if (due) counts.due += 1;
      if (studying) counts.studying += 1;
      if (due || studiedToday) counts.today += 1;
      const matches =
        quickFilter === "studying"
          ? studying
          : quickFilter === "due"
            ? due
            : quickFilter === "today"
              ? due || studiedToday
              : false;
      if (!matches) continue;
      keep.add(node.id);
      for (const ancestor of node.path) if (ids.has(ancestor)) keep.add(ancestor);
    }
    if (quickFilter === "none") return { visibleNodes: nodes, quickCounts: counts };
    return { visibleNodes: nodes.filter((node) => keep.has(node.id)), quickCounts: counts };
  }, [tree, quickFilter]);

  const filtered = Boolean(debouncedQuery.trim()) || statusFilter !== "all" || quickFilter !== "none";
  const selectedArea = areas.find((area) => area.id === areaId);
  const areaTitle = tree?.area.title ?? selectedArea?.title ?? "Öğrenme alanı";
  const revealPath = useMemo(() => (detail?.ancestors ?? []).map((ancestor) => ancestor.id), [detail]);
  const missing = [detailQuery.error, resourceQuery.error, treeQuery.error].some(notFound);

  const patchArea = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.patch<StudyAreaStats>(`/study/areas/${id}`, body),
    onSuccess: () => invalidateAfter("study.write"),
  });
  const createArea = useMutation({
    mutationFn: (title: string) => api.post<StudyAreaStats>("/study/areas", { title }),
    onSuccess: () => invalidateAfter("study.write"),
  });
  const removeArea = useMutation({
    mutationFn: (id: string) => api.del(`/study/areas/${id}`),
    onSuccess: (_data, id) => {
      if (id === areaId) writeUrl({ view: "topics", area: null, focus: null, resource: null });
      invalidateAfter("study.write");
    },
  });
  const createTopic = useMutation({
    mutationFn: (parentId: string | null) =>
      api.post<StudyTopicSummary>("/study/topics", {
        title: newTopicTitle.trim(),
        area_id: areaId,
        ...(parentId ? { parent_id: parentId } : {}),
      }),
    onSuccess: (topic) => {
      setNewTopicTitle("");
      invalidateAfter("study.write");
      writeUrl({ view: "topics", area: topic.area_id, focus: topic.id, resource: null });
    },
  });
  const createTask = useMutation({
    // Gorev + prepares_for bagi tek istekte (Faz 17); "bugune al" tercihi
    // plan_day olarak uygulanir (Faz 31).
    mutationFn: (topic: { id: string; title: string }) =>
      api.post(`/study/topics/${topic.id}/todos`, { plan_day: planDayForToday() }),
    onSuccess: () => invalidateAfter("todo.write", "study.write", "link.write"),
  });

  const selectArea = (id: string) => writeUrl({ view: "topics", area: id, focus: null, resource: null });
  const selectTopic = (id: string) => writeUrl({ view: "topics", area: areaId || null, focus: id, resource: null });
  const openTopic = (id: string) => writeUrl({ view: "topics", area: null, focus: id, resource: null });
  const confirmRemoveArea = async (area: StudyAreaStats) => {
    const ok = await confirmDialog({
      title: `"${area.title}" kalıcı olarak silinsin mi?`,
      body: `${area.topic_count} konu ve ${area.resource_count} kaynak da silinir. Bunun yerine arşivlemeyi düşün.`,
      confirmLabel: "Kalıcı olarak sil",
      tone: "danger",
    });
    if (ok) removeArea.mutate(area.id);
  };

  const rail = (
    <WorkspaceRailContent>
      <div data-onboarding="learning-create">
        <LearningRail
          online={online}
          areas={areas}
          areasState={areasQuery.isPending ? "loading" : areasQuery.isError ? "error" : "ready"}
          onRetryAreas={() => void areasQuery.refetch()}
          areaId={areaId}
          onSelectArea={selectArea}
          areaQuery={areaQuery}
          onAreaQuery={setAreaQuery}
          includeArchived={includeArchived}
          onIncludeArchived={setIncludeArchived}
          selectedArea={selectedArea}
          onManageAreas={() => setManageOpen(true)}
          topicQuery={topicQuery}
          onTopicQuery={setTopicQuery}
          statusFilter={statusFilter}
          onStatusFilter={setStatusFilter}
          quickFilter={quickFilter}
          onQuickFilter={setQuickFilter}
          quickCounts={quickCounts}
          tree={tree}
          treeState={!areaId ? "ready" : treeQuery.isPending ? "loading" : treeQuery.isError ? "error" : "ready"}
          onRetryTree={() => void treeQuery.refetch()}
          nodes={visibleNodes}
          filtered={filtered}
          selectedId={focusId}
          revealPath={revealPath}
          onSelectTopic={selectTopic}
          onTaskTopic={(node: StudyTreeNode) => createTask.mutate({ id: node.id, title: node.title })}
          onFocusTopic={(node: StudyTreeNode) => openPomodoro({ context: node.id, topic: node.title })}
          newTopicTitle={newTopicTitle}
          onNewTopicTitle={setNewTopicTitle}
          newTopicRoot={newTopicRoot}
          onNewTopicRoot={setNewTopicRoot}
          parentTitle={newTopicRoot ? undefined : detail?.topic.title}
          onAddTopic={() => createTopic.mutate(newTopicRoot ? null : focusId || null)}
          addPending={createTopic.isPending}
          manageOpen={manageOpen}
          onManageClose={() => setManageOpen(false)}
          onRenameArea={(id, title) => patchArea.mutate({ id, body: { title } })}
          onColorArea={(id, color) => patchArea.mutate({ id, body: { color: color || null } })}
          onArchiveArea={(id, archived) => patchArea.mutate({ id, body: { archived } })}
          onDeleteArea={(area) => void confirmRemoveArea(area)}
          onCreateArea={(title) => createArea.mutate(title)}
          areaPending={patchArea.isPending || removeArea.isPending || createArea.isPending}
        />
      </div>
    </WorkspaceRailContent>
  );

  const breadcrumb = detail && (
    <nav aria-label="Konu yolu" className="flex flex-wrap items-center gap-1 text-meta text-muted">
      <button
        type="button"
        onClick={() => writeUrl({ area: areaId || null, focus: null, resource: null })}
        className="max-w-[16rem] truncate rounded-control px-1 hover:bg-surface-hover hover:text-primary"
        title={areaTitle}
      >
        {areaTitle}
      </button>
      {detail.ancestors.map((ancestor) => (
        <span key={ancestor.id} className="flex min-w-0 items-center gap-1">
          <span aria-hidden="true">/</span>
          <button
            type="button"
            onClick={() => writeUrl({ focus: ancestor.id, resource: null })}
            className="max-w-[16rem] truncate rounded-control px-1 hover:bg-surface-hover hover:text-primary"
            title={ancestor.title}
          >
            {ancestor.title}
          </button>
        </span>
      ))}
      <span aria-hidden="true">/</span>
      <span aria-current="page" className="max-w-[22rem] truncate text-secondary" title={detail.topic.title}>
        {detail.topic.title}
      </span>
    </nav>
  );

  const pane = (compact: boolean) => (
    <>
      <WorkspacePaneHeader
        eyebrow={areaTitle}
        title={detail?.topic.title ?? "Konu seç"}
        wrapTitle
        hint={
          detail
            ? `${detail.progress.done}/${detail.progress.total} kaynak · ${detail.stats.minutes} dk odak`
            : `${visibleNodes.length} konu`
        }
        action={
          compact && focusId ? (
            <Button size="sm" onClick={() => writeUrl({ focus: null, resource: null })} ariaLabel="Konu listesine dön">
              <ArrowLeft size={14} /> Liste
            </Button>
          ) : undefined
        }
      />
      <WorkspaceScrollArea className="p-3">
        {focusId ? (
          detailQuery.isError && !notFound(detailQuery.error) ? (
            <div
              role="alert"
              className="mx-auto max-w-content stack-y-2 rounded-card border border-danger-border bg-danger-surface px-4 py-3"
            >
              <p className="text-meta text-danger">Konu yüklenemedi.</p>
              <Button size="sm" onClick={() => void detailQuery.refetch()}>
                Yeniden dene
              </Button>
            </div>
          ) : !detail ? (
            <div className="mx-auto max-w-content stack-y-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <div className="mx-auto max-w-content stack-y-3">
              {breadcrumb}
              {resource && (
                <p className="flex min-w-0 items-center gap-1.5 text-meta text-muted">
                  <Chip tone="accent" size="xs">
                    Kaynak
                  </Chip>
                  <span className="truncate" title={resource.title}>
                    {resource.title}
                  </span>
                </p>
              )}
              <TopicDetail
                topicId={focusId}
                tab={tab}
                onTabChange={(next) => writeUrl({ tab: next })}
                onDeleted={() => writeUrl({ view: "topics", focus: null, resource: null })}
              />
            </div>
          )
        ) : areasQuery.isSuccess && areas.length === 0 ? (
          <Empty
            variant="page"
            title="Henüz çalışma alanı yok"
            action={<Button onClick={() => setManageOpen(true)}>Alan oluştur</Button>}
          >
            Öğrenme yüzeyi alanlar üzerine kurulur. İlk alanını oluşturup konuları eklemeye başla.
          </Empty>
        ) : (
          <Empty variant="page" title="Bir konu seç">
            Soldaki konu ağacından bir başlık seç. Kaynaklar, ilerleme ve notlar bu çalışma yüzeyinde açılır.
          </Empty>
        )}
      </WorkspaceScrollArea>
    </>
  );

  return (
    <PageFrame className="stack-y-3">
      <div data-onboarding="learning-review" className="flex flex-wrap items-center gap-2">
        <Tabs
          value={view}
          onChange={(next) => writeUrl({ view: next })}
          items={LEARNING_VIEWS.map((item) => ({ id: item.id, label: item.label }))}
          ariaLabel="Öğrenme görünümleri"
        />
        <span className="h-px flex-1 bg-subtle" />
        <Button
          size="sm"
          onClick={() => setImportOpen(true)}
          disabled={!online}
          title={online ? undefined : "Çevrimdışı: yazma kapalı"}
        >
          <FileJson size={14} /> JSON yükle
        </Button>
      </div>

      {missing ? (
        <Empty
          variant="page"
          title="Kayıt bulunamadı"
          action={
            <Button onClick={() => writeUrl({ view: "topics", area: null, focus: null, resource: null })}>
              Alan listesine dön
            </Button>
          }
        >
          Bağlantıdaki kayıt silinmiş ya da taşınmış olabilir. Alan listesine dönüp yeniden seçebilirsin.
        </Empty>
      ) : view !== "topics" ? (
        <div className="min-h-workspace-body">
          {view === "courses" && <CoursesView />}
          {view === "review" && <ReviewView onOpenTopic={openTopic} />}
          {view === "stats" && <StatsView onOpenTopic={openTopic} />}
        </div>
      ) : wide ? (
        <Workspace rail={rail} railAt="lg" railWidth="wide">
          {pane(false)}
        </Workspace>
      ) : (
        /* Dar genislik: master-detail. Detay agacin ALTINA itilmez; konu
           secilince yerini detaya birakir ve gorunur bir geri dugmesi cikar. */
        <div className="min-h-workspace-body">
          {focusId ? (
            <Workspace>{pane(true)}</Workspace>
          ) : (
            <div className="rounded-card border border-subtle bg-surface p-3">{rail}</div>
          )}
        </div>
      )}

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onDone={(areaId) => {
          setImportOpen(false);
          writeUrl({ view: "topics", area: areaId, focus: null, resource: null });
        }}
      />
    </PageFrame>
  );
}

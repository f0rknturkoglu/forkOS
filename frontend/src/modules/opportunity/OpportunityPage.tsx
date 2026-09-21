import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { invalidateAfter } from "@/core/invalidation";
import { api } from "@/core/api";
import { Button, Empty, PageFrame, Section, Tabs, useToast } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { SavedViewPicker } from "@/core/SavedViewPicker";
import { useAppliedSavedView } from "@/core/savedViews";
import { confirmDialog } from "@/core/dialog";
import { navigate, useHashRoute } from "@/app/router";
import type { Opportunity } from "@/core/types";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { SyncProgress } from "@/core/SyncProgress";
import { useOnline } from "@/lib/hooks";
import { OpportunityDetail } from "./OpportunityDetail";
import { OpportunityCard, OpportunityCollection } from "./OpportunityList";
import { OpportunityKanban } from "./OpportunityKanban";
import { OpportunityFilterBar } from "./OpportunityFilters";
import { SourcePicker } from "./SourcePicker";
import { ApplicationsWorkspace } from "./ApplicationsWorkspace";
import { CareerWorkspace } from "./CareerWorkspace";
import { SourcesWorkspace } from "./SourcesWorkspace";
import { browseQuery, type OpportunityBrowseFilters, type OpportunityBrowseResponse } from "./opportunityBrowse";
import {
  OPPORTUNITY_TABS,
  sanitizeOpportunityFilters,
  serializeOpportunityFilters,
  parseOpportunityUrl,
  sectionForTab,
  serializeOpportunityUrl,
  type OpportunityTab,
} from "./opportunityUrl";
import { remoteKind } from "./labels";

const PAGE = 60;

const INITIAL_FILTERS: OpportunityBrowseFilters = {
  section: "jobs",
  sort: "score",
  offset: 0,
  limit: PAGE,
};

/**
 * Kariyer çalışma alanının bölümleri. Sekme KİMLİKLERİ sözleşmedir
 * (`?tab=` derin bağlantıları); etiketler ürün dilidir.
 */
const TAB_LABELS: Record<OpportunityTab, string> = {
  jobs: "Keşfet",
  applications: "Başvurular",
  announcements: "Duyurular",
  career: "Profil",
  sources: "Kaynaklar",
};

function initialView(): "rows" | "grid" | "kanban" {
  if (typeof window === "undefined") return "rows";
  const saved = window.localStorage.getItem("forkos:opportunity-view");
  if (saved === "grid" || saved === "kanban") return saved;
  return "rows";
}

export function OpportunityPage() {
  const online = useOnline();
  const toast = useToast();
  const { save } = useSaveToLibrary();
  const { params } = useHashRoute();
  const [filters, setFilters] = useState<OpportunityBrowseFilters>(INITIAL_FILTERS);
  const [tab, setTab] = useState<OpportunityTab>("jobs");
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"rows" | "grid" | "kanban">(initialView);
  // Sabitlenmiş görünüm kimliği URL'de kalır (`?saved=`): sidebar satırı vurgulu
  // kalır ve bağlantı yeniden üretilebilir olur.
  const [savedView, setSavedView] = useState<string | null>(params.get("saved"));
  const [searchDraft, setSearchDraft] = useState("");
  // Kariyer deep-link'leri (`?story=` / `?connection=`) URL'de korunur; aksi
  // halde sayfa kendi URL'sini yazarken onları siler ve kayıt kapanırdı.
  const [story, setStory] = useState<string | null>(null);
  const [connection, setConnection] = useState<string | null>(null);

  // ── URL <-> durum köprüsü ──────────────────────────────────────────
  // Filtreler ve sekme adres çubuğuna yazılır; tarayıcı geri/ileri çalışır ve
  // yenilemede seçili kayıt yeniden açılır. Kendi yazdığımız değişikliği
  // yok sayarak döngüyü kırıyoruz.
  const lastWritten = useRef<string | null>(null);

  useEffect(() => {
    const incoming = params.toString();
    if (lastWritten.current === incoming) return;
    const parsed = parseOpportunityUrl(params, INITIAL_FILTERS);
    lastWritten.current = incoming;
    setFilters(parsed.filters);
    setSearchDraft(parsed.filters.search ?? "");
    setTab(parsed.tab);
    setSelected(parsed.focus);
    setStory(parsed.story);
    setConnection(parsed.connection);
    if (parsed.view) setView(parsed.view);
    setSavedView(parsed.saved ?? null);
  }, [params]);


  const urlState = useMemo(
    () => serializeOpportunityUrl({ tab, focus: selected, story, connection, filters, view, saved: savedView }),
    [tab, selected, story, connection, filters, view, savedView],
  );

  useEffect(() => {
    if (lastWritten.current === urlState) return;
    lastWritten.current = urlState;
    navigate(`/opportunities?${urlState}`, { replace: true });
  }, [urlState]);

  // Arama girdisi debounce'lu: her tuşta sorgu gitmez.
  useEffect(() => {
    if ((filters.search ?? "") === searchDraft) return;
    const timer = window.setTimeout(() => {
      setFilters((current) => ({ ...current, search: searchDraft, offset: 0 }));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft, filters.search]);

  /**
   * Sabitlenmiş görünümün filtresini uygular: yalnız tanınan alanlar geçer,
   * bilinmeyen anahtar yok sayılır.
   */
  const applySavedFilters = useCallback(
    (saved: Record<string, unknown>, view?: { id: string }) => {
      const next = sanitizeOpportunityFilters(saved, INITIAL_FILTERS);
      setFilters(next);
      setSearchDraft(next.search ?? "");
      if (view?.id) setSavedView(view.id);
    },
    [],
  );

  // Sabitlenmiş görünüm: rota `?saved=` taşıyorsa filtre bir kez uygulanır.
  useAppliedSavedView("opportunity", params, applySavedFilters);

  const browseEnabled = tab === "jobs" || tab === "announcements";
  const queryFilters = useMemo(() => ({ ...filters, offset: 0 }), [filters]);
  const browse = useInfiniteQuery({
    queryKey: ["opportunities", "browse", queryFilters],
    initialPageParam: 0,
    enabled: browseEnabled,
    queryFn: ({ pageParam }) => api.get<OpportunityBrowseResponse>(browseQuery({ ...queryFilters, offset: pageParam })),
    getNextPageParam: (lastPage) => {
      if (lastPage.items.length === 0) return undefined;
      const next = lastPage.offset + lastPage.items.length;
      return next < lastPage.total ? next : undefined;
    },
  });

  const pages = browse.data?.pages ?? [];
  const rows = useMemo(() => pages.flatMap((page) => page.items), [pages]);
  const overview = pages[0];
  const counts = overview?.section_counts ?? { jobs: 0, announcements: 0, trash: 0 };
  const facets = overview?.facets ?? {};
  const total = overview?.total ?? 0;
  const isFetching = browseEnabled && browse.isFetching && !browse.isError;

  // Sayaç: yeni sorgu gelene kadar önceki veri korunur, sahte 0/0 gösterilmez.
  const shown = rows.length;

  const transition = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) => api.post(`/opportunities/${id}/transition`, { to }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });
  const lifecycleMutation = useMutation({
    mutationFn: ({ action, id }: { action: "trash" | "restore" | "delete"; id: string }) =>
      action === "delete" ? api.del(`/opportunities/${id}`) : api.post(`/opportunities/${id}/${action}`),
    onSuccess: (_, variables) => {
      invalidateAfter("opportunity.write");
      toast.push(
        variables.action === "trash"
          ? "Fırsat çöpe taşındı"
          : variables.action === "restore"
            ? "Fırsat geri yüklendi"
            : "Fırsat kalıcı olarak silindi",
        { tone: "ok" },
      );
    },
  });

  const changeView = useCallback((next: "rows" | "grid" | "kanban") => {
    setView(next);
    if (typeof window !== "undefined") window.localStorage.setItem("forkos:opportunity-view", next);
  }, []);

  const changeTab = useCallback((next: OpportunityTab) => {
    setTab(next);
    setFilters((current) => ({ ...current, section: sectionForTab(next, current.section), offset: 0 }));
    setSelected(null);
    if (next !== "career") {
      setStory(null);
      setConnection(null);
    }
  }, []);

  const openRecord = useCallback((id: string) => setSelected(id), []);
  const closeRecord = useCallback(() => {
    setSelected(null);
  }, []);

  const saveItem = (item: Opportunity) => {
    if (item.url) {
      void save({ url: item.url, title: item.title, collection: "reference", entity_id: item.id });
    }
  };

  async function trash(item: Opportunity) {
    if (
      await confirmDialog({
        title: "Fırsat çöpe atılsın mı?",
        body: item.title,
        confirmLabel: "Çöpe at",
        tone: "danger",
      })
    ) {
      lifecycleMutation.mutate({ action: "trash", id: item.id });
    }
  }
  async function permanentlyDelete(item: Opportunity) {
    if (
      await confirmDialog({
        title: "Fırsat kalıcı silinsin mi?",
        body: `${item.title} — bu işlem geri alınamaz.`,
        confirmLabel: "Kalıcı sil",
        tone: "danger",
      })
    ) {
      lifecycleMutation.mutate({ action: "delete", id: item.id });
    }
  }

  const tabs = OPPORTUNITY_TABS.map((id) => ({
    id,
    label: TAB_LABELS[id],
    badge: id === "jobs" ? counts.jobs : id === "announcements" ? counts.announcements : undefined,
  }));

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Takip"
          title="Fırsatlar"
          hint={
            tab === "jobs"
              ? "Keşfedilen iş ilanları ve kısa liste"
              : tab === "announcements"
                ? "YLSY, ÖSYM ve kamu duyuruları"
                : tab === "applications"
                  ? "Yalnızca gerçek başvurular"
                  : tab === "career"
                    ? "CV, hikâye bankası ve bağlantı ağı"
                    : "Kaynak sağlığı, kapsam ve cache"
          }
        >
          <div className="flex flex-wrap items-center gap-2">
            <Tabs value={tab} onChange={changeTab} items={tabs} ariaLabel="Fırsat çalışma alanları" />
            <span className="ml-auto flex flex-wrap items-center gap-2">
              {(tab === "jobs" || tab === "announcements") && <SourcePicker />}
              <SavedViewPicker
                module="opportunity"
                filters={serializeOpportunityFilters(filters)}
                onApply={applySavedFilters}
              />
            </span>
          </div>
          {tab !== "sources" && (
            <div className="mt-3">
              <SyncProgress compact />
            </div>
          )}
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="p-3">
          {browseEnabled ? (
            <div className="space-y-3">
              {filters.section !== "announcements" && counts.trash > 0 && (
                <div>
                  <Button
                    size="sm"
                    variant={filters.section === "trash" ? "secondary" : "ghost"}
                    onClick={() =>
                      setFilters((current) => ({
                        ...current,
                        section: current.section === "trash" ? "jobs" : "trash",
                        offset: 0,
                      }))
                    }
                  >
                    <Trash2 size={12} /> Çöp
                    <span className="tabular-nums text-muted">{counts.trash}</span>
                  </Button>
                </div>
              )}

              <OpportunityFilterBar
                filters={filters}
                facets={facets}
                shown={shown}
                total={total}
                loading={isFetching}
                view={view}
                onView={changeView}
                onChange={setFilters}
                searchValue={searchDraft}
                onSearchChange={setSearchDraft}
                liveMessage={isFetching ? "Sonuçlar güncelleniyor" : `${total} kayıttan ${shown} tanesi gösteriliyor`}
              />

              <Section
                title={
                  filters.section === "jobs" ? "İş ilanları" : filters.section === "announcements" ? "Duyurular" : "Çöp"
                }
                hint={`${shown} / ${total}`}
              >
                {browse.isPending && browseEnabled ? (
                  <div
                    className={view === "grid" ? "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3" : "space-y-3"}
                  >
                    {Array.from({ length: view === "grid" ? 6 : 4 }, (_, index) => (
                      <div key={index} className="h-24 rounded-card bg-surface-sunken" />
                    ))}
                  </div>
                ) : browse.isError ? (
                  <Empty
                    variant="page"
                    title="Fırsatlar yüklenemedi"
                    action={<Button onClick={() => void browse.refetch()}>Tekrar dene</Button>}
                  >
                    Kaynak yanıtını alamadım. Bağlantıyı kontrol edip yeniden deneyebilirsin.
                  </Empty>
                ) : rows.length === 0 ? (
                  <Empty
                    variant="page"
                    title={total === 0 ? "Bu süzgece uyan kayıt yok" : "Henüz kayıt yok"}
                    action={<Button onClick={() => setFilters(INITIAL_FILTERS)}>Süzgeci temizle</Button>}
                  >
                    {filters.section === "announcements"
                      ? "YLSY, ÖSYM ve diğer resmî duyurular burada yayın tarihine göre görünür."
                      : "Kaynaklar yenilendiğinde uygun kayıtlar burada görünür."}
                  </Empty>
                ) : (
                  <>
                    {view === "kanban" ? (
                      <OpportunityKanban
                        items={rows}
                        disabled={!online}
                        section={filters.section === "announcements" ? "announcements" : "jobs"}
                        onOpen={openRecord}
                        onStatus={(id, to) => transition.mutate({ id, to })}
                      />
                    ) : (
                      <OpportunityCollection layout={view}>
                        {rows.map((item) => (
                          <OpportunityCard
                            key={item.id}
                            item={item}
                            disabled={!online}
                            onOpen={() => openRecord(item.id)}
                            onStatus={(to) => transition.mutate({ id: item.id, to })}
                            isTrash={filters.section === "trash"}
                            layout={view}
                            sourceActive={filters.source === item.source}
                            remoteActive={filters.remote === remoteKind(item.remote)}
                            onSource={(source) =>
                              setFilters((current) => ({
                                ...current,
                                source: current.source === source ? "" : source,
                                offset: 0,
                              }))
                            }
                            onRemote={(remote) =>
                              setFilters((current) => ({
                                ...current,
                                remote: current.remote === remote ? "" : remote,
                                offset: 0,
                              }))
                            }
                            onKind={(kind) => {
                              const section = kind === "job" ? "jobs" : "announcements";
                              setFilters((current) => ({ ...current, section, offset: 0 }));
                              setTab(section === "jobs" ? "jobs" : "announcements");
                            }}
                            onTrash={() => void trash(item)}
                            onRestore={() => lifecycleMutation.mutate({ action: "restore", id: item.id })}
                            onDelete={() => void permanentlyDelete(item)}
                            onSave={() => saveItem(item)}
                          />
                        ))}
                      </OpportunityCollection>
                    )}
                    {browse.hasNextPage && (
                      <div className="mt-5 flex items-center justify-center gap-3">
                        <Button onClick={() => void browse.fetchNextPage()} disabled={browse.isFetchingNextPage}>
                          {browse.isFetchingNextPage ? "Yükleniyor…" : "Daha fazla"}
                        </Button>
                        <span className="text-meta text-muted">
                          {shown} / {total}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </Section>
            </div>
          ) : tab === "applications" ? (
            <ApplicationsWorkspace online={online} onOpen={openRecord} />
          ) : tab === "career" ? (
            <CareerWorkspace focusStoryId={story} focusConnectionId={connection} />
          ) : (
            <SourcesWorkspace />
          )}
        </WorkspaceScrollArea>
      </Workspace>

      {selected && <OpportunityDetail id={selected} close={closeRecord} />}
    </PageFrame>
  );
}

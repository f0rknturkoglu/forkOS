import { useEffect, useMemo, useState } from "react";
import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { LayoutGrid, List, Search, Settings2 } from "lucide-react";
import { invalidateAfter } from "@/core/invalidation";
import { api } from "@/core/api";
import { Button, Empty, IconButton, Input, PageFrame, PageHeader, Section, Toolbar, cx, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { navigate, useHashRoute } from "@/app/router";
import type { Opportunity } from "@/core/types";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { useOnline } from "@/lib/hooks";
import { OpportunityDetail } from "./OpportunityDetail";
import { JobhunterSettings } from "./JobhunterSettings";
import { FilterChip, OpportunityCard, OpportunityCollection } from "./OpportunityList";
import { OpportunityFilters } from "./OpportunityFilters";
import { SourcePicker } from "./SourcePicker";
import { ApplicationCrmPanel } from "./ApplicationCrmPanel";
import { SyncProgress } from "@/core/SyncProgress";
import {
  browseQuery,
  switchOpportunitySection,
  type OpportunityBrowseFilters,
  type OpportunityBrowseResponse,
  type OpportunitySection,
} from "./opportunityBrowse";
import { remoteKind } from "./labels";

const PAGE = 60;

const INITIAL_FILTERS: OpportunityBrowseFilters = {
  section: "jobs",
  sort: "score",
  offset: 0,
  limit: PAGE,
};

function initialView(): "rows" | "grid" {
  if (typeof window === "undefined") return "rows";
  return window.localStorage.getItem("forkos:opportunity-view") === "grid" ? "grid" : "rows";
}

export function OpportunityPage() {
  const online = useOnline();
  const toast = useToast();
  const { save } = useSaveToLibrary();
  const { params } = useHashRoute();
  const [filters, setFilters] = useState<OpportunityBrowseFilters>(INITIAL_FILTERS);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"rows" | "grid">(initialView);
  const [showSettings, setShowSettings] = useState(false);
  const [showCrm, setShowCrm] = useState(false);

  useEffect(() => {
    const focus = params.get("focus");
    if (focus) setSelected(focus);
  }, [params]);

  const queryFilters = useMemo(() => ({ ...filters, offset: 0 }), [filters]);
  const browse = useInfiniteQuery({
    queryKey: ["opportunities", "browse", queryFilters],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => api.get<OpportunityBrowseResponse>(browseQuery({ ...queryFilters, offset: pageParam })),
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.items.length;
      return next < lastPage.total ? next : undefined;
    },
  });
  const pages = browse.data?.pages ?? [];
  const rows = pages.flatMap((page) => page.items);
  const overview = pages[0];
  const counts = overview?.section_counts ?? { jobs: 0, announcements: 0, trash: 0 };
  const facets = overview?.facets ?? {};
  const total = overview?.total ?? 0;
  const hasActiveFilters = Boolean(
    filters.search ||
    filters.category ||
    filters.source ||
    filters.min_score !== undefined ||
    filters.max_score !== undefined,
  );

  const patch = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch(`/opportunities/${id}`, { status }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });
  const lifecycle = useMutation({
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

  const changeView = (next: "rows" | "grid") => {
    setView(next);
    if (typeof window !== "undefined") window.localStorage.setItem("forkos:opportunity-view", next);
  };
  const changeSection = (section: OpportunitySection) =>
    setFilters((current) => switchOpportunitySection(current, section));
  const resetFilters = () =>
    setFilters((current) => switchOpportunitySection({ ...INITIAL_FILTERS, search: current.search }, current.section));

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
      lifecycle.mutate({ action: "trash", id: item.id });
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
      lifecycle.mutate({ action: "delete", id: item.id });
    }
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Fırsatlar" />

      <Toolbar className="sticky top-0 z-10 bg-canvas/95 backdrop-blur">
        <div className="relative min-w-0 flex-[1_1_18rem]">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon" />
          <Input
            value={filters.search ?? ""}
            onChange={(search) => setFilters((current) => ({ ...current, search, offset: 0 }))}
            placeholder="Başlık, kurum, konum ya da kaynakta ara…"
            ariaLabel="Fırsatlarda ara"
            className="w-full pl-9"
          />
        </div>
        <Button size="sm" onClick={() => setShowCrm((value) => !value)}>
          {showCrm ? "CRM gizle" : "CRM"}
        </Button>
        <IconButton title="Jobhunter ayarları" onClick={() => setShowSettings(true)}>
          <Settings2 size={15} />
        </IconButton>
        <SourcePicker />
        <span className="flex items-center gap-1 rounded-control border border-subtle p-0.5">
          <IconButton
            title="Yatay satırlar"
            onClick={() => changeView("rows")}
            className={view === "rows" ? "bg-surface-sunken text-primary" : "border-transparent"}
          >
            <List size={14} />
          </IconButton>
          <IconButton
            title="Karesel kartlar"
            onClick={() => changeView("grid")}
            className={view === "grid" ? "bg-surface-sunken text-primary" : "border-transparent"}
          >
            <LayoutGrid size={14} />
          </IconButton>
        </span>
        <SyncProgress compact />
      </Toolbar>

      <nav className="flex flex-wrap gap-2" aria-label="Fırsat bölümleri">
        {(
          [
            ["jobs", "İş ilanları"],
            ["announcements", "Duyurular"],
            ["trash", "Çöp"],
          ] as const
        ).map(([section, label]) => (
          <FilterChip
            key={section}
            label={label}
            count={counts[section]}
            active={filters.section === section}
            onClick={() => changeSection(section)}
          />
        ))}
      </nav>

      {showCrm && <ApplicationCrmPanel />}
      <OpportunityFilters filters={filters} facets={facets} onChange={setFilters} />

      <Section
        title={filters.section === "jobs" ? "İş ilanları" : filters.section === "announcements" ? "Duyurular" : "Çöp"}
        hint={`${rows.length} / ${total} kayıt`}
      >
        {browse.isLoading ? (
          <div
            className={cx(
              "animate-pulse",
              view === "grid" ? "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3" : "space-y-3",
            )}
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
            title={hasActiveFilters ? "Bu süzgece uyan kayıt yok" : "Henüz kayıt yok"}
            action={
              hasActiveFilters ? (
                <Button onClick={resetFilters}>Süzgeci temizle</Button>
              ) : (
                <Button variant="primary" onClick={() => navigate("/sources")}>
                  Kaynakları çek
                </Button>
              )
            }
          >
            {filters.section === "announcements"
              ? "YLSY, ÖSYM ve diğer resmi duyurular burada yayın tarihine göre görünür."
              : "Kaynaklar yenilendiğinde uygun kayıtlar burada görünür."}
          </Empty>
        ) : (
          <>
            <OpportunityCollection layout={view}>
              {rows.map((item) => (
                <OpportunityCard
                  key={item.id}
                  item={item}
                  disabled={!online}
                  onOpen={() => setSelected(item.id)}
                  onStatus={(status) => patch.mutate({ id: item.id, status })}
                  isTrash={filters.section === "trash"}
                  layout={view}
                  sourceActive={filters.source === item.source}
                  remoteActive={filters.remote === item.remote || filters.remote === remoteKind(item.remote)}
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
                      remote:
                        current.remote === item.remote || current.remote === remote ? "" : (item.remote ?? remote),
                      offset: 0,
                    }))
                  }
                  onKind={(kind) =>
                    setFilters((current) => {
                      const section = kind === "job" ? "jobs" : "announcements";
                      return switchOpportunitySection(current, section);
                    })
                  }
                  onTrash={() => void trash(item)}
                  onRestore={() => lifecycle.mutate({ action: "restore", id: item.id })}
                  onDelete={() => void permanentlyDelete(item)}
                  onSave={() => saveItem(item)}
                />
              ))}
            </OpportunityCollection>
            {browse.hasNextPage && (
              <div className="mt-5 flex items-center justify-center gap-3">
                <Button onClick={() => void browse.fetchNextPage()} disabled={browse.isFetchingNextPage}>
                  {browse.isFetchingNextPage ? "Yükleniyor…" : "Daha fazla"}
                </Button>
                <span className="text-meta text-muted">
                  {rows.length} / {total}
                </span>
              </div>
            )}
          </>
        )}
      </Section>

      {showSettings && <JobhunterSettings onClose={() => setShowSettings(false)} />}
      {selected && <OpportunityDetail id={selected} close={() => setSelected(null)} />}
    </PageFrame>
  );
}

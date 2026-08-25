import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { LayoutGrid, List, Search, Settings2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { Button, Checkbox, Empty, Input, PageFrame, PageHeader, RowList, Section, Toolbar, cx, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { navigate } from "@/app/router";
import type { Opportunity } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";
import { REMOTE_LABELS, STATUSES, remoteKind, statusLabel } from "./labels";
import { sourceLabel } from "@/core/labels";
import { OpportunityDetail } from "./OpportunityDetail";
import { JobhunterSettings } from "./JobhunterSettings";
import { FilterChip, OpportunityCard } from "./OpportunityList";
import { SourcePicker } from "./SourcePicker";
import { ApplicationCrmPanel } from "./ApplicationCrmPanel";
import { SyncProgress } from "./SyncProgress";

type OpportunityTab = "jobs" | "ylsy" | "osym" | "announcements" | "trash";

/** Ilk acilista gosterilen kart sayisi; "daha fazla" bu kadar daha ekler. */
const PAGE = 60;

/* ── Sayfa ────────────────────────────────────────────────────────── */

export function OpportunityPage() {
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();
  const [tab, setTab] = useState<OpportunityTab>("jobs");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [shown, setShown] = useState(PAGE);
  const [selected, setSelected] = useState<string | null>(null);
  /** "score" varsayilan: 645 kaydin cogu elenmis, en uygunlar one gelsin. */
  const [sort, setSort] = useState<"score" | "recent" | "deadline">("score");
  const [hideKilled, setHideKilled] = useState(true);
  /** Yatay satir / karesel kart gorunumu */
  const [view, setView] = useState<"rows" | "grid">("rows");
  /** Tiklanabilir chip filtreleri: kaynak + uzaktan/ofis */
  const [sourceFilter, setSourceFilter] = useState("");
  const [remoteFilter, setRemoteFilter] = useState<"" | "remote" | "hybrid" | "office">("");
  const [showSettings, setShowSettings] = useState(false);
  const [showCrm, setShowCrm] = useState(false);

  const [regionFilter, setRegionFilter] = useState("");
  // Tum kayitlar bir kere gelir; suzme ve arama istemcide. 500 satir icin
  // her suzgec degisiminde sunucuya gitmekten hizli ve sayilar tutarli kalir.
  const { data: allActive = [], isLoading } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get<Opportunity[]>(`/opportunities${qs({ limit: 2000 })}`),
  });
  const { data: trashData = [] } = useQuery({
    queryKey: ["opportunities", "trash"],
    queryFn: () => api.get<Opportunity[]>(`/opportunities${qs({ limit: 2000, trashed_only: true })}`),
  });

  const patch = useMutation({
    mutationFn: ({ id, status: next }: { id: string; status: string }) =>
      api.patch(`/opportunities/${id}`, { status: next }),
    onSuccess: () => invalidate("opportunities", "activity"),
  });
  const lifecycle = useMutation({
    mutationFn: ({ action, id }: { action: "trash" | "restore" | "delete"; id: string }) =>
      action === "delete"
        ? api.del(`/opportunities/${id}`)
        : api.post(`/opportunities/${id}/${action}`),
    onSuccess: (_, variables) => {
      invalidate("opportunities", "activity");
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

  const tabRows = useMemo<Record<OpportunityTab, Opportunity[]>>(() => ({
    jobs: allActive.filter((item) => item.kind === "job"),
    ylsy: allActive.filter((item) => item.source === "ylsy"),
    osym: allActive.filter((item) => item.source === "osym"),
    announcements: allActive.filter(
      (item) => item.kind !== "job" && item.source !== "ylsy" && item.source !== "osym",
    ),
    trash: trashData,
  }), [allActive, trashData]);
  const data = tabRows[tab];

  const filtered = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    const rows = data.filter((item) => {
      if (status && item.status !== status) return false;
      if (hideKilled && item.score !== null && item.score < 0) return false;
      if (sourceFilter && item.source !== sourceFilter) return false;
      if (remoteFilter && remoteKind(item.remote) !== remoteFilter) return false;
      if (regionFilter && item.region !== regionFilter) return false;
      if (!needle) return true;
      return [item.title, item.organization, item.location, item.source]
        .some((field) => field?.toLocaleLowerCase("tr").includes(needle));
    });
    const by = {
      // Puansiz kayit (elle girilmis, eski) en sona dussun.
      score: (a: Opportunity, b: Opportunity) => (b.score ?? -99) - (a.score ?? -99),
      recent: (a: Opportunity, b: Opportunity) =>
        new Date(b.found_at).getTime() - new Date(a.found_at).getTime(),
      deadline: (a: Opportunity, b: Opportunity) =>
        (a.deadline_at ? new Date(a.deadline_at).getTime() : Infinity)
        - (b.deadline_at ? new Date(b.deadline_at).getTime() : Infinity),
    }[sort];
    return [...rows].sort(by);
  }, [data, status, search, sort, hideKilled, sourceFilter, remoteFilter, regionFilter]);

  const killedCount = useMemo(
    () => data.filter((item) => item.score !== null && item.score < 0).length,
    [data],
  );

  const visible = filtered.slice(0, shown);
  const resetPage = () => setShown(PAGE);

  async function trash(item: Opportunity) {
    const ok = await confirmDialog({
      title: "Fırsat çöpe atılsın mı?",
      body: item.title,
      confirmLabel: "Çöpe at",
      tone: "danger",
    });
    if (ok) lifecycle.mutate({ action: "trash", id: item.id });
  }

  async function permanentlyDelete(item: Opportunity) {
    const ok = await confirmDialog({
      title: "Fırsat kalıcı silinsin mi?",
      body: <><strong>{item.title}</strong><br />Bu işlem geri alınamaz.</>,
      confirmLabel: "Kalıcı sil",
      tone: "danger",
    });
    if (ok) lifecycle.mutate({ action: "delete", id: item.id });
  }

  return (
    <PageFrame className="space-y-5">
      <PageHeader eyebrow="Takip" title="Fırsatlar" />

      {/* ── Arama ve eylemler ── */}
      <Toolbar className="sticky top-0 z-10 bg-canvas/95 backdrop-blur">
        <div className="relative min-w-[260px] flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-icon" />
          <Input
            value={search}
            onChange={(value) => { setSearch(value); resetPage(); }}
            placeholder="Başlık, kurum, konum ya da kaynakta ara…"
            ariaLabel="Fırsatlarda ara"
            className="w-full pl-9"
          />
        </div>
        <span className="min-w-2 flex-1" />
        <button
          type="button"
          onClick={() => setShowCrm((v) => !v)}
          title="Başvuru CRM özeti"
          className="flex h-9 items-center gap-1.5 rounded-control border border-subtle bg-surface px-3 text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
        >
          {showCrm ? "CRM gizle" : "CRM"}
        </button>
        <button
          type="button"
          onClick={() => setShowSettings(true)}
          title="Jobhunter ayarları"
          className="flex h-9 w-9 items-center justify-center rounded-control border border-subtle bg-surface text-muted transition hover:bg-surface-hover hover:text-primary"
        >
          <Settings2 size={15} />
        </button>
        <SourcePicker />
        <span className="flex items-center gap-1 rounded-control border border-subtle p-0.5">
          <button type="button" title="Yatay satırlar" onClick={() => setView("rows")}
            className={cx("flex h-7 w-7 items-center justify-center rounded-control transition", view === "rows" ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary")}>
            <List size={14} />
          </button>
          <button type="button" title="Karesel kartlar" onClick={() => setView("grid")}
            className={cx("flex h-7 w-7 items-center justify-center rounded-control transition", view === "grid" ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary")}>
            <LayoutGrid size={14} />
          </button>
        </span>
        <SyncProgress compact />
      </Toolbar>

      {/* ── Ana fırsat sekmeleri ── */}
      <nav className="flex flex-wrap gap-2" aria-label="Fırsat türleri">
        {([
          ["jobs", "İş İlanları"],
          ["ylsy", "YLSY"],
          ["osym", "ÖSYM"],
          ["announcements", "Diğer Duyurular"],
          ["trash", "Çöp"],
        ] as const).map(([value, label]) => (
          <FilterChip
            key={value}
            label={label}
            count={tabRows[value].length}
            active={tab === value}
            onClick={() => {
              setTab(value);
              setStatus("");
              setHideKilled(value !== "trash");
              resetPage();
            }}
          />
        ))}
      </nav>

      {/* ── Durum süzgeci ── */}
      <Section title="Durum">
        <div className="flex flex-wrap gap-2">
          <FilterChip
            label="Hepsi" count={data.length}
            active={status === ""} onClick={() => { setStatus(""); resetPage(); }}
          />
          {STATUSES.filter((value) => data.some((item) => item.status === value)).map((value) => (
            <FilterChip
              key={value}
              label={statusLabel(value)}
              count={data.filter((item) => item.status === value).length}
              active={status === value}
              onClick={() => { setStatus(value); resetPage(); }}
            />
          ))}
        </div>
      </Section>

      {/* ── Sıralama ── */}

      {/* ── Kaynak ve konum filtreleri (tiklanabilir chip ler) ── */}
      {showCrm && <ApplicationCrmPanel />}
      <Section title="Kaynak & konum">
        <div className="flex flex-wrap gap-2">
          <FilterChip label="Tümü" count={data.length} active={!sourceFilter && !remoteFilter}
            onClick={() => { setSourceFilter(""); setRemoteFilter(""); resetPage(); }} />
          {([["TR", "Türkiye"], ["EU", "Avrupa"], ["OTHER", "Diğer"]] as const).filter(([r]) => data.some((x) => x.region === r)).map(([r, label]) => (
            <FilterChip key={r} label={label} count={data.filter((x) => x.region === r).length}
              active={regionFilter === r}
              onClick={() => { setRegionFilter(regionFilter === r ? "" : r); resetPage(); }} />
          ))}
          {[...new Set(data.map((x) => x.source))].slice(0, 12).map((source) => (
            <FilterChip key={source} label={sourceLabel(source)} count={data.filter((x) => x.source === source).length}
              active={sourceFilter === source}
              onClick={() => { setSourceFilter(sourceFilter === source ? "" : source); resetPage(); }} />
          ))}
          {(["remote", "hybrid", "office"] as const).filter((k) => data.some((x) => remoteKind(x.remote) === k)).map((k) => (
            <FilterChip key={k} label={REMOTE_LABELS[k]} count={data.filter((x) => remoteKind(x.remote) === k).length}
              active={remoteFilter === k}
              onClick={() => { setRemoteFilter(remoteFilter === k ? "" : k); resetPage(); }} />
          ))}
        </div>
      </Section>

      <Section title="Sıralama">
        <div className="flex flex-wrap items-center gap-2">
          {([
            ["score", "En uygun"],
            ["recent", "En yeni"],
            ["deadline", "Son tarihe göre"],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => { setSort(value); resetPage(); }}
              aria-pressed={sort === value}
              className={cx(
                "flex h-8 items-center rounded-control border px-3 text-meta transition",
                sort === value
                  ? "border-accent bg-accent-surface font-medium text-accent"
                  : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
              )}
            >
              {label}
            </button>
          ))}

          {killedCount > 0 && (
            <Checkbox
              checked={hideKilled}
              onChange={() => { setHideKilled((v) => !v); resetPage(); }}
              label={<><span>Elenenleri gizle</span> <span className="numeral text-meta text-muted">{killedCount}</span></>}
              className="ml-2"
            />
          )}
        </div>
      </Section>

      {/* ── Kartlar ── */}
      <Section
          title="Fırsatlar"
          hint={filtered.length === data.length
            ? `${data.length} kayıt`
            : `${filtered.length} / ${data.length} kayıt`}
        >

        {isLoading ? (
          <p className="py-8 text-center text-meta text-muted">Yükleniyor…</p>
        ) : filtered.length === 0 ? (
          <Empty
            variant="page"
            title={data.length === 0 ? "Henüz fırsat yok" : "Bu süzgece uyan kayıt yok"}
            action={data.length === 0
              ? <Button variant="primary" onClick={() => navigate("/sources")}>Kaynakları çek</Button>
              : <Button onClick={() => { setStatus(""); setSearch(""); resetPage(); }}>Süzgeci temizle</Button>}
          >
            {data.length === 0
              ? "Worker kaynakları ilk turda dolduracak; beklemeden kendin de çekebilirsin."
              : "Aramayı daralt ya da tür/durum seçimini kaldır."}
          </Empty>
        ) : (
          <>
            <RowList>
              {visible.map((item) => (
                <OpportunityCard
                  key={item.id}
                  item={item}
                  disabled={!online}
                  onOpen={() => setSelected(item.id)}
                  onStatus={(next) => patch.mutate({ id: item.id, status: next })}
                  isTrash={tab === "trash"}
                  layout={view}
                  sourceActive={sourceFilter === item.source}
                  remoteActive={remoteFilter === remoteKind(item.remote)}
                  onSource={(s) => { setSourceFilter(sourceFilter === s ? "" : s); resetPage(); }}
                  onRemote={(k) => { setRemoteFilter(remoteFilter === k ? "" : k); resetPage(); }}
                  onKind={(kind) => {
                    setStatus("");
                    setHideKilled(true);
                    if (kind === "job") setTab("jobs");
                    else if (kind === "exam") setTab("osym");
                    else if (kind === "scholarship") setTab("ylsy");
                    else setTab("announcements");
                    resetPage();
                  }}
                  onTrash={() => trash(item)}
                  onRestore={() => lifecycle.mutate({ action: "restore", id: item.id })}
                  onDelete={() => permanentlyDelete(item)}
                />
              ))}
            </RowList>

            {filtered.length > visible.length && (
              <div className="mt-5 flex items-center justify-center gap-3">
                <Button onClick={() => setShown((n) => n + PAGE)}>
                  Daha fazla göster
                </Button>
                <span className="text-meta text-muted">
                  {visible.length} / {filtered.length}
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
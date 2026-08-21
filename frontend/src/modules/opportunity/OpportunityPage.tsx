import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ExternalLink, MapPin, RotateCcw, Search, Trash2 } from "lucide-react";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Input, SectionHeader, cx, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { navigate } from "@/app/router";
import type { Opportunity } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";
import {
  SCORE_LABEL, SCORE_TONE, STATUSES,
  daysLeft, kindLabel, scoreBand, sourceLabel, statusLabel,
} from "./labels";
import { OpportunityDetail } from "./OpportunityDetail";
import { SourcePicker } from "./SourcePicker";
import { SyncProgress } from "./SyncProgress";

type OpportunityTab = "jobs" | "ylsy" | "osym" | "announcements" | "trash";

/** Ilk acilista gosterilen kart sayisi; "daha fazla" bu kadar daha ekler. */
const PAGE = 60;

/* ── Suzgec cipi ──────────────────────────────────────────────────── */

function FilterChip({
  label, count, active, onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "flex h-8 items-center gap-2 rounded-control border px-3 text-meta transition",
        active
          ? "border-accent bg-accent-surface font-medium text-accent"
          : "border-subtle bg-surface text-secondary hover:bg-surface-hover hover:text-primary",
      )}
    >
      <span>{label}</span>
      <span className={cx("numeral text-[13px]", active ? "text-accent" : "text-muted")}>{count}</span>
    </button>
  );
}

/* ── Kart ─────────────────────────────────────────────────────────── */

function OpportunityCard({
  item, onOpen, onStatus, onTrash, onRestore, onDelete, disabled, isTrash,
}: {
  item: Opportunity;
  onOpen: () => void;
  onStatus: (status: string) => void;
  onTrash: () => void;
  onRestore: () => void;
  onDelete: () => void;
  disabled: boolean;
  isTrash: boolean;
}) {
  const left = daysLeft(item.deadline_at);
  const urgent = left !== null && left <= 7;
  const band = scoreBand(item.score);

  return (
    <article className={cx(
      "flex flex-col gap-2.5 rounded-card border bg-surface p-3.5 transition hover:border-strong",
      band === "killed" ? "border-subtle opacity-60" : "border-subtle",
    )}>
      <div className="flex items-start gap-2">
        <Badge tone="neutral">{kindLabel(item.kind)}</Badge>
        {band && (
          <Badge tone={SCORE_TONE[band]}>
            {band === "killed" ? SCORE_LABEL.killed : `${Math.round(item.score as number)} · ${SCORE_LABEL[band]}`}
          </Badge>
        )}
        <span className="flex-1" />
        {item.remote && <span className="shrink-0 text-meta text-muted">{item.remote}</span>}
      </div>

      <button
        type="button"
        onClick={onOpen}
        className="text-left text-heading leading-snug text-primary transition hover:text-accent"
      >
        <span className="line-clamp-2">{item.title}</span>
      </button>

      <div className="flex flex-col gap-1 text-meta text-muted">
        {item.organization && <span className="truncate text-secondary">{item.organization}</span>}
        {item.location && (
          <span className="flex items-center gap-1.5 truncate">
            <MapPin size={12} className="shrink-0 text-icon" />
            {item.location}
          </span>
        )}
        <span className="truncate">{sourceLabel(item.source)}</span>
      </div>

      {left !== null && (
        <p className={cx("text-meta", urgent ? "text-warn" : "text-secondary")}>
          {left < 0
            ? `Son tarih ${Math.abs(left)} gün önce geçti`
            : left === 0
              ? "Son gün bugün"
              : `Son tarihe ${left} gün`}
        </p>
      )}

      <div className="mt-auto flex items-center gap-2 border-t border-subtle pt-2.5">
        {isTrash ? (
          <>
            <Button size="sm" onClick={onRestore} disabled={disabled}>
              <RotateCcw size={13} /> Geri yükle
            </Button>
            <Button size="sm" variant="danger" onClick={onDelete} disabled={disabled}>
              Kalıcı sil
            </Button>
          </>
        ) : (
          <select
            value={item.status}
            disabled={disabled}
            aria-label="Durum"
            onChange={(e) => onStatus(e.target.value)}
            className="h-8 min-w-0 flex-1 rounded-control border border-subtle bg-canvas px-2 text-meta text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50"
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>{statusLabel(status)}</option>
            ))}
          </select>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            title="İlanı yeni sekmede aç"
            aria-label="İlanı yeni sekmede aç"
            className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary"
          >
            <ExternalLink size={14} />
          </a>
        )}
        {!isTrash && (
          <button
            type="button"
            onClick={onTrash}
            disabled={disabled}
            title="Çöpe at"
            aria-label={`${item.title} fırsatını çöpe at`}
            className="flex h-8 w-8 items-center justify-center rounded-control border border-subtle text-muted transition hover:border-danger hover:text-danger disabled:opacity-50"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </article>
  );
}

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
  }, [data, status, search, sort, hideKilled]);

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
    <div className="flex flex-col gap-6 p-8">

      {/* ── Arama ve eylemler ── */}
      <div className="flex flex-wrap items-center gap-3">
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
        <SourcePicker />
      </div>

      <SyncProgress compact />

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
      <section>
        <SectionHeader label="Durum" />
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
      </section>

      {/* ── Sıralama ── */}
      <section>
        <SectionHeader label="Sıralama" />
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
            <label className="ml-2 flex cursor-pointer items-center gap-2.5 text-meta text-secondary">
              <input
                type="checkbox"
                checked={hideKilled}
                onChange={() => { setHideKilled((v) => !v); resetPage(); }}
                className="h-4 w-4 accent-[var(--accent)]"
              />
              Elenenleri gizle
              <span className="numeral text-[13px] text-muted">{killedCount}</span>
            </label>
          )}
        </div>
      </section>

      {/* ── Kartlar ── */}
      <section>
        <SectionHeader
          label="Fırsatlar"
          hint={filtered.length === data.length
            ? `${data.length} kayıt`
            : `${filtered.length} / ${data.length} kayıt`}
        />

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
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {visible.map((item) => (
                <OpportunityCard
                  key={item.id}
                  item={item}
                  disabled={!online}
                  onOpen={() => setSelected(item.id)}
                  onStatus={(next) => patch.mutate({ id: item.id, status: next })}
                  isTrash={tab === "trash"}
                  onTrash={() => trash(item)}
                  onRestore={() => lifecycle.mutate({ action: "restore", id: item.id })}
                  onDelete={() => permanentlyDelete(item)}
                />
              ))}
            </div>

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
      </section>

      {selected && <OpportunityDetail id={selected} close={() => setSelected(null)} />}
    </div>
  );
}

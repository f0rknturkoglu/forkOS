import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  CheckCircle2,
  Flower2,
  Leaf,
  Maximize2,
  MoonStar,
  Pencil,
  Pause,
  Play,
  Plus,
  Settings2,
  Sprout,
  Timer,
  Trash2,
  XCircle,
} from "lucide-react";
import { confirmDialog } from "@/core/dialog";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { PomodoroAnalytics, PomodoroDailyPoint, PomodoroSession } from "@/core/types";
import {
  Button,
  Checkbox,
  Empty,
  Field,
  IconButton,
  Input,
  PageFrame,
  RowList,
  Section,
  cx,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea, WorkspaceToolbar } from "@/core/workspace/Workspace";
import { useOnline } from "@/lib/hooks";
import { ContextChip, ContextPicker } from "./ContextPicker";
import { FocusMode } from "./FocusMode";
import { BREAK_MIN, FOCUS_MIN, focusPreferences, setFocusPreferences, type FocusPreferences } from "./preferences";
import { useActivePomodoro, usePomodoroClock } from "./queries";
import { clock, remaining } from "./time";

type FocusTab = "focus" | "stats" | "settings";
type AnalyticsRange = "week" | "month" | "all";

const TABS: { id: FocusTab; label: string; icon: typeof Timer }[] = [
  { id: "focus", label: "Odaklan", icon: Timer },
  { id: "stats", label: "İstatistikler", icon: BarChart3 },
  { id: "settings", label: "Ayarlar", icon: Settings2 },
];

const RANGE_LABELS: { id: AnalyticsRange; label: string }[] = [
  { id: "week", label: "Bu hafta" },
  { id: "month", label: "Bu ay" },
  { id: "all", label: "Tümü" },
];

const KIND_LABELS: Record<string, string> = {
  focus: "odak",
  short_break: "kısa mola",
  long_break: "uzun mola",
};

function durationLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} dk`;
  return rest ? `${hours} sa ${rest} dk` : `${hours} sa`;
}

function dateLabel(value: string): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString("tr-TR", { weekday: "short", day: "numeric" });
}

function sessionTitle(session: PomodoroSession): string {
  return session.topic || session.context_title || KIND_LABELS[session.kind] || "Odak";
}

function useAmoled(enabled: boolean) {
  useEffect(() => {
    if (enabled) document.documentElement.dataset.focusAmoled = "true";
    else delete document.documentElement.dataset.focusAmoled;
    return () => {
      delete document.documentElement.dataset.focusAmoled;
    };
  }, [enabled]);
}

export function PomodoroPage() {
  const params = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  const [tab, setTab] = useState<FocusTab>("focus");
  const [range, setRange] = useState<AnalyticsRange>("week");
  const [preferences, setPreferencesState] = useState<FocusPreferences>(focusPreferences);
  const [focusMode, setFocusMode] = useState(false);
  const [minutes, setMinutes] = useState(preferences.focusMinutes);
  const [topic, setTopic] = useState(params.get("title") ?? params.get("topic") ?? "");
  const [context, setContext] = useState(params.get("context") ?? "");
  const online = useOnline();
  const toast = useToast();

  useAmoled(preferences.amoled);

  const { data: active = null } = useActivePomodoro();
  const now = usePomodoroClock(active);
  const [historyPage, setHistoryPage] = useState(0);
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["pomodoro-analytics", range],
    queryFn: () => api.get<PomodoroAnalytics>(`/pomodoro/analytics?range=${range}`),
  });
  const historyQuery = useQuery({
    queryKey: ["pomodoro-sessions", historyPage],
    queryFn: () => api.get<PomodoroSession[]>(`/pomodoro/sessions?limit=80&offset=${historyPage * 80}`),
  });

  const sessions = historyQuery.data ?? [];
  const refresh = () => invalidateAfter("pomodoro.write");
  const start = useMutation({
    mutationFn: (kind: "focus" | "short_break") =>
      api.post("/pomodoro/start", {
        planned_min: kind === "focus" ? minutes : preferences.breakMinutes,
        kind,
        topic: kind === "focus" ? topic.trim() || undefined : undefined,
        context_entity_id: kind === "focus" ? context || undefined : undefined,
      }),
    onSuccess: refresh,
    onError: () => toast.push("Başlatılamadı — aktif bir seans olabilir.", { tone: "danger" }),
  });
  const stop = useMutation({
    mutationFn: (interrupted: boolean) => api.post(`/pomodoro/${active?.id}/stop`, { interrupted }),
    onSuccess: refresh,
  });
  const togglePause = useMutation({
    mutationFn: () => api.post(`/pomodoro/${active?.id}/${active?.paused_at ? "resume" : "pause"}`),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/pomodoro/${id}`),
    onSuccess: () => {
      refresh();
      toast.push("Seans silindi", { tone: "ok" });
    },
  });

  const left = remaining(active, now);
  const paused = Boolean(active?.paused_at);
  useEffect(() => {
    if (active && !paused && left === 0 && !stop.isPending && online) stop.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, active?.id, paused, online]);

  function updatePreferences(next: FocusPreferences) {
    setPreferencesState(next);
    setFocusPreferences(next);
  }

  return (
    <>
      <PageFrame>
        <Workspace>
          <WorkspacePaneHeader
            eyebrow="Planlama"
            title="Odak"
            hint={new Date().toLocaleDateString("tr-TR", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          />

          <WorkspaceToolbar
            left={
              <nav aria-label="Odak bölümleri" className="flex items-center gap-1">
                {TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    aria-current={tab === id ? "page" : undefined}
                    onClick={() => setTab(id)}
                    className={cx(
                      "flex h-8 items-center gap-1.5 rounded-control px-2.5 text-meta transition-colors",
                      tab === id
                        ? "bg-surface-selected font-medium text-primary"
                        : "text-muted hover:bg-surface-hover hover:text-primary",
                    )}
                  >
                    <Icon size={14} /> {label}
                  </button>
                ))}
              </nav>
            }
          />

          <WorkspaceScrollArea className="stack-y-4 p-4 sm:p-6">
            {tab === "focus" && (
              <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1.6fr)_minmax(20rem,0.72fr)]">
                <div className="stack-y-3">
                  <FocusGarden
                    points={analytics?.daily ?? []}
                    totalMinutes={analytics?.minutes ?? 0}
                    loading={analyticsLoading}
                  />
                  <FocusComposer
                    active={active}
                    left={left}
                    paused={paused}
                    minutes={minutes}
                    topic={topic}
                    context={context}
                    breakMinutes={preferences.breakMinutes}
                    online={online}
                    pending={start.isPending || stop.isPending || togglePause.isPending}
                    onMinutes={setMinutes}
                    onTopic={setTopic}
                    onContext={setContext}
                    onStart={() => start.mutate("focus")}
                    onBreak={() => start.mutate("short_break")}
                    onPause={() => togglePause.mutate()}
                    onComplete={() => stop.mutate(false)}
                    onInterrupt={() => stop.mutate(true)}
                    onFullscreen={() => setFocusMode(true)}
                  />
                </div>

                <div className="stack-y-3">
                  <FocusTrend points={analytics?.daily ?? []} />
                  <SessionList
                    sessions={sessions.slice(0, 8)}
                    title="Son odak seansları"
                    onShowAll={() => setTab("stats")}
                    onRemove={async (id) => {
                      if (
                        await confirmDialog({
                          title: "Seans silinsin mi?",
                          body: "Bu geçmiş seansı ve süresi kaldırılır. Olay geçmişi korunur.",
                          confirmLabel: "Seansı sil",
                        })
                      )
                        remove.mutate(id);
                    }}
                    removePending={remove.isPending}
                  />
                </div>
              </div>
            )}

            {tab === "stats" && (
              <div className="mt-4 stack-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-title text-primary">Odak analizi</h2>
                    <p className="text-meta text-muted">Tamamlanan ve yarıda kesilen odak bloklarından hesaplanır.</p>
                  </div>
                  <div className="flex rounded-control border border-subtle bg-surface p-1">
                    {RANGE_LABELS.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        aria-pressed={range === item.id}
                        onClick={() => setRange(item.id)}
                        className={cx(
                          "rounded-control px-3 py-1.5 text-meta transition-colors",
                          range === item.id ? "bg-primary text-canvas" : "text-muted hover:text-primary",
                        )}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 lg:grid-cols-3">
                  <StatValue label="Toplam odak" value={durationLabel(analytics?.minutes ?? 0)} />
                  <StatValue label="Tamamlanan" value={String(analytics?.completed ?? 0)} />
                  <StatValue label="Yarıda kesilen" value={String(analytics?.interrupted ?? 0)} />
                </div>

                <div className="grid gap-3 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                  <ContextBreakdown analytics={analytics} />
                  <SessionList
                    sessions={sessions}
                    title="Etkinlik geçmişi"
                    error={historyQuery.isError ? "Seans geçmişi yüklenemedi" : undefined}
                    loading={historyQuery.isLoading}
                    onRetry={() => void historyQuery.refetch()}
                    historyPage={historyPage}
                    onPage={setHistoryPage}
                    onRemove={async (id) => {
                      if (
                        await confirmDialog({
                          title: "Seans silinsin mi?",
                          body: "Bu geçmiş seansı ve süresi kaldırılır. Olay geçmişi korunur.",
                          confirmLabel: "Seansı sil",
                        })
                      )
                        remove.mutate(id);
                    }}
                    removePending={remove.isPending}
                    allowManual
                    onManualDone={refresh}
                  />
                </div>
              </div>
            )}

            {tab === "settings" && (
              <FocusSettings
                value={preferences}
                onChange={updatePreferences}
                onUseDefault={() => setMinutes(preferences.focusMinutes)}
              />
            )}
          </WorkspaceScrollArea>
        </Workspace>
      </PageFrame>

      {focusMode && active && <FocusMode onClose={() => setFocusMode(false)} />}
    </>
  );
}

function FocusGarden({
  points,
  totalMinutes,
  loading,
}: {
  points: PomodoroDailyPoint[];
  totalMinutes: number;
  loading: boolean;
}) {
  const visible = points.slice(-7);
  return (
    <Section
      title="Bu haftanın bahçesi"
      hint={loading ? "hesaplanıyor" : `Toplam ${durationLabel(totalMinutes)}`}
      bodyClassName="p-0"
    >
      <p className="px-4 pt-3 text-meta text-muted">Tamamladığın her odak seansı burada büyür.</p>
      {visible.length === 0 ? (
        <div className="m-4">
          <Empty>İlk odak bloğunu tamamladığında bahçen burada filizlenecek.</Empty>
        </div>
      ) : (
        <div
          className="mt-3 grid min-h-64 grid-cols-7 stack-divide-x divide-subtle border-y border-subtle"
          role="img"
          aria-label="Haftalık odak bahçesi"
        >
          {visible.map((point, index) => (
            <GardenDay key={point.date} point={point} index={index} />
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-meta text-muted">
        <span>Her gün biraz daha derinleşen çalışma alanın.</span>
        <span className="flex items-center gap-1.5">
          <Sprout size={14} className="text-ok" /> tamamlanan seans
        </span>
      </div>
    </Section>
  );
}

function GardenDay({ point, index }: { point: PomodoroDailyPoint; index: number }) {
  const count = Math.min(4, point.sessions);
  const icons = [Sprout, Leaf, Flower2, Sprout];
  return (
    <div
      className="flex min-w-0 flex-col items-center px-1 py-3 text-center"
      title={`${point.date}: ${durationLabel(point.minutes)}`}
    >
      <span className="text-micro text-muted">{dateLabel(point.date)}</span>
      <span className="mt-1 text-meta font-medium tabular-nums text-secondary">{durationLabel(point.minutes)}</span>
      <div className="flex min-h-36 flex-1 flex-wrap content-end items-end justify-center gap-1.5 pb-3 pt-4">
        {count === 0 ? (
          <span className="h-1.5 w-1.5 rounded-full bg-strong" aria-hidden />
        ) : (
          Array.from({ length: count }, (_, itemIndex) => {
            const Plant = icons[(index + itemIndex) % icons.length];
            return <Plant key={itemIndex} size={20 + itemIndex * 3} className="text-ok" aria-hidden />;
          })
        )}
      </div>
      <span className="text-micro text-muted">{point.sessions} seans</span>
    </div>
  );
}

function FocusTrend({ points }: { points: PomodoroDailyPoint[] }) {
  const visible = points.slice(-7);
  const max = Math.max(1, ...visible.map((point) => point.minutes));
  return (
    <Section title="Haftalık odak trendi" bodyClassName="pb-3">
      {visible.length === 0 ? (
        <Empty>Grafik için henüz odak kaydı yok.</Empty>
      ) : (
        <div className="flex h-44 items-end gap-2" role="img" aria-label="Günlere göre odak dakikaları">
          {visible.map((point) => (
            <div key={point.date} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1.5">
              <span className="text-micro tabular-nums text-secondary">{point.minutes || ""}</span>
              <div className="flex h-28 w-full items-end rounded-t-control bg-surface-sunken">
                <div
                  className={cx("w-full rounded-t-control", point.minutes ? "bg-ok" : "bg-subtle")}
                  style={{ height: `${point.minutes ? Math.max(8, (point.minutes / max) * 100) : 2}%` }}
                />
              </div>
              <span className="truncate text-micro text-muted">{dateLabel(point.date).split(" ")[0]}</span>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function FocusComposer({
  active,
  left,
  paused,
  minutes,
  topic,
  context,
  breakMinutes,
  online,
  pending,
  onMinutes,
  onTopic,
  onContext,
  onStart,
  onBreak,
  onPause,
  onComplete,
  onInterrupt,
  onFullscreen,
}: {
  active: PomodoroSession | null;
  left: number;
  paused: boolean;
  minutes: number;
  topic: string;
  context: string;
  breakMinutes: number;
  online: boolean;
  pending: boolean;
  onMinutes: (value: number) => void;
  onTopic: (value: string) => void;
  onContext: (value: string) => void;
  onStart: () => void;
  onBreak: () => void;
  onPause: () => void;
  onComplete: () => void;
  onInterrupt: () => void;
  onFullscreen: () => void;
}) {
  if (active) {
    const progress =
      active.planned_min > 0 ? Math.max(0, Math.min(100, 100 - (left / (active.planned_min * 60)) * 100)) : 0;
    return (
      <Section title={paused ? "Odak duraklatıldı" : "Odak devam ediyor"} hint={`${active.planned_min} dk planlandı`}>
        <div className="grid items-center gap-5 md:grid-cols-[minmax(12rem,0.65fr)_minmax(0,1fr)]">
          <div>
            <div className={cx("numeral text-display-xl leading-none", paused ? "text-muted" : "text-primary")}>
              {clock(left)}
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
              <div className="h-full rounded-full bg-ok transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div>
            <p className="truncate text-title text-primary">{sessionTitle(active)}</p>
            <p className="mt-1 flex items-center gap-1.5 text-meta text-muted">
              <ContextChip type={active.context_type} />
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" disabled={!online || pending} onClick={onFullscreen}>
                <Maximize2 size={14} /> tam ekran
              </Button>
              <Button disabled={!online || pending} onClick={onPause}>
                {paused ? <Play size={14} /> : <Pause size={14} />}
                {paused ? "devam et" : "duraklat"}
              </Button>
              <Button variant="ok" disabled={!online || pending} onClick={onComplete}>
                <CheckCircle2 size={14} /> tamamla
              </Button>
              <Button variant="danger" disabled={!online || pending} onClick={onInterrupt}>
                <XCircle size={14} /> yarıda kes
              </Button>
            </div>
          </div>
        </div>
      </Section>
    );
  }

  return (
    <Section
      title="Yeni odak seansı"
      action={
        <Button size="sm" disabled={!online || pending} onClick={onBreak}>
          {breakMinutes} dk mola
        </Button>
      }
    >
      <div className="grid gap-5 md:grid-cols-[minmax(12rem,0.65fr)_minmax(0,1fr)]">
        <div className="md:border-r md:border-subtle md:pr-5">
          <div className="numeral text-display-xl leading-none text-primary">{minutes} dk</div>
          <div className="mt-4 flex flex-wrap gap-2">
            {[25, 50, 90].map((preset) => (
              <Button
                key={preset}
                size="sm"
                variant={minutes === preset ? "ok" : "secondary"}
                onClick={() => onMinutes(preset)}
              >
                {preset} dk
              </Button>
            ))}
          </div>
        </div>
        <div className="stack-y-3">
          <Field label="Konu">
            <Input value={topic} onChange={onTopic} placeholder="Neye odaklanıyorsun?" className="w-full" />
          </Field>
          <ContextPicker value={context} onChange={onContext} />
          <Button variant="success" className="w-full" disabled={!online || pending} onClick={onStart}>
            <Play size={14} /> odaklanmaya başla
          </Button>
        </div>
      </div>
    </Section>
  );
}

function StatValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-subtle bg-surface px-4 py-4">
      <p className="numeral text-display text-primary">{value}</p>
      <p className="mt-1 text-meta text-muted">{label}</p>
    </div>
  );
}

function ContextBreakdown({ analytics }: { analytics: PomodoroAnalytics | undefined }) {
  const contexts = analytics?.contexts ?? [];
  return (
    <Section title="Neye vakit ayırdın?">
      {contexts.length === 0 ? (
        <Empty>Bağlam dağılımı için henüz odak kaydı yok.</Empty>
      ) : (
        <div className="stack-y-4">
          {contexts.map((item) => (
            <div key={item.context_entity_id ?? item.title}>
              <div className="mb-1.5 flex items-center gap-2 text-meta">
                <span className="min-w-0 flex-1 truncate text-primary">{item.title}</span>
                <ContextChip type={item.context_type} />
                <span className="tabular-nums text-muted">{durationLabel(item.minutes)}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                <div className="h-full rounded-full bg-accent" style={{ width: `${item.share}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function SessionList({
  sessions,
  loading,
  error,
  onRetry,
  historyPage,
  onPage,
  title,
  onShowAll,
  onRemove,
  removePending,
  allowManual = false,
  onManualDone,
}: {
  sessions: PomodoroSession[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  historyPage?: number;
  onPage?: (page: number) => void;
  title: string;
  onShowAll?: () => void;
  onRemove: (id: string) => void;
  removePending: boolean;
  allowManual?: boolean;
  onManualDone?: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<PomodoroSession | null>(null);
  const online = useOnline();
  return (
    <Section
      title={title}
      action={
        <div className="flex items-center gap-2">
          {onPage && (
            <>
              <Button size="sm" disabled={!historyPage} onClick={() => onPage(Math.max(0, (historyPage ?? 0) - 1))}>
                Daha yeni
              </Button>
              <Button size="sm" disabled={sessions.length < 80} onClick={() => onPage((historyPage ?? 0) + 1)}>
                Daha eski
              </Button>
            </>
          )}
          {allowManual && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setAdding(!(adding || editing));
                setEditing(null);
              }}
            >
              <Plus size={13} />
              {adding || editing ? "vazgeç" : "elle ekle"}
            </Button>
          )}
          {onShowAll && (
            <Button size="sm" variant="ghost" onClick={onShowAll}>
              tümünü gör
            </Button>
          )}
        </div>
      }
      bodyClassName="p-0"
    >
      {(adding || editing) && (
        <div className="border-b border-subtle p-3">
          <ManualForm
            key={editing?.id ?? "new"}
            session={editing ?? undefined}
            onDone={() => {
              setAdding(false);
              setEditing(null);
              invalidateAfter("pomodoro.write");
              onManualDone?.();
            }}
          />
        </div>
      )}
      {error ? (
        <div role="alert" className="p-3 text-body text-danger">
          {error} <Button onClick={onRetry}>Yeniden dene</Button>
        </div>
      ) : loading ? (
        <p role="status" className="p-3 text-body text-muted">
          Geçmiş yükleniyor…
        </p>
      ) : sessions.length === 0 ? (
        <div className="m-3">
          <Empty>Henüz kayıtlı seans yok.</Empty>
        </div>
      ) : (
        <RowList as="ul">
          {sessions.map((session) => (
            <li key={session.id} className="flex items-center gap-3 px-3.5 py-2.5">
              <span
                className={cx(
                  "h-2 w-2 shrink-0 rounded-full",
                  session.interrupted ? "bg-danger" : session.kind === "focus" ? "bg-ok" : "bg-icon",
                )}
                aria-hidden
              />
              <span className="min-w-0 flex-1">
                <span className="flex min-w-0 items-center gap-1.5">
                  <span className="truncate text-body text-primary">{sessionTitle(session)}</span>
                  <ContextChip type={session.context_type} />
                </span>
                <span className="mt-0.5 block text-meta text-muted">
                  {new Date(session.started_at).toLocaleString("tr-TR", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                  {session.source === "manual" ? " · Elle eklendi" : " · Sayaç"}
                  {session.interrupted ? " · yarıda kesildi" : ""}
                </span>
              </span>
              <span className="shrink-0 text-meta tabular-nums text-secondary">
                {durationLabel(session.actual_min ?? 0)}
              </span>
              <IconButton
                title="Seansı düzenle"
                disabled={!online || removePending}
                onClick={() => {
                  setAdding(false);
                  setEditing(session);
                }}
              >
                <Pencil size={14} />
              </IconButton>
              <IconButton
                title="Seansı sil"
                tone="danger"
                disabled={!online || removePending}
                onClick={() => onRemove(session.id)}
              >
                <Trash2 size={14} />
              </IconButton>
            </li>
          ))}
        </RowList>
      )}
    </Section>
  );
}

function FocusSettings({
  value,
  onChange,
  onUseDefault,
}: {
  value: FocusPreferences;
  onChange: (value: FocusPreferences) => void;
  onUseDefault: () => void;
}) {
  return (
    <div className="mt-4 max-w-2xl stack-y-3">
      <Section title="Görünüm">
        <Checkbox
          checked={value.amoled}
          onChange={(amoled) => onChange({ ...value, amoled })}
          label={
            <span>
              <span className="flex items-center gap-1.5 text-body text-primary">
                <MoonStar size={14} /> AMOLED karanlık
              </span>
              <span className="mt-0.5 block text-meta text-muted">
                Odak sayfasını ve tam ekran sayacı gerçek siyah, düşük dikkat dağıtan yüzeylerle gösterir.
              </span>
            </span>
          }
        />
      </Section>
      <Section title="Varsayılan süreler">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Odak süresi (dk)">
            <Input
              type="number"
              value={String(value.focusMinutes)}
              onChange={(raw) =>
                onChange({ ...value, focusMinutes: Math.max(1, Math.min(240, Number(raw) || FOCUS_MIN)) })
              }
              className="w-full"
            />
          </Field>
          <Field label="Mola süresi (dk)">
            <Input
              type="number"
              value={String(value.breakMinutes)}
              onChange={(raw) =>
                onChange({ ...value, breakMinutes: Math.max(1, Math.min(60, Number(raw) || BREAK_MIN)) })
              }
              className="w-full"
            />
          </Field>
        </div>
        <Button className="mt-3" onClick={onUseDefault}>
          Yeni seansa uygula
        </Button>
      </Section>
      <Section title="Veri yaklaşımı">
        <p className="text-body text-secondary">
          Bahçe ve grafikler yalnızca bu cihazdaki forkOS veritabanından hesaplanır. Dış servise analiz veya kullanım
          verisi gönderilmez.
        </p>
      </Section>
    </div>
  );
}

function ManualForm({ onDone, session }: { onDone: () => void; session?: PomodoroSession }) {
  const [when, setWhen] = useState(() => {
    const date = new Date(session?.started_at ?? Date.now() - FOCUS_MIN * 60_000);
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 16);
  });
  const [minutes, setMinutes] = useState(session?.actual_min ?? FOCUS_MIN);
  const [topic, setTopic] = useState(session?.topic ?? "");
  const [context, setContext] = useState(session?.context_entity_id ?? "");
  const online = useOnline();
  const toast = useToast();
  const add = useMutation({
    mutationFn: () => {
      const body = {
        started_at: new Date(when).toISOString(),
        minutes,
        topic: topic.trim() || undefined,
        context_entity_id: context || null,
        kind: session?.kind ?? "focus",
      };
      return session ? api.put(`/pomodoro/${session.id}`, body) : api.post("/pomodoro", body);
    },
    onSuccess: () => {
      invalidateAfter("pomodoro.write");
      toast.push(session ? "Seans güncellendi" : "Seans işlendi", { tone: "ok" });
      onDone();
    },
    onError: (error) => toast.push(`Kaydedilemedi: ${error.message}`, { tone: "danger" }),
  });
  return (
    <form
      className="grid gap-3 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        add.mutate();
      }}
    >
      <Field label="Başlangıç">
        <Input type="datetime-local" value={when} onChange={setWhen} className="w-full" />
      </Field>
      <Field label="Süre (dk)">
        <Input
          type="number"
          value={String(minutes)}
          onChange={(raw) => setMinutes(Math.max(1, Math.min(600, Number(raw) || FOCUS_MIN)))}
          className="w-full"
        />
      </Field>
      <Field label="Konu">
        <Input value={topic} onChange={setTopic} placeholder="Ne üzerinde çalıştın?" className="w-full" />
      </Field>
      <ContextPicker value={context} onChange={setContext} />
      <Button type="submit" variant="primary" disabled={!online || add.isPending}>
        {session ? "Değişiklikleri kaydet" : "Seansı işle"}
      </Button>
    </form>
  );
}

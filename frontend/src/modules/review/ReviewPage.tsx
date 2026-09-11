import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, CheckCircle2, Clock3, RotateCcw, Sparkles, Target } from "lucide-react";
import { invalidateAfter } from "@/core/invalidation";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  Empty,
  Input,
  Metric,
  MetricStrip,
  PageFrame,
  RowList,
  Section,
  Surface,
  Textarea,
  cx,
  hostOf,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import type { Bookmark, ReviewPreview } from "@/core/types";
import { navigate } from "@/app/router";
import { appWeekStartKey, formatTrDate, formatTrDateTime, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { reviewMetricRows } from "./reviewMetrics";
import { InboxFocusTriageModal } from "@/modules/inbox/InboxFocusTriageModal";

function startOf(kind: "daily" | "weekly") {
  return kind === "weekly" ? appWeekStartKey() : todayKey();
}

function shortDate(value: string): string {
  return formatTrDate(`${value}T12:00:00`, { day: "numeric", month: "short" });
}

function dayLabel(value?: string | null): string {
  if (!value) return "—";
  return formatTrDate(`${value}T12:00:00`, { weekday: "short", day: "numeric", month: "short" });
}

function ReviewFlow({ kind }: { kind: "daily" | "weekly" }) {
  const [step, setStep] = useState(1);
  const [note, setNote] = useState("");
  const [decisions, setDecisions] = useState<Record<string, "carry" | "drop">>({});
  const [priorities, setPriorities] = useState(["", "", ""]);
  const online = useOnline();
  const toast = useToast();
  const period = useMemo(() => startOf(kind), [kind]);
  const { data, isLoading } = useQuery({
    queryKey: ["review-preview", kind, period],
    queryFn: () => api.get<ReviewPreview>(`/reviews/preview${qs({ kind, period_start: period })}`),
  });
  const save = useMutation({
    mutationFn: () =>
      api.post("/reviews", {
        kind,
        period_start: period,
        note: note || undefined,
        decisions: {
          carry_over: Object.entries(decisions)
            .filter(([, value]) => value === "carry")
            .map(([id]) => id),
          drop: Object.entries(decisions)
            .filter(([, value]) => value === "drop")
            .map(([id]) => id),
          priorities: priorities.filter(Boolean),
        },
      }),
    onSuccess: () => {
      invalidateAfter("review.write");
      setStep(4);
      navigate(`/review/${kind}`);
    },
  });

  if (isLoading || !data) return <p className="p-6 text-body text-muted">Değerlendirme hesaplanıyor…</p>;

  const stats = data.stats;
  const decidedCount = Object.keys(decisions).length;
  const waitingCount = data.unfinished_todos.length - decidedCount;
  const totalOutcomes = data.completed_todos.length + data.unfinished_todos.length;
  const completionPct = totalOutcomes ? Math.round((data.completed_todos.length / totalOutcomes) * 100) : 0;
  // Kaydedilmemis karar/oncelik/not varken ust adim cipine tiklamak veriyi
  // sessizce atlamaz: ileri atlama engellenir, geri gitmek serbesttir.
  const dirty = Object.keys(decisions).length > 0 || priorities.some(Boolean) || note.trim() !== "";
  function selectStep(next: number) {
    if (next <= step) {
      setStep(next);
      return;
    }
    if (dirty) {
      toast.push("Önce bu adımı tamamla — kaydedilmemiş değişiklikler var.", { tone: "warn" });
      return;
    }
    setStep(next);
  }

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Değerlendirme"
          title={kind === "weekly" ? "Haftalık değerlendirme" : "Günlük değerlendirme"}
          hint={`${shortDate(data.period_start)} → ${shortDate(data.period_end)}`}
          action={step < 4 ? <ReviewSteps current={step} onSelect={selectStep} /> : undefined}
        />
        <WorkspaceScrollArea className="p-3">
          {step === 1 && <OverviewStep data={data} completionPct={completionPct} onNext={() => setStep(2)} />}

          {step === 2 && (
            <DecisionsStep
              todos={data.unfinished_todos}
              decisions={decisions}
              waitingCount={waitingCount}
              onDecision={(id, value) => setDecisions((old) => ({ ...old, [id]: value }))}
              onCarryAll={() =>
                setDecisions(Object.fromEntries(data.unfinished_todos.map((todo) => [todo.id, "carry"])))
              }
              onBack={() => setStep(1)}
              onNext={() => setStep(3)}
            />
          )}

          {step === 3 && (
            <PrioritiesStep
              kind={kind}
              priorities={priorities}
              onPriority={(index, value) =>
                setPriorities((old) => old.map((item, itemIndex) => (itemIndex === index ? value : item)))
              }
              note={note}
              onNote={setNote}
              carried={Object.values(decisions).filter((value) => value === "carry").length}
              dropped={Object.values(decisions).filter((value) => value === "drop").length}
              focusMinutes={stats.focus.minutes}
              completed={data.completed_todos.length}
              online={online}
              pending={save.isPending}
              onBack={() => setStep(2)}
              onSave={() => save.mutate()}
            />
          )}

          {step === 4 && (
            <Surface className="p-8 text-center">
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-ok-surface text-ok">
                <Check size={22} />
              </span>
              <h2 className="mt-4 text-title text-primary">Hafta kapandı</h2>
              <p className="mx-auto mt-2 max-w-xl text-body text-secondary">
                Kararların plana işlendi; seçtiğin öncelikler yeni haftanın başlangıcına eklendi.
              </p>
            </Surface>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

function ReviewSteps({ current, onSelect }: { current: number; onSelect: (step: number) => void }) {
  const steps = [
    [1, "Özet"],
    [2, "Kararlar"],
    [3, "Öncelikler"],
  ] as const;
  return (
    <nav aria-label="Değerlendirme adımları" className="flex items-center gap-1.5">
      {steps.map(([value, label]) => (
        <button
          key={value}
          type="button"
          onClick={() => onSelect(value)}
          className={cx(
            "flex items-center gap-2 rounded-control border px-3 py-2 text-meta transition",
            current === value
              ? "border-accent-border bg-accent-surface text-accent"
              : current > value
                ? "border-subtle bg-surface text-secondary hover:bg-surface-hover"
                : "border-transparent text-muted hover:bg-surface-hover",
          )}
        >
          <span
            className={cx(
              "flex h-5 w-5 items-center justify-center rounded-full border text-micro",
              current >= value ? "border-accent-border bg-accent text-canvas" : "border-strong",
            )}
          >
            {current > value ? <Check size={11} /> : value}
          </span>
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </nav>
  );
}

function OverviewStep({
  data,
  completionPct,
  onNext,
}: {
  data: ReviewPreview;
  completionPct: number;
  onNext: () => void;
}) {
  const [triageOpen, setTriageOpen] = useState(false);
  const { data: rawInboxItems = [] } = useQuery({
    queryKey: ["bookmarks", "inbox", "review-check"],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs({ collection: "inbox", limit: 50 })}`),
  });
  const inboxItems = Array.isArray(rawInboxItems) ? rawInboxItems : [];

  const stats = data.stats;
  const maxTopic = Math.max(...stats.topics.map((topic) => topic.minutes), 1);
  const signals = [
    ["Rutin tamamlamaları", Object.values(stats.habits).reduce((total, value) => total + value, 0)],
    ["Kart tekrarı", stats.flashcards.reviewed],
    ["Yeni not", stats.capture.notes],
    ["Kaydedilen kaynak", stats.capture.bookmarks],
    ["Okunan RSS", stats.capture.rss_read],
    ["GitHub commit", stats.github.commits],
    ["Güncellenen fırsat", stats.applications.updated],
    ["En uzun odak", `${stats.focus.longest_session} dk`],
    ["Yarıda kesilen", stats.focus.interrupted],
  ] as const;

  return (
    <div className="space-y-5">
      <MetricStrip className="grid-cols-2 lg:grid-cols-4">
        <Metric label="Tamamlama" value={`%${completionPct}`} hint={`${data.completed_todos.length} görev bitti`} />
        {reviewMetricRows(stats)
          .slice(1)
          .map(([label, value], index) => (
            <Metric
              key={label}
              label={label}
              value={value}
              hint={index === 0 ? `${stats.focus.sessions} tamamlanan seans` : undefined}
            />
          ))}
      </MetricStrip>

      <div className="grid gap-4 xl:grid-cols-2">
        <Section
          title="Yapılanlar"
          hint={`${data.completed_todos.length} tamamlanan`}
          action={<Chip tone="ok">haftanın kazanımları</Chip>}
        >
          {data.completed_todos.length === 0 ? (
            <Empty>Bu dönemde tamamlanan görev görünmüyor.</Empty>
          ) : (
            <RowList as="ul">
              {data.completed_todos.map((todo, index) => (
                <li
                  key={`${todo.id ?? "deleted"}-${todo.completed_at}-${index}`}
                  className="flex items-center gap-3 py-2.5"
                >
                  <CheckCircle2 size={15} className="shrink-0 text-ok" />
                  <span className="min-w-0 flex-1 truncate text-body text-primary">{todo.title}</span>
                  <span className="text-meta text-muted">
                    {formatTrDateTime(todo.completed_at, { weekday: "short", hour: "2-digit", minute: "2-digit" })}
                  </span>
                </li>
              ))}
            </RowList>
          )}
        </Section>

        <Section
          title="Yapılmayanlar"
          hint={`${data.unfinished_todos.length} karar bekliyor`}
          action={<Chip tone={data.unfinished_todos.length ? "warn" : "ok"}>hafta sonu durumu</Chip>}
        >
          {data.unfinished_todos.length === 0 ? (
            <Empty>Açık görev kalmamış — temiz kapanış.</Empty>
          ) : (
            <RowList as="ul">
              {data.unfinished_todos.slice(0, 7).map((todo) => (
                <li key={todo.id} className="flex items-center gap-3 py-2.5">
                  <span className="h-2 w-2 shrink-0 rounded-full bg-warn" />
                  <span className="min-w-0 flex-1 truncate text-body text-primary">{todo.title}</span>
                  <Chip size="xs">p{todo.priority}</Chip>
                </li>
              ))}
              {data.unfinished_todos.length > 7 && (
                <li className="py-2 text-center text-meta text-muted">
                  +{data.unfinished_todos.length - 7} görev daha
                </li>
              )}
            </RowList>
          )}
        </Section>
      </div>

      <Section
        title="Gelen Kutusunu Temizle (Inbox Zero)"
        hint={inboxItems.length === 0 ? "Temiz" : `${inboxItems.length} bekleyen kayıt`}
        action={
          inboxItems.length > 0 ? (
            <Button size="sm" onClick={() => setTriageOpen(true)}>
              Triage Modunu Başlat
            </Button>
          ) : (
            <Chip tone="ok">Sıfırlandı</Chip>
          )
        }
      >
        {inboxItems.length === 0 ? (
          <Empty>Gelen kutusunda bekleyen kayıt yok. Zihniniz temiz.</Empty>
        ) : (
          <div className="space-y-3">
            <p className="text-body text-secondary">
              Dönemi net kapatmak için gelen kutusundaki {inboxItems.length} kaydı inceleyin, arşivleyin veya göreve
              dönüştürün.
            </p>
            <RowList as="ul">
              {inboxItems.slice(0, 4).map((bm) => (
                <li key={bm.id} className="flex items-center justify-between gap-3 py-1.5 text-meta">
                  <span className="truncate text-primary">{bm.title || bm.url}</span>
                  <span className="text-muted shrink-0">{hostOf(bm.url)}</span>
                </li>
              ))}
            </RowList>
            {inboxItems.length > 4 && <p className="text-meta text-muted">+{inboxItems.length - 4} kayıt daha</p>}
          </div>
        )}
      </Section>
      <InboxFocusTriageModal open={triageOpen} onClose={() => setTriageOpen(false)} />

      <div className="grid gap-4 xl:grid-cols-3">
        <Section title="Odak dağılımı" className="xl:col-span-2">
          {stats.topics.length === 0 ? (
            <Empty>Bu dönemde tamamlanan odak seansı yok.</Empty>
          ) : (
            <div className="space-y-3">
              {stats.topics.map((topic) => (
                <div key={topic.topic}>
                  <div className="mb-1.5 flex items-center gap-3 text-meta">
                    <span className="min-w-0 flex-1 truncate text-secondary">{topic.topic}</span>
                    <span className="numeral text-muted">{topic.minutes} dk</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-control bg-surface-sunken">
                    <span
                      className="block h-full rounded-control bg-accent"
                      style={{ width: `${Math.max(6, Math.round((topic.minutes / maxTopic) * 100))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <Section title="Haftanın ritmi">
          <div className="space-y-3">
            <Signal icon={<Sparkles size={15} />} label="Üretken gün" value={`${stats.focus.active_days} gün`} />
            <Signal icon={<Target size={15} />} label="En iyi gün" value={dayLabel(stats.focus.best_day)} />
            <Signal icon={<Clock3 size={15} />} label="O gün odak" value={`${stats.focus.best_day_minutes} dk`} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 border-t border-subtle pt-4">
            {signals.map(([label, value]) => (
              <div key={label} className="rounded-control bg-surface-sunken p-2.5">
                <p className="numeral text-heading text-primary">{value}</p>
                <p className="mt-0.5 text-micro text-muted">{label}</p>
              </div>
            ))}
          </div>
        </Section>
      </div>

      <div className="flex justify-end">
        <Button variant="primary" onClick={onNext}>
          Açık işleri değerlendir <ArrowRight size={14} />
        </Button>
      </div>
    </div>
  );
}

function Signal({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-accent-surface text-accent">
        {icon}
      </span>
      <span className="min-w-0 flex-1 text-meta text-secondary">{label}</span>
      <span className="numeral text-body text-primary">{value}</span>
    </div>
  );
}

function DecisionsStep({
  todos,
  decisions,
  waitingCount,
  onDecision,
  onCarryAll,
  onBack,
  onNext,
}: {
  todos: ReviewPreview["unfinished_todos"];
  decisions: Record<string, "carry" | "drop">;
  waitingCount: number;
  onDecision: (id: string, value: "carry" | "drop") => void;
  onCarryAll: () => void;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <Section
      title="Açık işleri kapat"
      hint={waitingCount > 0 ? `${waitingCount} görev karar bekliyor` : "Tüm kararlar hazır"}
      action={
        todos.length ? (
          <Button onClick={onCarryAll}>
            <RotateCcw size={13} /> Hepsini devret
          </Button>
        ) : undefined
      }
    >
      <p className="mb-4 max-w-3xl text-body text-secondary">
        Gerçekten devam edecek işleri yeni haftaya taşı; anlamını yitirenleri bırak. Kararsız bıraktıkların olduğu gibi
        kalır.
      </p>
      {todos.length === 0 ? (
        <Empty>Açık görev yok — doğrudan önceliklerini seçebilirsin.</Empty>
      ) : (
        <RowList as="ul">
          {todos.map((todo) => (
            <li key={todo.id} className="flex flex-wrap items-center gap-3 py-3">
              <div className="min-w-48 flex-1">
                <p className="text-body text-primary">{todo.title}</p>
                <p className="mt-0.5 text-meta text-muted">
                  {todo.due_at ? `Son tarih ${dayLabel(todo.due_at.slice(0, 10))}` : "Son tarih yok"}
                </p>
              </div>
              <Chip tone={todo.priority >= 3 ? "warn" : "neutral"}>p{todo.priority}</Chip>
              <div className="inline-flex rounded-control border border-subtle bg-surface-sunken p-0.5">
                <Button
                  size="sm"
                  variant={decisions[todo.id] === "carry" ? "primary" : "ghost"}
                  onClick={() => onDecision(todo.id, "carry")}
                >
                  Devret
                </Button>
                <Button
                  size="sm"
                  variant={decisions[todo.id] === "drop" ? "danger" : "ghost"}
                  onClick={() => onDecision(todo.id, "drop")}
                >
                  Bırak
                </Button>
              </div>
            </li>
          ))}
        </RowList>
      )}
      <div className="mt-5 flex items-center justify-between border-t border-subtle pt-4">
        <Button onClick={onBack}>
          <ArrowLeft size={14} /> Özete dön
        </Button>
        <Button variant="primary" onClick={onNext}>
          Öncelikleri seç <ArrowRight size={14} />
        </Button>
      </div>
    </Section>
  );
}

function PrioritiesStep({
  kind,
  priorities,
  onPriority,
  note,
  onNote,
  carried,
  dropped,
  focusMinutes,
  completed,
  online,
  pending,
  onBack,
  onSave,
}: {
  kind: "daily" | "weekly";
  priorities: string[];
  onPriority: (index: number, value: string) => void;
  note: string;
  onNote: (value: string) => void;
  carried: number;
  dropped: number;
  focusMinutes: number;
  completed: number;
  online: boolean;
  pending: boolean;
  onBack: () => void;
  onSave: () => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Section
        title={kind === "weekly" ? "Gelecek haftanın 3 önceliği" : "Yarının öncelikleri"}
        className="xl:col-span-2"
      >
        <p className="mb-4 text-body text-secondary">Haftayı yapılacaklar listesiyle değil, üç net sonuçla başlat.</p>
        <div className="space-y-3">
          {priorities.map((value, index) => (
            <div key={index} className="flex items-center gap-3">
              <span className="numeral flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-surface text-accent">
                {index + 1}
              </span>
              <Input
                value={value}
                onChange={(next) => onPriority(index, next)}
                placeholder={`${index + 1}. öncelik`}
                className="w-full"
              />
            </div>
          ))}
        </div>
        <div className="mt-5">
          <p className="mb-2 text-meta text-secondary">Haftaya not</p>
          <Textarea
            value={note}
            onChange={onNote}
            placeholder="Neyi sürdürmek, neyi değiştirmek istiyorsun?"
            className="min-h-28"
          />
        </div>
        <div className="mt-5 flex items-center justify-between border-t border-subtle pt-4">
          <Button onClick={onBack}>
            <ArrowLeft size={14} /> Kararlara dön
          </Button>
          <Button variant="primary" disabled={!online || pending} onClick={onSave}>
            <Check size={14} /> {pending ? "Kaydediliyor" : "Değerlendirmeyi tamamla"}
          </Button>
        </div>
      </Section>

      <Section title="Kapanış özeti">
        <div className="space-y-3">
          <RecapRow label="Tamamlanan" value={completed} tone="ok" />
          <RecapRow label="Yeni haftaya" value={carried} tone="accent" />
          <RecapRow label="Bırakılan" value={dropped} tone="neutral" />
          <RecapRow label="Odak" value={`${focusMinutes} dk`} tone="neutral" />
        </div>
        <p className="mt-5 border-t border-subtle pt-4 text-meta text-muted">
          Önceliklerin tamamlayınca görev olarak oluşturulur ve yeni dönemin ilk gününe planlanır.
        </p>
      </Section>
    </div>
  );
}

function RecapRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone: "ok" | "accent" | "neutral";
}) {
  return (
    <div className="flex items-center justify-between rounded-control bg-surface-sunken px-3 py-2.5">
      <span className="text-meta text-secondary">{label}</span>
      <Chip tone={tone}>{value}</Chip>
    </div>
  );
}

export function WeeklyReviewPage() {
  return <ReviewFlow kind="weekly" />;
}

export function DailyReviewPage() {
  return <ReviewFlow kind="daily" />;
}

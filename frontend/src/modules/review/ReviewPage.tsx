import { entityRoute } from "@/core/entityRegistry";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, CheckCircle2, ChevronLeft, ChevronRight, Clock3, Target } from "lucide-react";
import { invalidateAfter } from "@/core/invalidation";
import { ContextualHelp, ScheduleTasks } from "@/core/ContextualHelp";
import { readStored, writeStored } from "@/core/storage";
import { api, qs } from "@/core/api";
import {
  Button,
  Chip,
  CopyButton,
  Disclosure,
  Empty,
  Metric,
  MetricStrip,
  PageFrame,
  RowList,
  Section,
  SectionHeader,
  Select,
  Tabs,
  Textarea,
  cx,
  useToast,
} from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import type { ReviewPreview } from "@/core/types";
import { navigate, useHashRoute } from "@/app/router";
import { appWeekStartKey, formatTrDate, formatTrDateTime, localDateKey, todayKey } from "@/lib/date";
import { useOnline } from "@/lib/hooks";
import { buildReviewDigest } from "./reviewDigest";
import {
  careerGoalReviewRows,
  careerReviewRows,
  reviewChangeRows,
  reviewMetricRows,
  reviewSecondarySignals,
} from "./reviewMetrics";

/** Kayıtlı değerlendirme satırı. `stats` eski kayıtlarda eksik alan taşıyabilir. */
interface SavedReviewRow {
  id: string;
  kind: "daily" | "weekly" | "monthly" | "yearly";
  period_start: string;
  period_end: string;
  stats: unknown;
  note: string | null;
}

function shortDate(value: string): string {
  return formatTrDate(`${value}T12:00:00`, { day: "numeric", month: "short" });
}

function dayLabel(value?: string | null): string {
  if (!value) return "—";
  return formatTrDate(`${value}T12:00:00`, { weekday: "short", day: "numeric", month: "short" });
}

/**
 * Değerlendirme tek sayfadır: zorunlu sihirbaz, zorunlu öncelik ve her açık
 * göreve karar verme töreni YOKTUR. Açık işler yalnızca kullanıcı isterse
 * "gelişmiş" katmanında taşınır/bırakılır; seçilmeyenler Todo olarak kalır.
 */
type ReviewKind = SavedReviewRow["kind"];

function currentPeriod(kind: ReviewKind): string {
  const today = todayKey();
  if (kind === "weekly") return appWeekStartKey();
  if (kind === "monthly") return `${today.slice(0, 7)}-01`;
  if (kind === "yearly") return `${today.slice(0, 4)}-01-01`;
  return today;
}

function adjacentPeriod(kind: ReviewKind, period: string, delta: number): string {
  const date = new Date(`${period}T12:00:00Z`);
  if (kind === "yearly") date.setUTCFullYear(date.getUTCFullYear() + delta);
  else if (kind === "monthly") date.setUTCMonth(date.getUTCMonth() + delta);
  else date.setUTCDate(date.getUTCDate() + delta * (kind === "weekly" ? 7 : 1));
  return localDateKey(date);
}

function ReviewFlow({ kind }: { kind: ReviewKind }) {
  const { params } = useHashRoute();
  const [note, setNote] = useState("");
  const [decisions, setDecisions] = useState<Record<string, "carry" | "drop">>({});
  const [reminderDismissed, setReminderDismissed] = useState(
    () => readStored("review.reminder-discovery") === "dismissed",
  );
  const online = useOnline();
  const toast = useToast();
  const requested = params.get("period");
  const period = useMemo(
    () => (requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) ? requested : currentPeriod(kind)),
    [kind, requested],
  );
  const goPeriod = (next: string) => navigate(`/review/${kind}?period=${next}`);

  const { data, isLoading } = useQuery({
    queryKey: ["review-preview", kind, period],
    queryFn: () => api.get<ReviewPreview>(`/reviews/preview${qs({ kind, period_start: period })}`),
  });

  // Geçmiş kayıtlar iki işi birden görür: bu dönem kapandıysa kaydetme kapanır,
  // önceki dönem kaydı varsa "neler değişti" ondan hesaplanır.
  const { data: rawHistory = [] } = useQuery({
    queryKey: ["reviews", "history", kind],
    queryFn: () => api.get<SavedReviewRow[]>(`/reviews${qs({ kind, limit: 100 })}`),
  });
  const history = Array.isArray(rawHistory) ? rawHistory : [];
  const saved = history.find((row) => row.period_start === period) ?? null;
  const previous = history.find((row) => row.period_start < period) ?? null;
  useEffect(() => setNote(saved?.note ?? ""), [saved?.id, saved?.note]);

  const updateNote = useMutation({
    mutationFn: () => api.patch(`/reviews/${saved?.id}`, { note }),
    onSuccess: () => {
      invalidateAfter("review.write");
      toast.push("Not güncellendi.", { tone: "ok" });
    },
    onError: () => toast.push("Not güncellenemedi.", { tone: "danger" }),
  });

  const save = useMutation({
    mutationFn: () => {
      const carry = Object.entries(decisions)
        .filter(([, value]) => value === "carry")
        .map(([id]) => id);
      const drop = Object.entries(decisions)
        .filter(([, value]) => value === "drop")
        .map(([id]) => id);
      return api.post("/reviews", {
        kind,
        period_start: period,
        // Not opsiyoneldir: boş not gönderilmez.
        ...(note.trim() ? { note } : {}),
        // Karar vermek zorunlu değil: seçim yoksa `decisions` hiç gönderilmez.
        ...(carry.length || drop.length ? { decisions: { carry_over: carry, drop } } : {}),
      });
    },
    onSuccess: () => {
      invalidateAfter("review.write");
      toast.push("Değerlendirme kaydedildi.", { tone: "ok" });
    },
    onError: () => {
      // 409 bu dönemin zaten kaydedildiği anlamına gelir; ham sunucu metni
      // kullanıcıya gösterilmez.
      toast.push("Değerlendirme kaydedilemedi — bu dönem için kayıt olabilir.", { tone: "warn" });
    },
  });

  if (isLoading || !data) return <p className="p-6 text-body text-muted">Değerlendirme hesaplanıyor…</p>;

  // Kayıtlı dönemin sayıları snapshot'tan gelir; canlı preview onları değiştirmez.
  const stats = (saved?.stats ?? data.stats) as ReviewPreview["stats"];
  const snapshot = { ...data, stats };
  const open = saved && period !== currentPeriod(kind) ? [] : data.unfinished_todos;
  const inclusiveEnd = adjacentPeriod("daily", data.period_end, -1);
  const periodRange = `${shortDate(data.period_start)} → ${shortDate(inclusiveEnd)}`;
  const topics = [...stats.topics].sort((left, right) => right.minutes - left.minutes);
  const maxTopic = Math.max(...topics.map((topic) => topic.minutes), 1);
  const signals = reviewSecondarySignals(stats);
  const changes = previous ? reviewChangeRows(stats, previous.stats) : [];
  const digest = buildReviewDigest(snapshot, note);

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Değerlendirme"
          title={`${kind === "weekly" ? "Haftalık" : kind === "monthly" ? "Aylık" : kind === "yearly" ? "Yıllık" : "Günlük"} değerlendirme`}
          hint={periodRange}
          action={
            <div className="flex items-center gap-2">
              {saved && <Chip tone="ok">Kaydedildi</Chip>}
              <CopyButton
                text={digest}
                label="Agent için özeti kopyala"
                ariaLabel="Agent için değerlendirme özetini kopyala"
              />
            </div>
          }
        />
        <WorkspaceScrollArea className="p-3">
          <div className="stack-y-5">
            <div className="flex flex-wrap items-center gap-2 border-b border-subtle pb-3">
              <Tabs
                value={kind === "daily" ? "weekly" : kind}
                onChange={(value) => navigate(`/review/${value}`)}
                ariaLabel="Değerlendirme dönemi"
                items={[
                  { id: "weekly", label: "Haftalık" },
                  { id: "monthly", label: "Aylık" },
                  { id: "yearly", label: "Yıllık" },
                ]}
              />
              <Button
                size="sm"
                variant="ghost"
                title="Önceki dönem"
                onClick={() => goPeriod(adjacentPeriod(kind, period, -1))}
              >
                <ChevronLeft size={14} /> Önceki
              </Button>
              <Button
                size="sm"
                variant="ghost"
                title="Sonraki dönem"
                onClick={() => goPeriod(adjacentPeriod(kind, period, 1))}
              >
                Sonraki <ChevronRight size={14} />
              </Button>
              <Select
                value={history.some((row) => row.period_start === period) ? period : ""}
                onChange={goPeriod}
                ariaLabel="Değerlendirme geçmişi"
              >
                <option value="">Geçmiş kayıtlar</option>
                {history.map((row) => (
                  <option key={row.id} value={row.period_start}>
                    {shortDate(row.period_start)} · {row.note?.trim() || "Not yok"}
                  </option>
                ))}
              </Select>
            </div>
            <ContextualHelp
              key={`${kind}:${period}`}
              summaryInitiallyOpen={false}
              label="Yerel özeti aç"
              context={{ kind: "review", period_kind: kind, period_start: period, review_id: saved?.id ?? null }}
            />
            {kind === "weekly" && history.length >= 3 && !reminderDismissed && (
              <div className="flex flex-wrap items-center gap-2 text-meta text-secondary">
                <span>İstersen haftalık değerlendirmeyi sana hatırlatabilirim.</span>
                <Button
                  size="sm"
                  onClick={() => {
                    writeStored("review.reminder-discovery", "dismissed");
                    setReminderDismissed(true);
                    navigate("/settings?tab=brain");
                  }}
                >
                  Hatırlatma tercihleri
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    writeStored("review.reminder-discovery", "dismissed");
                    setReminderDismissed(true);
                  }}
                >
                  Şimdi değil
                </Button>
              </div>
            )}
            {/* 1. NE OLDU? */}
            <div className="stack-y-3">
              <SectionHeader label="1. Ne oldu?" hint="Dönem metrikleri ve tamamlanan işler" />
              <MetricStrip className="grid-cols-2 lg:grid-cols-4">
                {reviewMetricRows(snapshot).map((row) => (
                  <Metric key={row.label} label={row.label} value={row.value} hint={row.hint} href={row.href} />
                ))}
              </MetricStrip>

              <div className="grid gap-4 xl:grid-cols-2">
                <Section title="Tamamlanan işler" hint={`${data.completed_todos.length} kayıt`}>
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
                            {formatTrDateTime(todo.completed_at, {
                              weekday: "short",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </li>
                      ))}
                    </RowList>
                  )}
                </Section>

                <Section
                  title="Odak dağılımı"
                  hint={stats.focus.minutes ? `${stats.focus.minutes} dk odak` : undefined}
                >
                  <div className="stack-y-3">
                    <Signal icon={<Target size={15} />} label="En iyi gün" value={dayLabel(stats.focus.best_day)} />
                    <Signal
                      icon={<Clock3 size={15} />}
                      label="O gün odak"
                      value={`${stats.focus.best_day_minutes} dk`}
                    />
                  </div>
                  <div className="mt-4 border-t border-subtle pt-3">
                    {topics.length === 0 ? (
                      <p className="text-meta text-muted">Bu dönemde tamamlanan odak seansı yok.</p>
                    ) : (
                      <div className="stack-y-2.5">
                        {topics.slice(0, 5).map((topic) => (
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
                        {topics.length > 5 && <p className="text-meta text-muted">+{topics.length - 5} konu daha</p>}
                      </div>
                    )}
                  </div>
                  <Disclosure summary="Diğer sinyaller" className="mt-3 border-t border-subtle pt-3">
                    <div className="grid grid-cols-2 gap-2">
                      {signals.map((signal) => (
                        <div key={signal.label} className="rounded-control bg-surface-sunken p-2.5">
                          <p className="numeral text-heading text-primary">
                            {signal.value}
                            {signal.unit ? ` ${signal.unit}` : ""}
                          </p>
                          <p className="mt-0.5 text-micro text-muted">{signal.label}</p>
                        </div>
                      ))}
                    </div>
                  </Disclosure>
                </Section>
              </div>
            </div>

            {/* 2. BU NE ANLAMA GELİYOR? */}
            <div className="stack-y-3 border-t border-subtle pt-4">
              <SectionHeader label="2. Bu ne anlama geliyor?" hint="Hedefler, eğilimler ve önemli değişiklikler" />

              {stats.strategy_snapshot &&
                Array.isArray(stats.strategy_snapshot.objectives) &&
                stats.strategy_snapshot.objectives.length > 0 && (
                  <Section title="Hedeflerdeki durum">
                    <StrategySnapshotSummary snapshot={stats.strategy_snapshot} />
                  </Section>
                )}

              {kind === "weekly" && (
                <Section title="Kariyer ve fırsatlar">
                  <div className="flex flex-wrap gap-2">
                    {careerReviewRows(
                      stats,
                      previous?.period_start === adjacentPeriod("weekly", period, -1) ? previous.stats : null,
                    ).map(([label, count, change]) => (
                      <Chip key={label} tone="neutral">
                        {label}: {count}
                        {change ? ` · ${change}` : ""}
                      </Chip>
                    ))}
                  </div>
                  {(stats.career_goals ?? []).length > 0 && (
                    <div className="mt-3 stack-y-1 border-t border-subtle pt-3">
                      <p className="text-meta font-semibold text-primary">Hedef adımları (milestone)</p>
                      {careerGoalReviewRows(
                        stats,
                        previous?.period_start === adjacentPeriod("weekly", period, -1) ? previous.stats : null,
                      ).map((goal) => (
                        <p key={goal.id} className="text-meta text-secondary">
                          {goal.title}: {goal.progress}
                          {goal.change ? ` · ${goal.change}` : ""}
                        </p>
                      ))}
                    </div>
                  )}
                </Section>
              )}

              {previous && changes.length > 0 && (
                <Section title="Önceki döneme göre değişim" hint={`önceki kayıt: ${shortDate(previous.period_start)}`}>
                  <RowList as="ul">
                    {changes.map(([label, value]) => (
                      <li key={label} className="flex items-center justify-between gap-3 py-2">
                        <span className="text-body text-secondary">{label}</span>
                        <span className="numeral text-body text-primary">{value}</span>
                      </li>
                    ))}
                  </RowList>
                </Section>
              )}
            </div>

            {/* 3. SIRADA NE VAR? */}
            <div className="stack-y-3 border-t border-subtle pt-4">
              <SectionHeader label="3. Sırada ne var?" hint="Açık işler ve önümüzdeki dönemin kararları" />
            <Section
              title="Açık kalanlar"
              hint={open.length ? `${open.length} görev açık` : "Açık görev yok"}
              action={
                open.length ? (
                  <div className="flex flex-wrap gap-2">
                    <ScheduleTasks
                      tasks={open}
                      label={kind === "weekly" ? "Gelecek haftaya taşı" : "Sonraki güne planla"}
                      defaultDay={adjacentPeriod(
                        kind === "weekly" ? "weekly" : "daily",
                        kind === "weekly" ? appWeekStartKey() : todayKey(),
                        1,
                      )}
                    />
                    <Button size="sm" onClick={() => navigate("/todos")}>
                      Görevlere git <ArrowRight size={13} />
                    </Button>
                  </div>
                ) : undefined
              }
            >
              {open.length === 0 ? (
                <Empty>Açık görev kalmamış — temiz kapanış.</Empty>
              ) : (
                <div className="stack-y-3">
                  <p className="text-body text-secondary">
                    Açık görevler görev listende kalır; otomatik taşıma veya silme yapılmaz.
                  </p>
                  <p className="text-meta text-muted">
                    {open
                      .slice(0, 3)
                      .map((todo) => todo.title)
                      .join(" · ")}
                    {open.length > 3 ? ` · +${open.length - 3} görev daha` : ""}
                  </p>
                  {!saved && (
                    <Disclosure summary="Taşı veya bırak (gelişmiş)">
                      <p className="text-meta text-muted">
                        Yalnız değiştirmek istediklerini işaretle; seçmediklerin Todo olarak kalır.
                      </p>
                      <RowList as="ul">
                        {open.map((todo) => (
                          <li key={todo.id} className="flex flex-wrap items-center gap-3 py-2.5">
                            <div className="min-w-48 flex-1">
                              <p className="text-body text-primary">{todo.title}</p>
                              <p className="mt-0.5 text-meta text-muted">
                                {todo.due_at ? `Son tarih ${dayLabel(todo.due_at.slice(0, 10))}` : "Son tarih yok"}
                              </p>
                            </div>
                            <div className="inline-flex rounded-control border border-subtle bg-surface-sunken p-0.5">
                              <Button
                                size="sm"
                                variant={decisions[todo.id] === "carry" ? "primary" : "ghost"}
                                onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "carry" }))}
                              >
                                Devret
                              </Button>
                              <Button
                                size="sm"
                                variant={decisions[todo.id] === "drop" ? "danger" : "ghost"}
                                onClick={() => setDecisions((old) => ({ ...old, [todo.id]: "drop" }))}
                              >
                                Bırak
                              </Button>
                            </div>
                          </li>
                        ))}
                      </RowList>
                    </Disclosure>
                  )}
                </div>
              )}
            </Section>

            <Section title="Kendi notum" hint="opsiyonel">
              <Textarea
                value={note}
                onChange={setNote}
                placeholder="Dönem hakkında kısa bir not"
                className="min-h-24"
              />
              {saved && (
                <Button
                  size="sm"
                  disabled={!online || updateNote.isPending || note === (saved.note ?? "")}
                  onClick={() => updateNote.mutate()}
                >
                  Notu kaydet
                </Button>
              )}
            </Section>

            <div className="flex flex-wrap items-center justify-end gap-3">
              {saved ? (
                <Chip tone="ok">Bu dönemin değerlendirmesi kaydedildi</Chip>
              ) : (
                <>
                  {!online && (
                    <span className="text-meta text-muted">Çevrimdışısın — kaydetmek için bağlantı gerekir.</span>
                  )}
                  <Button variant="primary" disabled={!online || save.isPending} onClick={() => save.mutate()}>
                    <Check size={14} /> {save.isPending ? "Kaydediliyor" : "Değerlendirmeyi kaydet"}
                  </Button>
                </>
              )}
            </div>
          </div>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

function StrategySnapshotSummary({ snapshot }: { snapshot: Record<string, unknown> }) {
  const objectives = Array.isArray(snapshot.objectives) ? snapshot.objectives : [];
  if (!objectives.length) return <p className="text-meta text-muted">Bu kayıtta hedef ölçümü bulunmuyor.</p>;
  return (
    <ul className="mt-2 stack-y-2 text-body">
      {objectives.slice(0, 6).map((item, i) => {
        const objective = item as {
          goal?: { id?: string; title?: string };
          strategic_progress_percent?: number | null;
          confidence?: string;
          warnings?: unknown[];
        };
        return (
          <li key={objective.goal?.id ?? i}>
            {objective.goal?.id ? (
              <a className="text-accent underline" href={`#${entityRoute("goal", objective.goal.id)}`}>
                {objective.goal.title}
              </a>
            ) : (
              "Hedef"
            )}
            :{" "}
            {typeof objective.strategic_progress_percent === "number"
              ? `${objective.strategic_progress_percent}% kayıtlı sonuç ilerlemesi`
              : "Sonuç ölçümü bilinmiyor"}
            {objective.confidence === "low" ? " · Ölçüm eksikleri var" : ""}
          </li>
        );
      })}
    </ul>
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

export function WeeklyReviewPage() {
  return <ReviewFlow kind="weekly" />;
}

export function DailyReviewPage() {
  return <ReviewFlow kind="daily" />;
}

export function MonthlyReviewPage() {
  return <ReviewFlow kind="monthly" />;
}

export function YearlyReviewPage() {
  return <ReviewFlow kind="yearly" />;
}

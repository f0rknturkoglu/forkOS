import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Undo2 } from "lucide-react";
import { invalidateAfter } from "@/core/invalidation";
import { ProactivitySnoozeButton } from "@/core/ProactivitySnooze";
import {
  PROACTIVITY_HISTORY_KEY,
  PROACTIVITY_RULES_KEY,
  PROACTIVITY_STATUS_KEY,
  proactivityHistory,
  proactivityRules,
  proactivityStatus,
  saveProactivityConfig,
  saveProactivityRule,
  snoozeProactivityRule,
  snoozeUntil,
  unsnoozeProactivityRun,
} from "@/core/proactivity";
import type { ProactivityConfigPatch, ProactivityRule, ProactivityRun } from "@/core/proactivity";
import {
  Button,
  Checkbox,
  Chip,
  Disclosure,
  Field,
  IconButton,
  Input,
  Metric,
  MetricStrip,
  NumberInput,
  Section,
  Select,
  Spinner,
  relativeTime,
  useToast,
} from "@/core/ui";

/**
 * H6 kontrol bolumu: ana anahtar, sessiz saatler, kapali kural kumesi,
 * durum ozeti ve son kosular.
 *
 * Bolum H6'nin KENDI durumunu yonetir; hicbir canonical kaydi degistirmez.
 * Kurallar kapali bir kumedir: burada serbest kural yazilmaz, yalnizca var
 * olan kuralin ac/kapa ve esik ayari yapilir.
 */

/** Kapali kural kumesi -> insan dili (backend `models.RULE_KINDS`). */
const RULE_LABELS: Record<string, string> = {
  morning_continuity: "Sabah sürekliliği",
  daily_close: "Gün kapanışı",
  weekly_review: "Haftalık gözden geçirme",
  deadline_staircase: "Son tarih basamakları",
  continuity_gap: "Sessizlik sonrası dönüş",
  project_stalled: "Durmuş projeler",
  strategy_attention: "Stratejik dikkat (isteğe bağlı)",
};

/** Kural varsayilan saatleri (backend `service.RULE_DEFAULTS`). */
const DEFAULT_TIME: Record<string, string> = {
  morning_continuity: "08:05",
  daily_close: "21:00",
  weekly_review: "18:00",
};

/** Kosu durumu -> insan dili (backend `models.RUN_STATES`). */
const STATE_LABELS: Record<string, string> = {
  candidate: "aday",
  deferred: "ertelendi",
  digest_queued: "özet kuyruğunda",
  snoozed: "susturuldu",
  delivered: "teslim edildi",
  suppressed: "bastırıldı",
  resolved: "kapandı",
  cancelled: "iptal edildi",
  dismissed: "yok sayıldı",
  failed: "hata",
};

const STATE_TONES: Record<string, "neutral" | "accent" | "ok" | "warn" | "danger"> = {
  candidate: "accent",
  digest_queued: "accent",
  deferred: "warn",
  snoozed: "warn",
  delivered: "ok",
  failed: "danger",
};

/** Python `weekday()` sirasi: 0 = Pazartesi .. 6 = Pazar. */
/** Gecmis listesinde once gosterilen satir sayisi; kalani katlanir. */
const VISIBLE_RUNS = 5;

const WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

/** Gelecek bir an: `relativeTime` gecmis icin yazildigi icin ayri bicim. */
function untilLabel(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Kural ayarindan pozitif sayi oku; alan yoksa varsayilan. */
function configNumber(rule: ProactivityRule, key: string, fallback: number): number {
  const raw = Number(rule.config[key]);
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

/** Kural ayarindan saat oku (`HH:MM`). */
function configTime(rule: ProactivityRule, fallback: string): string {
  const raw = rule.config["time"];
  return typeof raw === "string" ? raw : fallback;
}

export function ProactivitySection({ online }: { online: boolean }) {
  const toast = useToast();
  /** Alan taslaklari: sunucu degeri yetisene kadar yazilan sey kaybolmasin. */
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [numbers, setNumbers] = useState<Record<string, number>>({});

  const statusQuery = useQuery({
    queryKey: [PROACTIVITY_STATUS_KEY],
    queryFn: proactivityStatus,
    refetchInterval: 60_000,
  });
  const rulesQuery = useQuery({ queryKey: [PROACTIVITY_RULES_KEY], queryFn: proactivityRules });
  const historyQuery = useQuery({
    queryKey: [PROACTIVITY_HISTORY_KEY],
    queryFn: proactivityHistory,
    refetchInterval: 60_000,
  });

  const configMutation = useMutation({
    mutationFn: saveProactivityConfig,
    onSuccess: () => invalidateAfter("settings.write"),
  });
  const ruleMutation = useMutation({
    mutationFn: (input: { kind: string; patch: { enabled?: boolean; config?: Record<string, unknown> } }) =>
      saveProactivityRule(input.kind, input.patch),
    onSuccess: () => invalidateAfter("settings.write"),
  });
  const ruleSnooze = useMutation({
    mutationFn: (kind: string) => snoozeProactivityRule(kind, snoozeUntil("week")),
    onSuccess: () => {
      invalidateAfter("settings.write");
      toast.push("Kural bir hafta susturuldu — süre bitince kendiliğinden döner.", { tone: "ok" });
    },
  });
  const unsnooze = useMutation({
    mutationFn: unsnoozeProactivityRun,
    onSuccess: () => {
      invalidateAfter("settings.write");
      toast.push("Erteleme kaldırıldı — koşu yeniden değerlendirilir.", { tone: "ok" });
    },
  });

  /** Taslak temizleme: kaydedilen alan artik sunucudan okunur. */
  function commitDraft(key: string) {
    setDrafts((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  /** Konfig saat alani: yalniz DEGISEN deger yazilir. */
  function saveConfigTime(key: string, server: string, next: string, patch: (value: string) => ProactivityConfigPatch) {
    commitDraft(key);
    if (next && next !== server) configMutation.mutate(patch(next));
  }

  /** Kural saati: yalniz DEGISEN deger yazilir. */
  function saveRuleTime(rule: ProactivityRule, fallback: string, next: string) {
    commitDraft(`${rule.kind}:time`);
    if (next && next !== configTime(rule, fallback)) {
      ruleMutation.mutate({ kind: rule.kind, patch: { config: { time: next } } });
    }
  }

  /** Sayisal kural alani: yalniz DEGISEN deger yazilir. */
  function saveRuleNumber(rule: ProactivityRule, field: string, fallback: number) {
    const key = `${rule.kind}:${field}`;
    const next = numbers[key];
    setNumbers((current) => {
      const rest = { ...current };
      delete rest[key];
      return rest;
    });
    if (next !== undefined && next !== configNumber(rule, field, fallback)) {
      ruleMutation.mutate({ kind: rule.kind, patch: { config: { [field]: next } } });
    }
  }

  const status = statusQuery.data;
  if (!status) {
    return (
      <Section title="Proaktivite">
        <Spinner label="Proaktivite durumu yükleniyor…" />
      </Section>
    );
  }

  const busy = !online;
  const rules = Array.isArray(rulesQuery.data) ? rulesQuery.data : [];
  const runs = Array.isArray(historyQuery.data) ? historyQuery.data : [];
  const failures = status.recent_failures ?? [];
  const heartbeat = status.worker_heartbeat?.at;

  return (
    <Section title="Proaktivite" hint={status.enabled ? "açık" : "kapalı"}>
      <p className="mb-3 text-meta text-muted">
        forkOS yalnızca açtığın kurallar çerçevesinde kendiliğinden devreye girer ve varsayılan olarak kapalıdır. Uygun
        an yoksa hiçbir bildirim çıkmaz: sessiz kalmak başarısızlık değildir.
      </p>

      <div className="stack-y-3">
        <Checkbox
          checked={status.enabled}
          disabled={busy}
          onChange={(next) => configMutation.mutate({ enabled: next })}
          label="Proaktif müdahale açık"
        />

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Sessiz saat başlangıcı">
            <Input
              type="time"
              className="w-full"
              ariaLabel="Sessiz saat başlangıcı"
              disabled={busy}
              value={drafts["quiet_start"] ?? status.quiet_hours_start}
              onChange={(next) => setDrafts((current) => ({ ...current, quiet_start: next }))}
              onBlur={(next) =>
                saveConfigTime("quiet_start", status.quiet_hours_start, next, (value) => ({
                  quiet_hours_start: value,
                }))
              }
            />
          </Field>
          <Field label="Sessiz saat bitişi">
            <Input
              type="time"
              className="w-full"
              ariaLabel="Sessiz saat bitişi"
              disabled={busy}
              value={drafts["quiet_end"] ?? status.quiet_hours_end}
              onChange={(next) => setDrafts((current) => ({ ...current, quiet_end: next }))}
              onBlur={(next) =>
                saveConfigTime("quiet_end", status.quiet_hours_end, next, (value) => ({ quiet_hours_end: value }))
              }
            />
          </Field>
          <Field label="Günlük özet saati">
            <Input
              type="time"
              className="w-full"
              ariaLabel="Günlük özet saati"
              disabled={busy}
              value={drafts["digest_time"] ?? status.digest_time}
              onChange={(next) => setDrafts((current) => ({ ...current, digest_time: next }))}
              onBlur={(next) =>
                saveConfigTime("digest_time", status.digest_time, next, (value) => ({ digest_time: value }))
              }
            />
          </Field>
        </div>

        <Checkbox
          checked={status.focus_deferral_enabled}
          disabled={busy}
          onChange={(next) => configMutation.mutate({ focus_deferral_enabled: next })}
          label="Odak oturumu sürerken dürtme (bugün/yarın biten son tarihler hariç)"
        />

        <div className="stack-y-2">
          {rules.map((rule) => (
            <div key={rule.kind} className="rounded-control border border-subtle p-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Checkbox
                  checked={rule.enabled}
                  disabled={busy}
                  onChange={(next) => ruleMutation.mutate({ kind: rule.kind, patch: { enabled: next } })}
                  label={RULE_LABELS[rule.kind] ?? rule.kind}
                />
                <span className="flex items-center gap-2">
                  {rule.snoozed_until && (
                    <Chip tone="warn">{untilLabel(rule.snoozed_until)}&apos;a kadar susturuldu</Chip>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy || Boolean(rule.snoozed_until) || ruleSnooze.isPending}
                    onClick={() => ruleSnooze.mutate(rule.kind)}
                  >
                    Bu hafta dürtme
                  </Button>
                </span>
              </div>

              {rule.kind === "morning_continuity" || rule.kind === "daily_close" || rule.kind === "weekly_review" ? (
                <div className="mt-2 flex flex-wrap items-end gap-3">
                  <Field label="Saat" className="w-28">
                    <Input
                      type="time"
                      className="w-full"
                      ariaLabel={`${RULE_LABELS[rule.kind] ?? rule.kind} saati`}
                      disabled={busy}
                      value={drafts[`${rule.kind}:time`] ?? configTime(rule, DEFAULT_TIME[rule.kind] ?? "08:00")}
                      onChange={(next) => setDrafts((current) => ({ ...current, [`${rule.kind}:time`]: next }))}
                      onBlur={(next) => saveRuleTime(rule, DEFAULT_TIME[rule.kind] ?? "08:00", next)}
                    />
                  </Field>
                  {rule.kind === "weekly_review" && (
                    <Field label="Gün" className="w-36">
                      <Select
                        className="w-full"
                        ariaLabel="Haftalık gözden geçirme günü"
                        disabled={busy}
                        value={String(rule.config["weekday"] ?? 6)}
                        onChange={(next) =>
                          ruleMutation.mutate({ kind: rule.kind, patch: { config: { weekday: Number(next) } } })
                        }
                      >
                        {WEEKDAYS.map((label, index) => (
                          <option key={label} value={index}>
                            {label}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  )}
                </div>
              ) : null}

              {rule.kind === "continuity_gap" && (
                <Field label="Sessizlik eşiği (saat)" className="mt-2 w-40">
                  <div onBlur={() => saveRuleNumber(rule, "threshold_hours", 48)}>
                    <NumberInput
                      className="w-full"
                      min={1}
                      max={720}
                      ariaLabel="Sessizlik eşiği (saat)"
                      disabled={busy}
                      value={numbers[`${rule.kind}:threshold_hours`] ?? configNumber(rule, "threshold_hours", 48)}
                      onChange={(next) =>
                        setNumbers((current) => ({ ...current, [`${rule.kind}:threshold_hours`]: next }))
                      }
                    />
                  </div>
                </Field>
              )}

              {rule.kind === "project_stalled" && (
                <div className="mt-2 flex flex-wrap gap-3">
                  <Field label="Hareketsizlik (gün)" className="w-40">
                    <div onBlur={() => saveRuleNumber(rule, "days", 14)}>
                      <NumberInput
                        className="w-full"
                        min={1}
                        max={365}
                        ariaLabel="Hareketsizlik (gün)"
                        disabled={busy}
                        value={numbers[`${rule.kind}:days`] ?? configNumber(rule, "days", 14)}
                        onChange={(next) => setNumbers((current) => ({ ...current, [`${rule.kind}:days`]: next }))}
                      />
                    </div>
                  </Field>
                  <Field label="Tekrar bekleme (gün)" className="w-40">
                    <div onBlur={() => saveRuleNumber(rule, "cooldown_days", 7)}>
                      <NumberInput
                        className="w-full"
                        min={1}
                        max={90}
                        ariaLabel="Tekrar bekleme (gün)"
                        disabled={busy}
                        value={numbers[`${rule.kind}:cooldown_days`] ?? configNumber(rule, "cooldown_days", 7)}
                        onChange={(next) =>
                          setNumbers((current) => ({ ...current, [`${rule.kind}:cooldown_days`]: next }))
                        }
                      />
                    </div>
                  </Field>
                </div>
              )}
            </div>
          ))}
        </div>

        <MetricStrip className="grid-cols-3">
          <Metric label="bekleyen erteleme" value={status.pending_deferred} hint="koşu" />
          <Metric label="özet kuyruğu" value={status.pending_digest} hint="koşu" />
          <Metric
            label="bugün anlık yüzey"
            value={`${status.immediate_surfaces_today}/${status.immediate_budget}`}
            hint="günlük bütçe"
          />
        </MetricStrip>
        <p className="text-meta text-muted">
          worker: {heartbeat ? relativeTime(heartbeat) : "kalp atışı yok"} · son koşu:{" "}
          {status.last_run_at ? relativeTime(status.last_run_at) : "—"} · bütçe dolduğunda aday kaybolmaz, özete düşer.
        </p>

        <div>
          <p className="mb-1.5 text-meta text-secondary">Son koşular</p>
          {runs.length === 0 ? (
            <p className="text-meta text-muted">
              Koşu yok. Sessiz geçen tur satır bırakmaz: yalnız gerçekten değerlendirilecek bir şey bulunduğunda koşu
              oluşur.
            </p>
          ) : (
            <div className="stack-y-2">
              <ul className="stack-divide-y divide-subtle">
                {runsList(runs.slice(0, VISIBLE_RUNS), busy, (id) => unsnooze.mutate(id), unsnooze.isPending)}
              </ul>
              {runs.length > VISIBLE_RUNS && (
                <Disclosure summary={`Tüm koşular (${runs.length})`}>
                  <ul className="stack-divide-y divide-subtle">
                    {runsList(runs.slice(VISIBLE_RUNS), busy, (id) => unsnooze.mutate(id), unsnooze.isPending)}
                  </ul>
                </Disclosure>
              )}
            </div>
          )}
          <p className="mt-1 text-meta text-muted">
            Koşular en fazla 90 gün tutulur; erteleme geri alınabilir, koşu silinmez.
          </p>
        </div>

        {failures.length > 0 && (
          <div className="rounded-control border border-warn-border bg-warn-surface p-2.5">
            <p className="mb-1 text-meta font-medium text-warn">Son kural hataları</p>
            <ul className="stack-y-0.5">
              {failures.map((failure) => (
                <li key={`${failure.rule_kind}-${failure.at}`} className="text-micro text-warn">
                  {failure.rule_kind ? (RULE_LABELS[failure.rule_kind] ?? failure.rule_kind) : "kural yok"} ·{" "}
                  {failure.failure_code ?? "hata"} · {relativeTime(failure.at)}
                </li>
              ))}
            </ul>
            <p className="mt-1 text-micro text-muted">Bir kural hata verirse diğerleri etkilenmez.</p>
          </div>
        )}
      </div>
    </Section>
  );
}

/**
 * Kosu satirlari. Iki liste ayni satiri cizer (ilk N + "tum kosular"),
 * bu yuzden JSX TEK yerde durur.
 */
function runsList(items: ProactivityRun[], busy: boolean, onUnsnooze: (runId: number) => void, pending: boolean) {
  return items.map((run) => (
    <li key={run.id} className="flex flex-wrap items-start gap-2 py-2">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-meta text-primary">
            {run.rule_kind ? (RULE_LABELS[run.rule_kind] ?? run.rule_kind) : "kural silinmiş"}
          </span>
          <Chip tone={STATE_TONES[run.state] ?? "neutral"}>{STATE_LABELS[run.state] ?? run.state}</Chip>
          {run.snoozed_until && <Chip tone="warn">{untilLabel(run.snoozed_until)}</Chip>}
        </div>
        {run.why_now && <p className="mt-0.5 text-meta text-muted">{run.why_now}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <span className="text-micro text-muted">{relativeTime(run.triggered_at)}</span>
        {run.snoozed_until ? (
          <IconButton title="Ertelemeyi kaldır" disabled={busy || pending} onClick={() => onUnsnooze(run.id)}>
            <Undo2 size={14} />
          </IconButton>
        ) : (
          <ProactivitySnoozeButton
            runId={run.id}
            title="Bu koşuyu ertele"
            headline={
              run.why_now ?? (run.rule_kind ? (RULE_LABELS[run.rule_kind] ?? run.rule_kind) : "proaktivite koşusu")
            }
          />
        )}
      </div>
    </li>
  ));
}

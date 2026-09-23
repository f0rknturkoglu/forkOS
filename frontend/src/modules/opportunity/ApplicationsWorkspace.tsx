/**
 * Başvurular çalışma alanı (Faz 4.1) — YALNIZCA gerçek başvuru kayıtları
 * (`GET /applications`). Keşfedilmiş ilanlar bu ekrana hiçbir koşulda girmez;
 * payda her blokta açıkça yazılır.
 *
 * CRM hattı `application.status`'tadır (`opportunity.status` değil). İzinli
 * geçişler elle tanımlanmaz: satırın `allowed_application_transitions` alanı
 * backend state machine'inden gelir. Kanban kovaları ise
 * `GET /opportunities/lifecycle` cevabından türetilir.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarClock, Radar } from "lucide-react";
import { api, qs } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import {
  Button,
  Chip,
  Empty,
  Metric,
  MetricStrip,
  Section,
  Select,
  SkeletonRows,
  Spinner,
  Tabs,
  relativeTime,
  useToast,
} from "@/core/ui";
import { formatTrDate } from "@/lib/date";
import type {
  ApplicationFunnel,
  Document,
  Followup,
  FunnelBreakdownRow,
  FunnelVolumeRow,
  Opportunity,
  ApplicationListPage,
  OpportunityLifecycle,
  SilentApplication,
} from "@/core/types";
import { APPLICATION_STATUS_TONES, applicationStatusLabel } from "./labels";

/** Kanban sütunu. Durum kümesi lifecycle'dan gelir, elle yazılmaz. */
interface ApplicationColumn {
  key: string;
  title: string;
  statuses: string[];
}

/**
 * Kanban sütunlarını lifecycle'dan türetir. Bir durum, izinli geçişleri
 * arasında kendisinden DAHA İLERİ bir adım bulunmuyorsa kapanmıştır
 * (accepted/rejected/closed + yeniden açılabilen withdrawn "Sonuçlandı"ya
 * girer). Durum adları burada elle yazılmaz. Backend uçmuyorsa boş döner.
 */
function applicationColumns(lifecycle: OpportunityLifecycle | undefined): ApplicationColumn[] {
  if (!lifecycle) return [];
  const { flow, transitions } = lifecycle.application;
  const order = new Map(flow.map((status, index) => [status, index]));
  const isConcluded = (status: string) => {
    const position = order.get(status) ?? -1;
    return (transitions[status] ?? []).every((next) => (order.get(next) ?? -1) <= position);
  };
  const columns: ApplicationColumn[] = flow
    .filter((status) => !isConcluded(status))
    .map((status) => ({ key: status, title: applicationStatusLabel(status), statuses: [status] }));
  const concludedStatuses = flow.filter(isConcluded);
  if (concludedStatuses.length > 0) {
    columns.push({ key: "concluded", title: "Sonuçlandı", statuses: concludedStatuses });
  }
  return columns;
}

/** Oran etiketi: null oran "—" olur; asla yanıltıcı %0 yazılmaz. */
/**
 * Oran etiketi. Küçük örneklemde yüzde yanıltıcıdır (1 kayıttan "%100"):
 * eşiğin altında yüzde yerine ham sayı gösterilir.
 */
function rateLabel(rate: number | null | undefined, counted: number, sample: number, minimum: number): string {
  if (rate === null || rate === undefined || sample === 0) return "—";
  return sample < minimum ? `${counted}/${sample}` : `%${rate}`;
}

/** Kohort dönüşümü: pay/payda ham sayıları ve yüzdesi. */
function CohortRow({
  label,
  reached,
  base,
  minimum,
}: {
  label: string;
  reached: number;
  base: number;
  minimum: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="min-w-0 flex-1 truncate text-meta text-secondary">{label}</span>
      <span className="shrink-0 text-meta tabular-nums text-muted">
        {reached}/{base}
      </span>
      <span className="w-12 shrink-0 text-right text-meta tabular-nums text-primary">
        {rateLabel(base ? Math.round((reached / base) * 1000) / 10 : null, reached, base, minimum)}
      </span>
    </div>
  );
}

const VIEW_TABS = [
  { id: "list", label: "Liste" },
  { id: "kanban", label: "Kanban" },
];

type ApplicationsView = "list" | "kanban";

interface ApplicationsWorkspaceProps {
  online: boolean;
  onOpen: (id: string) => void;
}

function statusOf(item: Opportunity): string {
  return item.application_status ?? item.status;
}

/** Sorgu hatasında boş-liste yerine gösterilen rol=alert bloğu. */
function QueryFailure({ message, onRetry, retrying }: { message: string; onRetry: () => void; retrying?: boolean }) {
  return (
    <div role="alert" className="space-y-2 rounded-control border border-danger-border bg-danger-surface px-3 py-3">
      <p className="text-meta text-danger">{message}</p>
      <Button size="sm" disabled={retrying} onClick={onRetry}>
        Tekrar dene
      </Button>
    </div>
  );
}

/** Kullanıcının sıradaki adımı; mevcut alanlardan türetilir, yeni istek atmaz. */
interface NextAction {
  key: "document" | "send" | "followup" | "prepare";
  label: string;
  hint: string;
}

/**
 * Sıradaki adım önceliği: belge tamamla → başvuruyu gönder → takip et →
 * görüşmeye hazırlan. Kapanmış kayıtta (izinli geçiş yok) adım üretilmez.
 */
function applicationNextAction(item: Opportunity): NextAction | null {
  const status = statusOf(item);
  if ((item.allowed_application_transitions ?? []).length === 0) return null;
  if (status === "preparing") {
    if (!item.cv_document_id) return { key: "document", label: "Belge tamamla", hint: "CV seç" };
    const missing = (item.evaluation?.matches ?? []).find((entry) => entry.match === "missing");
    if (missing) return { key: "document", label: "Belge tamamla", hint: `Eksik gereksinim: ${missing.requirement}` };
    return { key: "send", label: "Başvuru gönder", hint: "Başvuruldu'ya taşı" };
  }
  if (item.follow_up_at) return { key: "followup", label: "Takip et", hint: formatTrDate(item.follow_up_at) };
  if (status === "interview") return { key: "prepare", label: "Görüşmeye hazırlan", hint: "Mülakat hazırlığı" };
  return null;
}

function TransitionSelect({
  item,
  online,
  pending,
  onTransition,
}: {
  item: Opportunity;
  online: boolean;
  pending: boolean;
  onTransition: (id: string, to: string) => void;
}) {
  const current = statusOf(item);
  const options = item.allowed_application_transitions ?? [];
  return (
    <Select
      value={current}
      disabled={!online || pending || options.length === 0}
      ariaLabel={`${item.title} başvuru durumunu değiştir`}
      onChange={(next) => onTransition(item.id, next)}
      className="w-36"
    >
      <option value={current}>{applicationStatusLabel(current)}</option>
      {options.map((status) => (
        <option key={status} value={status}>
          {applicationStatusLabel(status)}
        </option>
      ))}
    </Select>
  );
}

function StatusChip({ status }: { status: string }) {
  return <Chip tone={APPLICATION_STATUS_TONES[status] ?? "neutral"}>{applicationStatusLabel(status)}</Chip>;
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <span className="min-w-16 shrink-0">
      <span className="block text-micro text-muted">{label}</span>
      <span className="block truncate text-meta text-secondary">{value}</span>
    </span>
  );
}

function BreakdownTable({
  title,
  rows,
  hint,
  labelFor,
  minimumSample,
}: {
  title: string;
  rows: FunnelBreakdownRow[];
  hint: string;
  /** Ham anahtarı okunabilir etikete çevirir (kaynak kimlikleri gibi). */
  labelFor?: (row: FunnelBreakdownRow) => string;
  /** Bu sayının altında yüzde yerine ham sayı gösterilir. */
  minimumSample: number;
}) {
  const shown = rows.slice(0, 6);
  return (
    <Section title={title} hint={hint} flat bodyClassName="pt-0">
      {shown.length === 0 ? (
        <Empty>Veri yok.</Empty>
      ) : (
        <div className="divide-y divide-subtle">
          {shown.map((row) => {
            const label = labelFor ? labelFor(row) : row.label;
            return (
              <div key={row.key} className="flex items-center gap-2 py-1.5">
                <span className="min-w-0 flex-1 truncate text-meta text-secondary" title={label}>
                  {label}
                </span>
                <span className="w-10 shrink-0 text-right text-meta tabular-nums text-muted">{row.total}</span>
                <span className="w-14 shrink-0 text-right text-meta tabular-nums text-secondary">
                  {rateLabel(row.response_rate, row.responded, row.total, minimumSample)}
                </span>
                <span className="w-14 shrink-0 text-right text-meta tabular-nums text-secondary">
                  {rateLabel(row.interview_rate, row.interviewed, row.total, minimumSample)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Section>
  );
}

function VolumeBars({ rows }: { rows: FunnelVolumeRow[] }) {
  const max = Math.max(1, ...rows.map((row) => row.applied));
  if (rows.length === 0) return <Empty>Veri yok.</Empty>;
  return (
    <div className="space-y-1.5">
      {rows.map((row) => (
        <div key={row.period} className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-meta tabular-nums text-muted">{row.period}</span>
          <div className="h-3 min-w-0 flex-1 overflow-hidden rounded-control bg-surface-sunken">
            <div className="h-full rounded-control bg-accent" style={{ width: `${(row.applied / max) * 100}%` }} />
          </div>
          <span className="w-8 shrink-0 text-right text-meta tabular-nums text-secondary">{row.applied}</span>
        </div>
      ))}
    </div>
  );
}

function RecordLink({
  title,
  subtitle,
  meta,
  onOpen,
}: {
  title: string;
  subtitle: string;
  meta: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex w-full items-center gap-2 rounded-control border border-subtle bg-surface px-3 py-2 text-left transition hover:border-strong hover:bg-surface-hover"
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate text-body font-medium text-primary">{title}</span>
        <span className="block truncate text-micro text-muted">{subtitle}</span>
      </span>
      <span className="shrink-0 text-micro text-muted">{meta}</span>
      <ArrowRight size={13} className="shrink-0 text-muted transition group-hover:translate-x-0.5" />
    </button>
  );
}

export function ApplicationsWorkspace({ online, onOpen }: ApplicationsWorkspaceProps) {
  const [view, setView] = useState<ApplicationsView>("list");
  const [mode, setMode] = useState<"pipeline" | "followup" | "stats">("pipeline");
  const toast = useToast();

  const applications = useQuery({
    queryKey: ["opportunities", "applications", "list"],
    queryFn: () => api.get<ApplicationListPage>(`/applications${qs({ limit: 500 })}`),
  });
  const lifecycle = useQuery({
    queryKey: ["opportunity-lifecycle"],
    queryFn: () => api.get<OpportunityLifecycle>("/opportunities/lifecycle"),
  });
  const funnel = useQuery({
    queryKey: ["applications-funnel"],
    queryFn: () => api.get<ApplicationFunnel>("/applications/funnel"),
  });
  const followups = useQuery({
    queryKey: ["followups"],
    queryFn: () => api.get<Followup[]>("/opportunities/followups"),
  });
  const silence = useQuery({
    queryKey: ["opportunities", "silence", 21],
    queryFn: () => api.get<SilentApplication[]>("/opportunities/silence?days=21"),
  });
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });
  const rejectionReasons = useQuery({
    queryKey: ["opportunities", "applications", "rejection-reasons"],
    queryFn: () => api.get<string[]>("/applications/rejection-reasons"),
  });

  const transition = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) => api.post(`/applications/${id}/transition`, { to }),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      toast.push("Başvuru durumu güncellendi", { tone: "ok" });
    },
  });

  const rows = applications.data?.items ?? [];
  const applicationsTotal = applications.data?.total ?? rows.length;
  const funnelData = funnel.data;
  const cvTitles = useMemo(() => new Map((documents.data ?? []).map((doc) => [doc.id, doc.title])), [documents.data]);
  const columns = useMemo(() => applicationColumns(lifecycle.data), [lifecycle.data]);
  const reasonRows = useMemo(() => {
    const counts = new Map((funnelData?.rejection_reasons ?? []).map((row) => [row.reason, row.count]));
    const canonical = rejectionReasons.data ?? [];
    const rowsInOrder = canonical.map((reason) => ({ reason, count: counts.get(reason) ?? 0 }));
    const extra = (funnelData?.rejection_reasons ?? []).filter((row) => !canonical.includes(row.reason));
    return [...rowsInOrder, ...extra];
  }, [funnelData, rejectionReasons.data]);

  const changeStatus = (id: string, to: string) => transition.mutate({ id, to });

  const maxStatusCount = Math.max(1, ...(funnelData?.by_status ?? []).map((row) => row.count));
  const minimumSample = funnelData?.min_cohort_size ?? 10;
  const cohort = funnelData?.cohort ?? {};
  // Grafikler küçük örneklemde yanıltıcı: eşiğin altında bölümler gizlenir.
  const sparse = applicationsTotal < 3;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Tabs
          value={mode}
          onChange={setMode}
          items={[
            { id: "pipeline", label: "Pipeline" },
            { id: "followup", label: "Takip" },
            { id: "stats", label: "İstatistik" },
          ]}
          ariaLabel="Başvuru alanı"
        />
        {mode === "pipeline" && (
          <Tabs value={view} onChange={setView} items={VIEW_TABS} ariaLabel="Pipeline görünümü" />
        )}
        <span className="flex-1" />
        <span className="text-meta text-muted">
          Payda: yalnızca gerçek başvurular · {applicationsTotal} kayıt
          {applicationsTotal > rows.length ? ` (${rows.length} tanesi gösteriliyor)` : ""}
        </span>
      </div>

      {!online && (
        <p role="status" className="text-meta text-warn">
          Çevrimdışısın: başvuru durumu değiştirilemez, geçiş kontrolleri kapalı.
        </p>
      )}

      {mode === "pipeline" && view === "list" && (
        <Section
          title="Başvuru listesi"
          hint={
            applications.isLoading
              ? "Yükleniyor…"
              : applications.isError
                ? "okunamadı"
                : `${applicationsTotal} kayıt · payda: yalnızca gerçek başvurular`
          }
        >
          {applications.isLoading ? (
            <SkeletonRows rows={5} />
          ) : applications.isError ? (
            <QueryFailure
              message={`Başvurular yüklenemedi: ${
                applications.error instanceof Error ? applications.error.message : "bilinmeyen hata"
              }`}
              retrying={applications.isFetching}
              onRetry={() => void applications.refetch()}
            />
          ) : rows.length === 0 ? (
            <Empty title="Henüz gerçek başvuru yok">
              Keşfedilen ilanlar bu listede görünmez. Bir ilandan "Başvur" ile başvuru kaydı aç.
            </Empty>
          ) : (
            <div className="divide-y divide-subtle">
              {rows.map((item) => {
                const status = statusOf(item);
                const next = applicationNextAction(item);
                return (
                  <div key={item.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 py-2.5">
                    <button type="button" onClick={() => onOpen(item.id)} className="min-w-0 flex-1 text-left">
                      <span className="block truncate text-body font-medium text-primary">{item.title}</span>
                      <span className="block truncate text-micro text-muted">
                        {item.organization || "Kurum belirtilmemiş"}
                      </span>
                    </button>
                    <StatusChip status={status} />
                    <Meta label="Başvuru" value={item.applied_at ? formatTrDate(item.applied_at) : "—"} />
                    <Meta
                      label="Son değişim"
                      value={
                        item.application_status_changed_at ? relativeTime(item.application_status_changed_at) : "—"
                      }
                    />
                    <Meta
                      label="CV"
                      value={!item.cv_document_id ? "—" : (cvTitles.get(item.cv_document_id) ?? "CV bağlı")}
                    />
                    <Meta label="Takip" value={item.follow_up_at ? formatTrDate(item.follow_up_at) : "—"} />
                    <TransitionSelect
                      item={item}
                      online={online}
                      pending={transition.isPending}
                      onTransition={changeStatus}
                    />
                    {next && (
                      <p className="basis-full text-micro text-muted">
                        Sıradaki adım: <strong className="font-medium text-accent">{next.label}</strong> · {next.hint}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Section>
      )}

      {mode === "pipeline" && view === "kanban" && (
        <Section
          title="Başvuru hattı"
          hint={
            applications.isError || lifecycle.isError
              ? "okunamadı"
              : columns.length === 0
                ? "Durum makinesi yükleniyor…"
                : "Payda: yalnızca gerçek başvurular"
          }
        >
          {applications.isLoading || lifecycle.isLoading ? (
            <SkeletonRows rows={4} />
          ) : applications.isError ? (
            <QueryFailure
              message={`Başvurular yüklenemedi: ${
                applications.error instanceof Error ? applications.error.message : "bilinmeyen hata"
              }`}
              retrying={applications.isFetching}
              onRetry={() => void applications.refetch()}
            />
          ) : lifecycle.isError ? (
            <QueryFailure
              message={`Durum makinesi yüklenemedi: ${
                lifecycle.error instanceof Error ? lifecycle.error.message : "bilinmeyen hata"
              }`}
              retrying={lifecycle.isFetching}
              onRetry={() => void lifecycle.refetch()}
            />
          ) : columns.length === 0 ? (
            <Spinner label="Durum makinesi yükleniyor…" />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {columns.map((column) => {
                const columnRows = rows.filter((item) => column.statuses.includes(statusOf(item)));
                return (
                  <section key={column.key} aria-label={column.title} className="min-w-0">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="label-caps truncate text-secondary">{column.title}</span>
                      <span className="numeral text-meta tabular-nums text-muted">{columnRows.length}</span>
                    </div>
                    <div className="space-y-2">
                      {columnRows.length === 0 ? (
                        <p className="rounded-control border border-dashed border-subtle px-2 py-3 text-center text-micro text-muted">
                          Kayıt yok
                        </p>
                      ) : (
                        columnRows.map((item) => (
                          <div key={item.id} className="space-y-2 rounded-control border border-subtle bg-surface p-2">
                            <button type="button" onClick={() => onOpen(item.id)} className="block w-full text-left">
                              <span className="block truncate text-meta font-medium text-primary">{item.title}</span>
                              <span className="block truncate text-micro text-muted">
                                {item.organization || "Kurum belirtilmemiş"}
                              </span>
                            </button>
                            <div className="flex flex-wrap items-center gap-1.5">
                              <StatusChip status={statusOf(item)} />
                              <span className="text-micro text-muted">
                                {item.applied_at ? formatTrDate(item.applied_at) : "başvuru tarihi yok"}
                              </span>
                            </div>
                            <TransitionSelect
                              item={item}
                              online={online}
                              pending={transition.isPending}
                              onTransition={changeStatus}
                            />
                          </div>
                        ))
                      )}
                    </div>
                  </section>
                );
              })}
            </div>
          )}
        </Section>
      )}

      {mode === "followup" && (
        <div className="space-y-4">
          <Section
            title="Yaklaşan takipler"
            hint={followups.isError ? "okunamadı" : `${(followups.data ?? []).length} kayıt`}
            action={<CalendarClock size={14} className="text-icon" />}
          >
            {followups.isLoading ? (
              <SkeletonRows rows={3} />
            ) : followups.isError ? (
              <QueryFailure
                message={`Takipler yüklenemedi: ${
                  followups.error instanceof Error ? followups.error.message : "bilinmeyen hata"
                }`}
                retrying={followups.isFetching}
                onRetry={() => void followups.refetch()}
              />
            ) : (followups.data ?? []).length === 0 ? (
              <Empty>Takipli başvuru yok.</Empty>
            ) : (
              <div className="space-y-1.5">
                {(followups.data ?? []).map((item) => (
                  <RecordLink
                    key={item.id}
                    title={item.title}
                    subtitle={applicationStatusLabel(item.status)}
                    meta={relativeTime(item.follow_up_at)}
                    onOpen={() => onOpen(item.id)}
                  />
                ))}
              </div>
            )}
          </Section>
        </div>
      )}

      {mode === "stats" && (
        <>
          {funnel.isError ? (
            <Section title="Başvuru ritmi" hint="okunamadı">
              <QueryFailure
                message={`Başvuru ritmi yüklenemedi: ${
                  funnel.error instanceof Error ? funnel.error.message : "bilinmeyen hata"
                }`}
                retrying={funnel.isFetching}
                onRetry={() => void funnel.refetch()}
              />
            </Section>
          ) : sparse ? (
            <p className="text-meta text-muted">
              Henüz yeterli veri yok: başvuru ritmi grafikleri en az 3 gerçek başvuru birikince görünür.
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              <Section title="Haftalık başvuru ritmi" hint="Son 12 hafta">
                {funnel.isLoading ? <SkeletonRows rows={4} /> : <VolumeBars rows={funnelData?.weekly_volume ?? []} />}
              </Section>
              <Section title="Aylık başvuru ritmi" hint="Son 12 ay">
                {funnel.isLoading ? <SkeletonRows rows={4} /> : <VolumeBars rows={funnelData?.monthly_volume ?? []} />}
              </Section>
            </div>
          )}
        </>
      )}

      {mode === "stats" &&
        (funnel.isError ? (
          <Section title="Başvuru analizi" hint="okunamadı">
            <QueryFailure
              message={`Başvuru analitiği yüklenemedi: ${
                funnel.error instanceof Error ? funnel.error.message : "bilinmeyen hata"
              }`}
              retrying={funnel.isFetching}
              onRetry={() => void funnel.refetch()}
            />
          </Section>
        ) : (
          <>
            <MetricStrip className="grid-cols-2 lg:grid-cols-4">
              <Metric
                label="Gerçek başvuru"
                value={funnelData?.total ?? rows.length}
                hint="Payda: yalnızca gerçek başvurular"
              />
              <Metric label="Takip edilen" value={funnelData?.tracked ?? "—"} hint="preparing ve sonrası" />
              <Metric
                label="Ort. ilk yanıt"
                value={
                  funnelData?.avg_first_response_days === null || funnelData?.avg_first_response_days === undefined
                    ? "—"
                    : `${funnelData.avg_first_response_days} gün`
                }
                hint="başvurudan ilk yanıta"
              />
              <Metric
                label="Ort. başvuru → görüşme"
                value={
                  funnelData?.avg_applied_to_interview_days === null ||
                  funnelData?.avg_applied_to_interview_days === undefined
                    ? "—"
                    : `${funnelData.avg_applied_to_interview_days} gün`
                }
                hint="gün"
              />
            </MetricStrip>

            {sparse ? (
              <Section title="Başvuru analizi" hint={`Payda: ${applicationsTotal} gerçek başvuru`}>
                <Empty title="Henüz yeterli veri yok">
                  Dönüşüm, durum dağılımı ve kırılım grafikleri en az 3 gerçek başvuru biriktiğinde anlamlı olur.
                </Empty>
              </Section>
            ) : (
              <>
                <Section
                  title="Kohort dönüşümü"
                  hint={`Payda: ${funnelData?.cohort_size ?? 0} başvuru · eşik ${minimumSample}`}
                >
                  {funnel.isLoading ? (
                    <SkeletonRows rows={4} />
                  ) : (
                    <div className="space-y-1.5">
                      <CohortRow
                        label="Başvuru → görüşme"
                        reached={cohort.interview ?? 0}
                        base={cohort.applied ?? 0}
                        minimum={minimumSample}
                      />
                      <CohortRow
                        label="Görüşme → teklif"
                        reached={cohort.offer ?? 0}
                        base={cohort.interview ?? 0}
                        minimum={minimumSample}
                      />
                      <CohortRow
                        label="Teklif → kabul"
                        reached={cohort.accepted ?? 0}
                        base={cohort.offer ?? 0}
                        minimum={minimumSample}
                      />
                      <CohortRow
                        label="Başvuru → ret"
                        reached={cohort.rejected ?? 0}
                        base={cohort.applied ?? 0}
                        minimum={minimumSample}
                      />
                    </div>
                  )}
                  {funnelData && !funnelData.sufficient && (
                    <p className="mt-2 text-micro text-muted">
                      Örneklem küçük ({funnelData.cohort_size} başvuru): yanıltıcı yüzde yerine ham sayı gösteriliyor.
                    </p>
                  )}
                </Section>

                <div className="grid gap-4 lg:grid-cols-2">
                  <Section title="Durum dağılımı" hint={`Payda: ${funnelData?.total ?? rows.length} gerçek başvuru`}>
                    {funnel.isLoading ? (
                      <SkeletonRows rows={4} />
                    ) : (funnelData?.by_status ?? []).every((row) => row.count === 0) ? (
                      <Empty>Henüz başvuru yok.</Empty>
                    ) : (
                      <div className="space-y-1.5">
                        {(funnelData?.by_status ?? []).map((row) => (
                          <div key={row.status} className="flex items-center gap-2">
                            <span className="w-24 shrink-0 truncate text-meta text-secondary">
                              {applicationStatusLabel(row.status)}
                            </span>
                            <div className="h-3 min-w-0 flex-1 overflow-hidden rounded-control bg-surface-sunken">
                              <div
                                className="h-full rounded-control bg-accent"
                                style={{ width: `${(row.count / maxStatusCount) * 100}%` }}
                              />
                            </div>
                            <span className="w-8 shrink-0 text-right text-meta tabular-nums text-primary">
                              {row.count}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </Section>

                  <Section title="Red nedenleri" hint="Payda: red durumundaki başvurular">
                    {funnel.isLoading ? (
                      <SkeletonRows rows={3} />
                    ) : !reasonRows.some((row) => row.count > 0) ? (
                      <Empty>Henüz red kaydı yok.</Empty>
                    ) : (
                      <div className="divide-y divide-subtle">
                        {reasonRows.map((row) => (
                          <div key={row.reason} className="flex items-center gap-2 py-1.5">
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-danger" />
                            <span className="min-w-0 flex-1 truncate text-meta text-secondary">{row.reason}</span>
                            <Chip tone={row.count > 0 ? "danger" : "neutral"}>{row.count}</Chip>
                          </div>
                        ))}
                      </div>
                    )}
                  </Section>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <BreakdownTable
                    title="Kaynağa göre"
                    rows={funnelData?.by_source ?? []}
                    hint="Kayıt · yanıt · görüşme oranı"
                    labelFor={(row) => sourceLabel(row.key)}
                    minimumSample={minimumSample}
                  />
                  <BreakdownTable
                    title="CV'ye göre"
                    rows={funnelData?.by_cv ?? []}
                    hint="Kayıt · yanıt · görüşme oranı"
                    minimumSample={minimumSample}
                  />
                  <BreakdownTable
                    title="Role göre"
                    rows={funnelData?.by_role ?? []}
                    hint="Kayıt · yanıt · görüşme oranı"
                    minimumSample={minimumSample}
                  />
                  <BreakdownTable
                    title="Ülkeye göre"
                    rows={funnelData?.by_country ?? []}
                    hint="Kayıt · yanıt · görüşme oranı"
                    minimumSample={minimumSample}
                  />
                  <BreakdownTable
                    title="Çalışma biçimine göre"
                    rows={funnelData?.by_work_mode ?? []}
                    hint="Kayıt · yanıt · görüşme oranı"
                    minimumSample={minimumSample}
                  />
                </div>
              </>
            )}
          </>
        ))}

      {mode === "pipeline" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Section
            title="Yaklaşan takipler"
            hint={followups.isError ? "okunamadı" : `${(followups.data ?? []).length} kayıt · payda: aktif başvurular`}
            action={<CalendarClock size={14} className="text-icon" />}
          >
            {followups.isLoading ? (
              <SkeletonRows rows={3} />
            ) : followups.isError ? (
              <QueryFailure
                message={`Takipler yüklenemedi: ${
                  followups.error instanceof Error ? followups.error.message : "bilinmeyen hata"
                }`}
                retrying={followups.isFetching}
                onRetry={() => void followups.refetch()}
              />
            ) : (followups.data ?? []).length === 0 ? (
              <Empty>Takipli başvuru yok.</Empty>
            ) : (
              <div className="space-y-1.5">
                {(followups.data ?? []).slice(0, 5).map((item) => (
                  <RecordLink
                    key={item.id}
                    title={item.title}
                    subtitle={applicationStatusLabel(item.status)}
                    meta={relativeTime(item.follow_up_at)}
                    onOpen={() => onOpen(item.id)}
                  />
                ))}
              </div>
            )}
          </Section>

          <Section
            title="Firma sessizliği"
            hint="21 günü aşan yanıtsız görüşme · payda: görüşmedeki başvurular"
            action={<Radar size={14} className="text-icon" />}
          >
            {silence.isLoading ? (
              <SkeletonRows rows={3} />
            ) : silence.isError ? (
              <QueryFailure
                message={`Firma sessizliği yüklenemedi: ${
                  silence.error instanceof Error ? silence.error.message : "bilinmeyen hata"
                }`}
                retrying={silence.isFetching}
                onRetry={() => void silence.refetch()}
              />
            ) : (silence.data ?? []).length === 0 ? (
              <Empty>21 günü aşan yanıtsız görüşme yok.</Empty>
            ) : (
              <div className="space-y-1.5">
                {(silence.data ?? []).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onOpen(item.id)}
                    className="group flex w-full items-center gap-2 rounded-control border border-warn-border bg-warn-surface px-3 py-2 text-left transition hover:border-strong"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body font-medium text-primary">{item.title}</span>
                      <span className="block text-micro text-muted">{item.organization || "Kurum belirtilmemiş"}</span>
                    </span>
                    <Chip tone="warn">{item.days_silent} gün</Chip>
                    <ArrowRight size={13} className="shrink-0 text-muted transition group-hover:translate-x-0.5" />
                  </button>
                ))}
              </div>
            )}
          </Section>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Award,
  CalendarClock,
  Check,
  CheckSquare,
  Compass,
  ExternalLink,
  FileText,
  GitBranch,
  Paperclip,
  Star,
  Users,
  XCircle,
} from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { sourceLabel } from "@/core/labels";
import { displayScore } from "./scoreDomain";
import { RelatedPanel } from "@/core/RelatedPanel";
import { planDayForToday } from "@/core/tasks";
import { Button, Chip, Empty, Input, Section, Select, Tabs, relativeTime, useToast } from "@/core/ui";
import type {
  ApplicationHistoryRow,
  ApplicationTimeline,
  ApplicationTimelineEntry,
  Document,
  Opportunity,
  Todo,
} from "@/core/types";
import { useOnline } from "@/lib/hooks";
import type { VaultItem } from "@/core/obsidian";
import { CareerStoryBank } from "./CareerStoryBank";
import { OpportunityConnectionsSection } from "./OpportunityConnectionsSection";
import { OpportunityEvaluationSection } from "./OpportunityEvaluationSection";
import { OpportunityDeepEvaluationSection } from "./OpportunityDeepEvaluationSection";
import { OpportunityApplicationPackageSection } from "./OpportunityApplicationPackageSection";
import {
  ApplicationSection,
  FollowUpSection,
  InterviewsSection,
  OpportunityKnowledgeSection,
  ReplyProcessorSection,
  RequirementsSection,
} from "./OpportunityDetailSections";
import {
  APPLICATION_STATUS_TONES,
  REMOTE_LABELS,
  SCORE_TONE,
  STATUS_TONES,
  applicationStatusLabel,
  daysLeft,
  jobCategoryLabel,
  kindLabel,
  remoteKind,
  scoreBand,
  statusLabel,
} from "./labels";

type JobTab = "ozet" | "uyum" | "basvuru" | "notlar";

const TAB_ITEMS = [
  { id: "ozet", label: "Özet" },
  { id: "uyum", label: "Uyum" },
  { id: "basvuru", label: "Başvuru" },
  { id: "notlar", label: "Notlar ve İlişkiler" },
] as const;

const TAB_LABELS: Record<JobTab, string> = {
  ozet: "Özet",
  uyum: "Uyum",
  basvuru: "Başvuru",
  notlar: "Notlar ve İlişkiler",
};

const SOURCE_STATUS_LABELS: Record<string, string> = {
  active: "Kaynakta aktif",
  missing: "Kaynakta görünmüyor",
  likely_closed: "Muhtemelen kapandı",
  closed: "Kapandı",
};

/** Puan bilesenlerinin Turkce etiketleri (forkjob skor kirilimi). */
const SCORE_REASON_LABELS: Record<string, string> = {
  base: "Temel puan",
  role: "Rol uyumu",
  skills: "Beceri uyumu",
  level: "Seviye",
  seniority: "Kıdem",
  visa: "Vize / sponsorluk",
  earning: "Ücret beklentisi",
  language: "Dil",
  experience: "Deneyim",
  relocation: "Taşınma",
  freshness: "Tazelik",
  total: "Toplam",
  killed: "Eleme sinyali",
};

/** Kaynak gozlemi + kapanma zamanindan turetilen kapanma ihtimali. */
function closureRisk(item: Opportunity): { label: string; tone: "ok" | "warn" | "danger"; detail: string } {
  if (item.closed_at || item.source_status === "closed") {
    return {
      label: "Kapandı",
      tone: "danger",
      detail: item.closed_at
        ? `${new Date(item.closed_at).toLocaleDateString("tr-TR")} tarihinde kaynaktan kalktı.`
        : "Kaynak kaydı kapandı olarak işaretlendi.",
    };
  }
  if (item.source_status === "likely_closed") {
    return {
      label: "Yüksek",
      tone: "warn",
      detail: "İlan kaynakta uzun süredir görünmüyor; kapanmış olabilir.",
    };
  }
  if (item.source_status === "missing") {
    return {
      label: "Orta",
      tone: "warn",
      detail: "İlan son taramada kaynakta bulunamadı; kapanma ihtimali var.",
    };
  }
  return {
    label: "Düşük",
    tone: "ok",
    detail: "İlan son taramada kaynakta görüldü.",
  };
}

/**
 * CV degerlendirmesi, ilan verisiyle birlikte saklanan bir parmak izine baglidir.
 * Parmak izi istemcide yeniden uretilemez (profil + CV metni gerekir); bu yuzden
 * bayatlik, ilanin degerlendirmeden SONRA yeniden gorulmesiyle yaklasik olarak
 * turetilir. Kesin yeniden uretim icin degerlendirme yenilenmelidir.
 */
function evaluationStale(item: Opportunity): boolean | null {
  const evaluation = item.evaluation;
  if (!evaluation) return null;
  const evaluated = Date.parse(evaluation.evaluated_at);
  const seen = item.last_seen_at ? Date.parse(item.last_seen_at) : Number.NaN;
  if (!Number.isFinite(evaluated) || !Number.isFinite(seen)) return null;
  return seen > evaluated;
}

function reasonValue(value: unknown): string {
  if (typeof value === "number") return `${value > 0 ? "+" : ""}${value}`;
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const parts: string[] = [];
    if (record.term != null) parts.push(String(record.term));
    if (record.where != null) parts.push(String(record.where));
    if (typeof record.delta === "number") parts.push(`${record.delta > 0 ? "+" : ""}${record.delta}`);
    if (parts.length > 0) return parts.join(" · ");
    return JSON.stringify(record);
  }
  return value == null ? "—" : String(value);
}

const TIMELINE_ICONS: Record<ApplicationTimelineEntry["kind"], LucideIcon> = {
  discovered: Compass,
  shortlisted: Star,
  status: GitBranch,
  followup: CalendarClock,
  interview: Users,
  note: FileText,
  document: Paperclip,
  todo: CheckSquare,
  offer: Award,
  rejection: XCircle,
};

/** Is ilani detayi: ozet, uc katmanli uyum, basvuru hatti ve iliski/notlar. */
export function JobDetail({ item }: { item: Opportunity }) {
  const online = useOnline();
  const [tab, setTab] = useState<JobTab>("ozet");

  return (
    <div className="flex flex-col gap-4">
      <JobSummary item={item} online={online} />
      <Tabs<JobTab> ariaLabel="İş ilanı sekmeleri" value={tab} onChange={setTab} items={[...TAB_ITEMS]} />
      <div role="tabpanel" aria-label={TAB_LABELS[tab]} id={`job-tabpanel-${tab}`}>
        {tab === "ozet" && <JobOverview item={item} online={online} />}
        {tab === "uyum" && <JobFit item={item} online={online} />}
        {tab === "basvuru" && <JobApplication item={item} online={online} />}
        {tab === "notlar" && <JobNotes item={item} online={online} />}
      </div>
    </div>
  );
}

function JobSummary({ item, online }: { item: Opportunity; online: boolean }) {
  const shortlist = useMutation({
    mutationFn: () => api.post(`/opportunities/${item.id}/transition`, { to: "shortlisted" }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });
  const band = scoreBand(item.score);
  const left = daysLeft(item.deadline_at);
  const workMode = remoteKind(item.remote);
  const url = item.url;

  return (
    <div className="stack-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <Chip>{kindLabel(item.kind)}</Chip>
        <Chip>{jobCategoryLabel(item.category)}</Chip>
        <Chip tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Chip>
        {band && (
          <Chip tone={SCORE_TONE[band]}>{band === "eliminated" ? "Elendi" : `${displayScore(item.score)} Puan`}</Chip>
        )}
      </div>
      <p className="text-meta text-muted">
        {[item.organization, item.location, workMode ? REMOTE_LABELS[workMode] : null, item.compensation]
          .filter(Boolean)
          .join(" · ") || "—"}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {url && (
          <>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="flex h-control items-center gap-1.5 rounded-control border border-subtle bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
            >
              <ExternalLink size={13} /> İlanı Aç
            </a>
            {item.allowed_transitions.includes("shortlisted") && (
              <Button
                variant="secondary"
                size="sm"
                disabled={!online || shortlist.isPending}
                title="Kısa Listeye Al"
                onClick={() => shortlist.mutate()}
              >
                <Star size={13} /> Kısa Listeye Al
              </Button>
            )}
          </>
        )}
        {left !== null && (
          <span className={`text-meta font-medium tabular-nums ${left <= 7 ? "text-warn" : "text-muted"}`}>
            {left < 0 ? `${Math.abs(left)} gün önce doldu` : `Son tarihe ${left} gün`}
          </span>
        )}
      </div>
    </div>
  );
}

function ListingHealthSection({ item, online }: { item: Opportunity; online: boolean }) {
  const toast = useToast();
  const health = item.intelligence?.listing_health;

  const checkLiveness = useMutation({
    mutationFn: () => api.post(`/opportunities/${item.id}/liveness`, {}),
    onSuccess: () => {
      toast.push("Canlılık durumu güncellendi.", { tone: "ok" });
      invalidateAfter("opportunity.write");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Canlılık kontrolü başarısız";
      toast.push(msg, { tone: "danger" });
    },
  });

  const extractJd = useMutation({
    mutationFn: () => api.post(`/opportunities/${item.id}/extract-jd`, {}),
    onSuccess: (data: any) => {
      if (data?.promoted) {
        toast.push("İlan metni zenginleştirildi.", { tone: "ok" });
      } else if (data?.identity_status === "invalid_non_job") {
        toast.push("İlan metni doğrulanamadı. Kaynak genel kariyer sayfasına yönlendirdi.", { tone: "warn" });
      } else if (data?.identity_status === "uncertain_identity") {
        toast.push("İlan kimliği doğrulanamadı.", { tone: "warn" });
      } else if (data?.reason === "already_has_substantive_description") {
        toast.push("İlan açıklaması zaten mevcut.", { tone: "neutral" });
      } else {
        toast.push("İlan metni yükseltilmedi.", { tone: "neutral" });
      }
      invalidateAfter("opportunity.write");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "İlan metni çıkarılamadı";
      toast.push(msg, { tone: "danger" });
    },
  });

  const healthScore = health?.health_score ?? 100;
  const scoreTone: "ok" | "warn" | "danger" = healthScore >= 75 ? "ok" : healthScore >= 50 ? "warn" : "danger";

  const livenessLabels: Record<string, string> = {
    live: "Canlı",
    at_risk: "Kapanma Riski",
    expired: "Kapandı",
    uncertain: "Belirsiz",
    unchecked: "Kontrol Edilmedi",
  };
  const livenessTones: Record<string, "ok" | "warn" | "danger" | "neutral"> = {
    live: "ok",
    at_risk: "warn",
    expired: "danger",
    uncertain: "warn",
    unchecked: "neutral",
  };

  const completenessLabels: Record<string, string> = {
    complete: "Tam Açıklama (>1000 kr)",
    concise: "Özet Açıklama (300-1000 kr)",
    stub: "Kısa/Taslak Açıklama (<300 kr)",
  };

  const salaryLabels: Record<string, string> = {
    transparent: "Maaş: Şeffaf",
    unclear: "Maaş: Belirsiz Aralık",
    missing: "Maaş: Belirtilmemiş",
  };

  const repostLabels: Record<string, string> = {
    none: "İlk Kez Görüldü",
    moderate: "Tekrar İlan (2x)",
    frequent: "Sık Tekrar (3+)",
  };

  return (
    <Section title="İlan kalitesi ve canlılık" hint={health ? `${healthScore} / 100 Kalite` : undefined}>
      <div className="stack-y-3">
        <div className="flex flex-wrap items-center gap-2">
          {health && <Chip tone={scoreTone}>Kalite Puanı: {healthScore} / 100</Chip>}
          {health && (
            <Chip tone={livenessTones[health.liveness_status] ?? "neutral"}>
              {livenessLabels[health.liveness_status] ?? health.liveness_status}
            </Chip>
          )}
          {health && (
            <Chip tone={health.jd_completeness === "stub" ? "warn" : "neutral"}>
              {completenessLabels[health.jd_completeness] ?? health.jd_completeness}
            </Chip>
          )}
          {health && (
            <Chip
              tone={
                health.salary_transparency === "transparent"
                  ? "ok"
                  : health.salary_transparency === "unclear"
                    ? "warn"
                    : "neutral"
              }
            >
              {salaryLabels[health.salary_transparency] ?? health.salary_transparency}
            </Chip>
          )}
          {health && health.repost_frequency !== "none" && (
            <Chip tone={health.repost_frequency === "frequent" ? "danger" : "warn"}>
              {repostLabels[health.repost_frequency] ?? health.repost_frequency}
            </Chip>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button
            variant="secondary"
            size="sm"
            disabled={!online || checkLiveness.isPending}
            onClick={() => checkLiveness.mutate()}
          >
            <Activity size={13} />
            {checkLiveness.isPending ? "Kontrol Ediliyor..." : "Canlılık Kontrolü"}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={!online || extractJd.isPending}
            onClick={() => extractJd.mutate()}
          >
            <FileText size={13} />
            {extractJd.isPending ? "Çıkarılıyor..." : "İlan Metnini Çıkar"}
          </Button>
        </div>
      </div>
    </Section>
  );
}

function JobOverview({ item, online }: { item: Opportunity; online: boolean }) {
  const risk = closureRisk(item);
  const workMode = remoteKind(item.remote);
  const rows: [string, string][] = [
    ["Kurum", item.organization || "—"],
    ["Lokasyon", item.location || "Belirtilmemiş"],
    ["Çalışma biçimi", workMode ? REMOTE_LABELS[workMode] : "—"],
    ["Ücret / Maaş", item.compensation || "Belirtilmemiş"],
    ["Kaynak", sourceLabel(item.source)],
    ["İlan tarihi", item.published_at ? new Date(item.published_at).toLocaleDateString("tr-TR") : "—"],
    ["Son başvuru", item.deadline_at ? new Date(item.deadline_at).toLocaleDateString("tr-TR") : "—"],
    ["İlk görülme", new Date(item.found_at).toLocaleDateString("tr-TR")],
    ["Son görülme", item.last_seen_at ? relativeTime(item.last_seen_at) : "—"],
    ["Kaynak durumu", SOURCE_STATUS_LABELS[item.source_status ?? "active"] ?? item.source_status ?? "—"],
    ["Kapandı", item.closed_at ? new Date(item.closed_at).toLocaleDateString("tr-TR") : "—"],
  ];

  return (
    <div className="stack-y-4">
      <Section title="İlan künyesi">
        <dl className="grid grid-cols-[9rem_1fr] gap-x-4 gap-y-2 text-meta">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="font-medium text-muted">{label}</dt>
              <dd className="font-medium text-primary">{value}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <ListingHealthSection item={item} online={online} />

      <Section title="Kapanma ihtimali" hint={SOURCE_STATUS_LABELS[item.source_status ?? "active"] ?? undefined}>
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone={risk.tone}>{risk.label}</Chip>
          <span className="text-meta text-secondary">{risk.detail}</span>
        </div>
      </Section>

      <Section title="Risk sinyalleri" hint={`${item.intelligence?.signals.length ?? 0} yerel sinyal`}>
        {!item.intelligence || item.intelligence.signals.length === 0 ? (
          <Empty>Bu ilan için yerel risk sinyali bulunmadı.</Empty>
        ) : (
          <ul className="stack-y-2">
            {item.intelligence.signals.map((signal) => (
              <li key={signal.code} className="rounded-control border border-subtle bg-surface-sunken px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Chip tone={signal.severity}>{signal.label}</Chip>
                  {signal.code === "repost" && (
                    <span className="text-micro tabular-nums text-muted">
                      {item.intelligence?.repost_count} bağlantı
                    </span>
                  )}
                </div>
                <p className="mt-1 text-meta text-secondary">{signal.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}

function JobFit({ item, online }: { item: Opportunity; online: boolean }) {
  const band = scoreBand(item.score);
  const profileRatio = item.profile_match_ratio ?? item.skill_match?.match_ratio ?? null;
  const candidateMatch = item.raw.candidate_match;
  const matchEvidence =
    candidateMatch && typeof candidateMatch === "object"
      ? (candidateMatch as { coverage?: number; unknown?: string[]; algorithm?: string })
      : null;
  const stale = evaluationStale(item);
  const evaluation = item.evaluation ?? null;

  return (
    <div className="stack-y-4">
      {/* (a) Genel uygunluk — kural tabanli puan, aciklanabilir bilesenlerle. */}
      <Section title="Genel uygunluk" hint={item.score_source ?? "henüz hesaplanmadı"}>
        {item.score === null || item.score === undefined ? (
          <Empty>Bu ilan için genel uygunluk puanı henüz hesaplanmadı.</Empty>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <span className="numeral text-numeral-xl leading-none text-primary">
                {band === "eliminated" ? "Elendi" : displayScore(item.score)}
              </span>
              {band && (
                <Chip tone={SCORE_TONE[band]}>
                  {band === "eliminated" ? "Elendi" : `${displayScore(item.score)} / 100`}
                </Chip>
              )}
              {item.score_source && <Chip>{item.score_source}</Chip>}
              {item.score_computed_at && (
                <span className="text-meta text-muted">Hesaplandı: {relativeTime(item.score_computed_at)}</span>
              )}
            </div>
            {item.score_reasons ? (
              <div className="mt-3 rounded-control border border-subtle bg-surface-sunken p-3">
                <span className="mb-2 block text-micro font-medium uppercase tracking-wider text-secondary">
                  Neden bu puan?
                </span>
                <dl className="grid grid-cols-[10rem_1fr] gap-x-3 gap-y-1 text-meta">
                  {Object.entries(item.score_reasons).map(([key, value]) => (
                    <div key={key} className="contents">
                      <dt className="text-muted">{SCORE_REASON_LABELS[key] ?? key}</dt>
                      <dd className="tabular-nums text-primary">{reasonValue(value)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : (
              <p className="mt-2 text-meta text-muted">
                Puan bileşenleri bu kayıt için taşınmıyor (yalnızca detay ucu açıklamayı içerir).
              </p>
            )}
          </>
        )}
      </Section>

      {/* (b) Kanıta dayalı CV/profil ve ilan gereksinimi eşleşmesi. */}
      <Section title="CV / profil uyumu" hint="Kanıta dayalı gereksinim eşleşmesi">
        {profileRatio === null ? (
          <Empty>
            {matchEvidence?.algorithm
              ? "Kanıt yetersiz; güvenilir bir oran hesaplanamadı."
              : "Uyum henüz hesaplanmadı."}
          </Empty>
        ) : (
          <>
            <div className="mb-4 flex items-center gap-3">
              <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                <div
                  className="h-full rounded-full bg-ok transition-all"
                  style={{ width: `${Math.max(0, Math.min(100, Math.round(profileRatio * 100)))}%` }}
                />
              </div>
              <Chip tone="ok">%{Math.round(profileRatio * 100)}</Chip>
            </div>
            <p className="mb-3 text-meta text-muted">
              Yerel CV ve doğrulanmış profil kanıtları ilanın gereksinimleriyle karşılaştırılır. Bilinmeyenler eksik
              sayılmaz.
            </p>
            {typeof matchEvidence?.coverage === "number" && (
              <p className="mb-3 text-meta text-muted">Kanıt kapsamı: %{Math.round(matchEvidence.coverage * 100)}</p>
            )}
            <div className="stack-y-3">
              {item.skill_match && item.skill_match.matched.length > 0 && (
                <div>
                  <span className="mb-1.5 block text-micro font-medium uppercase tracking-wider text-secondary">
                    Örtüşen yetenekler ({item.skill_match.matched.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {item.skill_match.matched.map((skill) => (
                      <Chip key={skill} tone="ok">
                        {skill}
                      </Chip>
                    ))}
                  </div>
                </div>
              )}
              {item.skill_match && item.skill_match.missing.length > 0 && (
                <div>
                  <span className="mb-1.5 block text-micro font-medium uppercase tracking-wider text-muted">
                    Kanıtlanan eksikler ({item.skill_match.missing.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {item.skill_match.missing.map((skill) => (
                      <Chip key={skill}>{skill}</Chip>
                    ))}
                  </div>
                </div>
              )}
              {matchEvidence?.unknown && matchEvidence.unknown.length > 0 && (
                <p className="text-meta text-muted">Kanıtı bilinmeyen gereksinim: {matchEvidence.unknown.length}</p>
              )}
            </div>
          </>
        )}
      </Section>

      {/* (c) CV degerlendirmesi — gercek career-ops degerlendirmesi. */}
      <Section
        title="CV Değerlendirmesi"
        hint={evaluation ? evaluation.version : "henüz çalıştırılmadı"}
        action={
          stale === true ? (
            <Chip tone="warn">İlan verisi değerlendirmeden sonra güncellendi</Chip>
          ) : stale === false ? (
            <Chip tone="ok">Değerlendirme güncel</Chip>
          ) : undefined
        }
      >
        {!evaluation ? (
          <p className="text-meta text-secondary">
            Bu ilan için CV değerlendirmesi yok. Aşağıdan çalıştırabilirsin; değerlendirme başvuruya bağlı CV belgesini
            (yoksa en güncel yerel CV'yi) kullanır ve yalnızca bu cihazda çalışır.
          </p>
        ) : (
          <dl className="mb-4 grid grid-cols-[11rem_1fr] gap-x-3 gap-y-1 text-meta">
            <div className="contents">
              <dt className="text-muted">Aday belgesi</dt>
              <dd className="text-primary">
                {evaluation.candidate_document_title ?? "Belge bağlı değil (yerel profil kullanıldı)"}
                {evaluation.candidate_document_id && (
                  <span className="ml-1 text-micro text-muted">({evaluation.candidate_document_id.slice(0, 8)}…)</span>
                )}
              </dd>
            </div>
            <div className="contents">
              <dt className="text-muted">Kaynak parmak izi</dt>
              <dd className="font-mono text-primary">{evaluation.source_fingerprint}</dd>
            </div>
            <div className="contents">
              <dt className="text-muted">Değerlendirme anı</dt>
              <dd className="text-primary">{relativeTime(evaluation.evaluated_at)}</dd>
            </div>
          </dl>
        )}
        <OpportunityEvaluationSection id={item.id} evaluation={evaluation} online={online} />
      </Section>

      {/* (d) Derin Uzman Değerlendirmesi (C4). */}
      <Section title="Kariyer Uzmanı Derin Değerlendirmesi" hint="kanıta dayalı analiz">
        <OpportunityDeepEvaluationSection opportunityId={item.id} online={online} />
      </Section>
    </div>
  );
}

function JobApplication({ item, online }: { item: Opportunity; online: boolean }) {
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });
  const { data: steps = [] } = useQuery({
    queryKey: ["opportunity", item.id, "todos"],
    queryFn: () => api.get<Todo[]>(`/opportunities/${item.id}/todos`),
  });
  const { data: history = [] } = useQuery({
    queryKey: ["opportunity", item.id, "history"],
    queryFn: () => api.get<ApplicationHistoryRow[]>(`/opportunities/${item.id}/history`),
  });
  const [stepTitle, setStepTitle] = useState("");

  const transition = useMutation({
    mutationFn: (to: string) => api.post(`/applications/${item.id}/transition`, { to }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  const addStep = useMutation({
    mutationFn: () =>
      api.post(`/opportunities/${item.id}/todos`, { title: stepTitle.trim(), plan_day: planDayForToday() }),
    onSuccess: () => {
      setStepTitle("");
      invalidateAfter("opportunity.write", "todo.write");
    },
  });

  const toggleStep = useMutation({
    mutationFn: (step: Todo) =>
      step.status === "done"
        ? api.patch(`/todos/${step.id}`, { status: "open" })
        : api.post(`/todos/${step.id}/complete`),
    onSuccess: () => invalidateAfter("opportunity.write", "todo.write"),
  });

  const allowedApplication = item.allowed_application_transitions ?? [];

  return (
    <div className="stack-y-4">
      <Section title="Başvuru hattı" hint={item.application_status ? "CRM" : "henüz başvurulmadı"}>
        {item.application_status ? (
          <div className="flex flex-wrap items-center gap-3">
            <Chip tone={APPLICATION_STATUS_TONES[item.application_status] ?? "neutral"}>
              {applicationStatusLabel(item.application_status)}
            </Chip>
            {item.application_status_changed_at && (
              <span className="text-meta text-muted">
                Aşama değişti: {relativeTime(item.application_status_changed_at)}
              </span>
            )}
            <Select
              value=""
              disabled={!online || allowedApplication.length === 0}
              ariaLabel="Başvuru aşaması"
              onChange={(value) => value && transition.mutate(value)}
              className="w-52 border-strong font-medium"
            >
              <option value="">{allowedApplication.length === 0 ? "İzinli geçiş yok" : "Aşamayı güncelle…"}</option>
              {allowedApplication.map((status) => (
                <option key={status} value={status}>
                  {applicationStatusLabel(status)}
                </option>
              ))}
            </Select>
          </div>
        ) : (
          <p className="text-meta text-secondary">
            Bu ilan için henüz başvuru kaydı yok. Aşağıdaki başvuru formundan başvurduğunda ilan snapshot'ı ve CV
            künyesi saklanır.
          </p>
        )}
      </Section>

      <Section title="Başvuru bilgileri">
        <ApplicationSection id={item.id} online={online} documents={documents} />
      </Section>

      <Section title="Kariyer Başvuru Paketi" hint="CV uyarlama, ön yazı ve soru yanıtları">
        <OpportunityApplicationPackageSection opportunityId={item.id} online={online} />
      </Section>

      <Section title="Takip">
        <FollowUpSection id={item.id} followUpAt={item.follow_up_at} />
      </Section>

      <Section title="Görüşmeler">
        <InterviewsSection id={item.id} online={online} />
      </Section>

      <Section title="Gelen yanıtı işle">
        <ReplyProcessorSection id={item.id} status={item.status} online={online} />
      </Section>

      <Section
        title="Başvuru adımları & görevler"
        hint={`${steps.filter((step) => step.status === "done").length}/${steps.length} tamamlandı`}
      >
        {steps.length === 0 ? (
          <Empty>Henüz görev adımı eklenmedi.</Empty>
        ) : (
          <ul className="mb-3 flex flex-col gap-2">
            {steps.map((step) => (
              <li
                key={step.id}
                className="flex items-center gap-2 rounded-control border border-subtle bg-surface-sunken px-3 py-2"
              >
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={step.status === "done"}
                  disabled={!online || toggleStep.isPending}
                  onClick={() => toggleStep.mutate(step)}
                  title={step.status === "done" ? "Adımı aç" : "Adımı tamamla"}
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition ${
                    step.status === "done"
                      ? "border-ok bg-ok text-canvas"
                      : "border-strong bg-surface hover:border-accent"
                  }`}
                >
                  {step.status === "done" && <Check size={11} />}
                </button>
                <span
                  className={`min-w-0 flex-1 truncate text-body ${step.status === "done" ? "text-muted line-through" : ""}`}
                >
                  {step.title}
                </span>
              </li>
            ))}
          </ul>
        )}
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (stepTitle.trim()) addStep.mutate();
          }}
        >
          <Input
            value={stepTitle}
            onChange={setStepTitle}
            placeholder="Örn. Formu doldur, referans mektubu iste…"
            ariaLabel="Yeni başvuru adımı"
            className="flex-1"
          />
          <Button type="submit" size="sm" disabled={!online || !stepTitle.trim() || addStep.isPending}>
            Ekle
          </Button>
        </form>
      </Section>

      <TimelineSection id={item.id} />

      <Section title="Süreç geçmişi" hint={`${history.length} geçiş kaydı`}>
        {history.length === 0 ? (
          <Empty>Henüz aşama değişikliği kaydedilmedi.</Empty>
        ) : (
          <ol className="stack-y-2">
            {history.map((row) => (
              <li key={row.id} className="flex items-center gap-2 text-meta">
                <span className="w-24 shrink-0 text-muted">
                  {row.scope === "discovery"
                    ? statusLabel(row.from_status ?? "—")
                    : applicationStatusLabel(row.from_status ?? "—")}
                </span>
                <span className="text-accent">→</span>
                <span className="font-medium text-primary">
                  {row.scope === "discovery" ? statusLabel(row.to_status) : applicationStatusLabel(row.to_status)}
                </span>
                <span className="ml-auto shrink-0 tabular-nums text-muted">{relativeTime(row.at)}</span>
              </li>
            ))}
          </ol>
        )}
      </Section>
    </div>
  );
}

function TimelineSection({ id }: { id: string }) {
  const { data } = useQuery({
    queryKey: ["opportunity", id, "timeline"],
    queryFn: () => api.get<ApplicationTimeline>(`/opportunities/${id}/timeline`),
  });
  const entries = [...(data?.entries ?? [])].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));

  return (
    <Section title="Zaman çizelgesi" hint={`${entries.length} kayıt`}>
      {entries.length === 0 ? (
        <Empty>Bu fırsat için henüz zaman çizelgesi kaydı yok.</Empty>
      ) : (
        <ol className="stack-y-3">
          {entries.map((entry, index) => {
            const Icon = TIMELINE_ICONS[entry.kind] ?? Compass;
            return (
              <li key={`${entry.kind}-${entry.at}-${index}`} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-accent">
                  <Icon size={13} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-body text-primary">{entry.title}</strong>
                    {entry.status && <Chip>{statusLabel(entry.status)}</Chip>}
                    <span className="ml-auto text-micro tabular-nums text-muted">{relativeTime(entry.at)}</span>
                  </div>
                  {entry.detail && <p className="mt-0.5 text-meta text-secondary">{entry.detail}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Section>
  );
}

function JobNotes({ item, online }: { item: Opportunity; online: boolean }) {
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });

  return (
    <div className="stack-y-4">
      <OpportunityKnowledgeSection
        id={item.id}
        online={online}
        canonical
        title="Şirket & Mülakat Notu"
        description="Bu ilan ve kurum için araştırma notu Obsidian Vault'unda yaşar; forkOS yalnız köprüyü kurar."
        searchQuery={item.title}
        createLabel="Araştırma notu oluştur"
        emptyTitle="Henüz Şirket Notu Oluşturulmadı"
        emptyText={`${item.organization || "Şirket"} hakkında faaliyet alanı, teknoloji yığını ve mülakat soruları için tek tıkla Vault'ta şablon not oluştur.`}
        create={() => api.post<VaultItem>(`/opportunities/${item.id}/research-note`)}
      />

      {item.notes && (
        <Section title="İlan notu">
          <p className="whitespace-pre-line text-body text-secondary">{item.notes}</p>
        </Section>
      )}

      <Section title="Gereksinimler">
        <RequirementsSection id={item.id} online={online} documents={documents} />
      </Section>

      <JobStories />

      <OpportunityConnectionsSection id={item.id} />

      <Section title="İlişkili kayıtlar">
        <RelatedPanel entityId={item.id} />
      </Section>
    </div>
  );
}

/** Mulakat hazirligi icin STAR hikaye bankasi (degerlendirme eslesmeleriyle ortusur). */
function JobStories() {
  const [open, setOpen] = useState(false);
  return (
    <Section
      title="STAR hikâyeleri"
      hint="mülakat hazırlığı"
      action={
        <Button size="sm" onClick={() => setOpen((value) => !value)}>
          {open ? "Kapat" : "Aç"}
        </Button>
      }
    >
      {open ? <CareerStoryBank /> : <p className="text-meta text-muted">Hikâye bankası kapalı.</p>}
    </Section>
  );
}

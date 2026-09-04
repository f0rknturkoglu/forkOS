import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertOctagon, RefreshCw, Save, Sparkles } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Checkbox, Chip, SectionHeader, Select, Textarea, cx, useToast } from "@/core/ui";
import type {
  CandidateMatch,
  CareerStory,
  EvaluationMatch,
  EvaluationRequirement,
  OpportunityArchetype,
  OpportunityEvaluation,
  RequirementEvidence,
  RequirementImportance,
} from "@/core/types";

const IMPORTANCE_LABELS: Record<RequirementImportance, string> = {
  critical: "Kritik",
  high: "Yüksek",
  meaningful: "Anlamlı",
  preferred: "Tercih",
  low_signal: "Zayıf sinyal",
};

const EVIDENCE_LABELS: Record<RequirementEvidence, string> = {
  stated: "Açıkça yazıyor",
  structural: "Yapısal",
  inferred: "Tahmini",
};

const MATCH_LABELS: Record<CandidateMatch, string> = {
  strong: "Güçlü",
  partial: "Kısmi",
  missing: "Eksik",
};

const ARCHETYPE_LABELS: Record<OpportunityArchetype, string> = {
  fde: "FDE",
  sa: "Solutions Architect",
  pm: "Product Manager",
  llmops: "LLMOps",
  agentic: "Agentic Systems",
  transformation: "Transformation",
};

const IMPORTANCE_OPTIONS = Object.keys(IMPORTANCE_LABELS) as RequirementImportance[];
const EVIDENCE_OPTIONS = Object.keys(EVIDENCE_LABELS) as RequirementEvidence[];
const MATCH_OPTIONS = Object.keys(MATCH_LABELS) as CandidateMatch[];
const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as OpportunityArchetype[];

function cloneEvaluation(evaluation: OpportunityEvaluation): OpportunityEvaluation {
  return JSON.parse(JSON.stringify(evaluation)) as OpportunityEvaluation;
}

function importanceTone(value: RequirementImportance) {
  if (value === "critical") return "danger" as const;
  if (value === "high") return "warn" as const;
  if (value === "meaningful") return "accent" as const;
  return "neutral" as const;
}

function matchTone(value: CandidateMatch) {
  if (value === "strong") return "ok" as const;
  if (value === "partial") return "warn" as const;
  return "danger" as const;
}

function recommendationLabel(value: OpportunityEvaluation["recommendation"]) {
  if (value === "pursue") return "Başvurmaya değer";
  if (value === "consider") return "İnceleyerek ilerle";
  return "Şimdilik geç";
}

export function OpportunityEvaluationSection({
  id,
  evaluation,
  online,
}: {
  id: string;
  evaluation: OpportunityEvaluation | null;
  online: boolean;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<OpportunityEvaluation | null>(evaluation ? cloneEvaluation(evaluation) : null);
  const { data: stories = [] } = useQuery({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });

  useEffect(() => {
    if (!editing) setDraft(evaluation ? cloneEvaluation(evaluation) : null);
  }, [evaluation, editing]);

  const generate = useMutation({
    mutationFn: () => api.post<OpportunityEvaluation>(`/opportunities/${id}/evaluation`),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      toast.push("İki aşamalı değerlendirme yenilendi.", { tone: "ok" });
    },
    onError: () => toast.push("İlan değerlendirilemedi.", { tone: "danger" }),
  });

  const save = useMutation({
    mutationFn: (value: OpportunityEvaluation) =>
      api.put<OpportunityEvaluation>(`/opportunities/${id}/evaluation`, {
        archetype: value.archetype,
        requirements: value.requirements,
        matches: value.matches,
        notes: value.notes,
      }),
    onSuccess: () => {
      setEditing(false);
      invalidateAfter("opportunity.write");
      toast.push("Değerlendirme düzenlemeleri kaydedildi.", { tone: "ok" });
    },
    onError: () => toast.push("Değerlendirme kaydedilemedi.", { tone: "danger" }),
  });

  function patchRequirement(id: string, patch: Partial<EvaluationRequirement>) {
    setDraft((current) => {
      if (!current) return current;
      const requirements = current.requirements.map((item) => {
        if (item.id !== id) return item;
        const next = { ...item, ...patch };
        if (next.evidence === "inferred" && (next.importance === "critical" || next.importance === "high")) {
          next.importance = "meaningful";
        }
        return next;
      });
      return { ...current, requirements };
    });
  }

  function patchMatch(requirementId: string, patch: Partial<EvaluationMatch>) {
    setDraft((current) =>
      current
        ? {
            ...current,
            matches: current.matches.map((item) =>
              item.requirement_id === requirementId ? { ...item, ...patch } : item,
            ),
          }
        : current,
    );
  }

  function toggleStory(requirementId: string, storyId: string, checked: boolean) {
    const match = draft?.matches.find((item) => item.requirement_id === requirementId);
    const current = match?.story_ids ?? [];
    patchMatch(requirementId, {
      story_ids: checked ? [...new Set([...current, storyId])] : current.filter((id) => id !== storyId),
    });
  }

  if (!evaluation || !draft) {
    return (
      <section className="rounded-card border border-subtle bg-surface p-5 shadow-card">
        <div className="mx-auto max-w-content py-8 text-center">
          <Sparkles size={22} className="mx-auto text-accent" />
          <h3 className="mt-3 text-heading text-primary">İlanı iki aşamada değerlendir</h3>
          <p className="mx-auto mt-1 max-w-prose text-meta text-muted">
            Önce yalnızca ilan metninden gereksinimler çıkarılır; ardından başvuruya bağlı CV veya en güncel yerel CV
            ile eşleştirilir. CV bulunamazsa yerel uyum profili kullanılır. Hiçbir veri dışarı gönderilmez.
          </p>
          <Button
            variant="primary"
            className="mt-4"
            disabled={!online || generate.isPending}
            onClick={() => generate.mutate()}
          >
            <Sparkles size={14} /> {generate.isPending ? "Değerlendiriliyor…" : "İlanı değerlendir"}
          </Button>
        </div>
      </section>
    );
  }

  const recommendationTone =
    draft.recommendation === "pursue" ? "ok" : draft.recommendation === "consider" ? "warn" : "danger";

  return (
    <div className="space-y-4">
      {draft.notes && draft.notes.includes("İlan metni çok kısa") && (
        <div className="rounded-card border border-warn-border bg-warn-surface p-3 text-meta text-warn">
          <strong>İlan metni uyarısı:</strong> {draft.notes}
        </div>
      )}
      <section className="rounded-card border border-subtle bg-surface p-4 shadow-card">
        <SectionHeader
          label="İki aşamalı değerlendirme"
          hint={`${draft.version} · ${new Date(draft.evaluated_at).toLocaleDateString("tr-TR")}`}
          action={
            <div className="flex items-center gap-1.5">
              {editing ? (
                <>
                  <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                    Vazgeç
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={!online || save.isPending}
                    onClick={() => save.mutate(draft)}
                  >
                    <Save size={13} /> Kaydet
                  </Button>
                </>
              ) : (
                <>
                  <Button size="sm" onClick={() => setEditing(true)}>
                    Düzenle
                  </Button>
                  <Button size="sm" disabled={!online || generate.isPending} onClick={() => generate.mutate()}>
                    <RefreshCw size={13} /> Yenile
                  </Button>
                </>
              )}
            </div>
          }
        />

        <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
          <div className="flex min-w-32 flex-col justify-center rounded-control bg-surface-sunken p-3 text-center">
            <span className="numeral text-display text-primary">{draft.score}</span>
            <span className="text-micro text-muted">100 üzerinden</span>
          </div>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={recommendationTone}>{recommendationLabel(draft.recommendation)}</Chip>
              {editing ? (
                <Select
                  value={draft.archetype ?? ""}
                  ariaLabel="Rol arketipi"
                  onChange={(value) =>
                    setDraft((current) =>
                      current ? { ...current, archetype: (value || null) as OpportunityArchetype | null } : current,
                    )
                  }
                >
                  <option value="">Belirgin arketip yok</option>
                  {ARCHETYPE_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {ARCHETYPE_LABELS[value]}
                    </option>
                  ))}
                </Select>
              ) : (
                <Chip>{draft.archetype ? ARCHETYPE_LABELS[draft.archetype] : "Belirgin arketip yok"}</Chip>
              )}
              <Chip>{draft.engine === "local_rules" ? "Tamamen yerel" : draft.engine}</Chip>
            </div>
            <p className="text-meta text-secondary">
              Pass 1 yalnızca ilanı okur. Pass 2,{" "}
              {draft.candidate_source === "document"
                ? `${draft.candidate_document_title ?? "yerel CV"} belgesindeki doğrulanabilir terimleri kullanır.`
                : "CV içeriği bulunamadığı için tanımlı yerel yetenek profilini kullanır."}
            </p>
          </div>
        </div>
      </section>

      <section
        className={cx(
          "rounded-card border p-4",
          draft.gate.hard_blocker ? "border-danger-border bg-danger-surface" : "border-subtle bg-surface",
        )}
      >
        <SectionHeader
          label="Konum & çalışma izni kapısı"
          hint={draft.gate.hard_blocker ? "Hard blocker" : "Engel yok"}
          action={draft.gate.hard_blocker ? <AlertOctagon size={15} className="text-danger" /> : undefined}
        />
        <div className="flex flex-wrap gap-1.5">
          <Chip>{draft.gate.job_country ?? "Konum belirsiz"}</Chip>
          <Chip tone={draft.gate.authorized_to_work === false ? "danger" : "neutral"}>
            {draft.gate.authorized_to_work === true
              ? "Çalışma izni var"
              : draft.gate.authorized_to_work === false
                ? "Çalışma izni yok"
                : "Çalışma izni belirsiz"}
          </Chip>
          <Chip tone={draft.gate.sponsorship_status === "no_sponsorship" ? "danger" : "neutral"}>
            {draft.gate.sponsorship_status === "sponsors"
              ? "Sponsorluk var"
              : draft.gate.sponsorship_status === "not_needed"
                ? "Sponsorluk gerekmiyor"
                : draft.gate.sponsorship_status === "no_sponsorship"
                  ? "Sponsorluk yok"
                  : "Sponsorluk belirtilmemiş"}
          </Chip>
          {draft.gate.geo_mismatch && <Chip tone="danger">Konum uyuşmazlığı</Chip>}
        </div>
        {draft.gate.reasons.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-meta text-secondary">
            {draft.gate.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-card border border-subtle bg-surface p-4">
        <SectionHeader label="Pass 1 · İlan gereksinimleri" hint={`${draft.requirements.length} gereksinim`} />
        <div className="divide-y divide-subtle">
          {draft.requirements.map((requirement) => (
            <div key={requirement.id} className="py-3 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center gap-2">
                <strong className="min-w-0 flex-1 text-body text-primary">{requirement.name}</strong>
                {editing ? (
                  <>
                    <Select
                      value={requirement.importance}
                      ariaLabel={`${requirement.name} önem seviyesi`}
                      onChange={(value) =>
                        patchRequirement(requirement.id, { importance: value as RequirementImportance })
                      }
                    >
                      {IMPORTANCE_OPTIONS.filter(
                        (value) => requirement.evidence !== "inferred" || !["critical", "high"].includes(value),
                      ).map((value) => (
                        <option key={value} value={value}>
                          {IMPORTANCE_LABELS[value]}
                        </option>
                      ))}
                    </Select>
                    <Select
                      value={requirement.evidence}
                      ariaLabel={`${requirement.name} kanıt türü`}
                      onChange={(value) => patchRequirement(requirement.id, { evidence: value as RequirementEvidence })}
                    >
                      {EVIDENCE_OPTIONS.map((value) => (
                        <option key={value} value={value}>
                          {EVIDENCE_LABELS[value]}
                        </option>
                      ))}
                    </Select>
                  </>
                ) : (
                  <>
                    <Chip tone={importanceTone(requirement.importance)}>
                      {IMPORTANCE_LABELS[requirement.importance]}
                    </Chip>
                    <Chip>{EVIDENCE_LABELS[requirement.evidence]}</Chip>
                  </>
                )}
              </div>
              {requirement.excerpt && <p className="mt-1.5 line-clamp-2 text-meta text-muted">{requirement.excerpt}</p>}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-card border border-subtle bg-surface p-4">
        <SectionHeader
          label="Pass 2 · Aday eşleşmesi"
          hint={draft.candidate_source === "document" ? draft.candidate_document_title : "yerel yetenek profili"}
        />
        <div className="space-y-3">
          {draft.matches.map((match) => (
            <div key={match.requirement_id} className="rounded-control border border-subtle bg-surface-sunken p-3">
              <div className="flex flex-wrap items-center gap-2">
                <strong className="min-w-0 flex-1 text-body text-primary">{match.requirement}</strong>
                {editing ? (
                  <Select
                    value={match.match}
                    ariaLabel={`${match.requirement} aday eşleşmesi`}
                    onChange={(value) => patchMatch(match.requirement_id, { match: value as CandidateMatch })}
                  >
                    {MATCH_OPTIONS.map((value) => (
                      <option key={value} value={value}>
                        {MATCH_LABELS[value]}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Chip tone={matchTone(match.match)}>{MATCH_LABELS[match.match]}</Chip>
                )}
              </div>
              <p className="mt-1.5 text-meta text-secondary">{match.evidence}</p>
              {editing ? (
                <div className="mt-2 space-y-2">
                  <Textarea
                    value={match.gap_mitigation ?? ""}
                    onChange={(value) => patchMatch(match.requirement_id, { gap_mitigation: value || null })}
                    rows={2}
                    placeholder="Gap telafisi…"
                  />
                  {stories.length > 0 && (
                    <div className="flex flex-wrap gap-x-3 gap-y-1">
                      {stories.map((story) => (
                        <Checkbox
                          key={story.id}
                          checked={(match.story_ids ?? []).includes(story.id)}
                          onChange={(checked) => toggleStory(match.requirement_id, story.id, checked)}
                          label={story.title}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  {match.gap_mitigation && <p className="mt-2 text-meta text-muted">Telafi: {match.gap_mitigation}</p>}
                  {(match.story_ids ?? []).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(match.story_ids ?? []).map((storyId) => (
                        <Chip key={storyId} tone="accent">
                          {stories.find((story) => story.id === storyId)?.title ?? "Bağlı STAR+R hikâyesi"}
                        </Chip>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-card border border-subtle bg-surface p-4">
        <SectionHeader label="Değerlendirme notu" />
        {editing ? (
          <Textarea
            value={draft.notes ?? ""}
            onChange={(notes) => setDraft((current) => (current ? { ...current, notes: notes || null } : current))}
            rows={4}
            placeholder="Kararı etkileyen kişisel notlar…"
          />
        ) : (
          <p className="whitespace-pre-wrap text-meta text-secondary">{draft.notes || "Henüz kişisel not yok."}</p>
        )}
      </section>
    </div>
  );
}

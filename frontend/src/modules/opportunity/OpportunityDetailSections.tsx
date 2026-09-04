import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, MailSearch, X } from "lucide-react";
import { api } from "@/core/api";
import { Button, Chip, Input, SectionHeader, Select, Textarea, cx, useToast } from "@/core/ui";
import type {
  Application,
  CareerStory,
  CoverLetterReview,
  Document,
  Interview,
  ReplyAnalysis,
  SalaryConsistency,
} from "@/core/types";

type Requirement = {
  id: string;
  name: string;
  status: string;
  required: boolean;
  document_entity_id: string | null;
};

/** Gereksinimler: belge baglama ve yeni gereksinim ekleme. */
export function RequirementsSection({ id, online, documents }: { id: string; online: boolean; documents: Document[] }) {
  const [requirement, setRequirement] = useState("");
  const { data: requirements = [] } = useQuery({
    queryKey: ["opportunity-requirements", id],
    queryFn: () => api.get<Requirement[]>(`/opportunities/${id}/requirements`),
  });
  const addRequirement = useMutation({
    mutationFn: () => api.post(`/opportunities/${id}/requirements`, { name: requirement.trim() }),
    onSuccess: () => {
      setRequirement("");
      invalidateAfter("opportunity.write");
    },
  });
  const bindDocument = useMutation({
    mutationFn: ({ requirementId, documentId }: { requirementId: string; documentId: string }) =>
      api.patch(`/requirements/${requirementId}/document`, { document_entity_id: documentId || null }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  return (
    <section>
      <SectionHeader
        label="Gereksinimler"
        hint={`${requirements.filter((r) => r.document_entity_id).length}/${requirements.length} hazır`}
      />
      {requirements.length === 0 ? (
        <p className="py-3 text-meta text-muted">Henüz gereksinim eklenmedi.</p>
      ) : (
        <ul className="mb-3 flex flex-col gap-2">
          {requirements.map((req) => (
            <li key={req.id} className="flex items-center gap-3">
              <span
                className={cx(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
                  req.document_entity_id ? "border-ok bg-ok text-canvas" : "border-strong bg-surface",
                )}
                aria-hidden
              >
                {req.document_entity_id && <Check size={12} />}
              </span>
              <span className="min-w-0 flex-1 truncate text-body">{req.name}</span>
              <Select
                value={req.document_entity_id ?? ""}
                disabled={!online}
                ariaLabel={`${req.name} için belge`}
                onChange={(v) => bindDocument.mutate({ requirementId: req.id, documentId: v })}
                className="w-48"
              >
                <option value="">belge eksik</option>
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title}
                  </option>
                ))}
              </Select>
            </li>
          ))}
        </ul>
      )}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (requirement.trim()) addRequirement.mutate();
        }}
      >
        <Input
          value={requirement}
          onChange={setRequirement}
          placeholder="CV, transkript, niyet mektubu…"
          ariaLabel="Yeni gereksinim"
          className="flex-1"
        />
        <Button type="submit" disabled={!online || !requirement.trim()}>
          Ekle
        </Button>
      </form>
    </section>
  );
}

/** Başvuru: ilk basvuru formu, guncelleme ve basvuru anindaki ilan ozeti. */
export function ApplicationSection({ id, online, documents }: { id: string; online: boolean; documents: Document[] }) {
  const [editingApp, setEditingApp] = useState(false);
  const [coverDraft, setCoverDraft] = useState("");
  const [cvDraft, setCvDraft] = useState("");
  const [salaryDraft, setSalaryDraft] = useState("");
  const [researchDraft, setResearchDraft] = useState("");
  const [appNoteDraft, setAppNoteDraft] = useState("");
  const [coverReview, setCoverReview] = useState<CoverLetterReview | null>(null);

  const apply = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(`/opportunities/${id}/apply`, body),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });
  const updateApp = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/opportunities/${id}/application`, body),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      setEditingApp(false);
    },
  });
  const reviewCover = useMutation({
    mutationFn: () => api.post<CoverLetterReview>("/career/cover-letter-review", { text: coverDraft.trim() }),
    onSuccess: setCoverReview,
  });
  const { data: stories = [] } = useQuery<CareerStory[]>({
    queryKey: ["career-stories"],
    queryFn: () => api.get<CareerStory[]>("/career/stories"),
  });
  const insertStory = (storyId: string) => {
    const story = stories.find((s) => s.id === storyId);
    if (!story) return;
    const snippet = `\n\n[${story.title}]\n${story.action}\n${story.result}`;
    setCoverDraft((prev) => (prev ? `${prev.trimEnd()}${snippet}` : `${story.action}\n${story.result}`));
    setCoverReview(null);
  };
  const { data: app, refetch: refetchApp } = useQuery({
    queryKey: ["application", id],
    queryFn: () => api.get<Application>(`/opportunities/${id}/application`).catch(() => null),
  });
  useEffect(() => {
    if (app) {
      setCoverDraft(app.cover_letter ?? "");
      setCvDraft(app.cv_document_id ?? "");
      setSalaryDraft(app.salary_expectation ?? "");
      setResearchDraft(app.company_research ?? "");
      setAppNoteDraft(app.note ?? "");
    }
  }, [app]);

  return (
    <section>
      <SectionHeader label="Başvuru" hint={app ? `cv: ${app.cv_title ?? "—"}` : "henüz yapılmadı"} />
      {!app && (
        <div className="space-y-2">
          <Select value={cvDraft} onChange={setCvDraft} ariaLabel="Kullanılan CV" className="w-full border-strong">
            <option value="">CV seç (varsa)</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
          </Select>
          <div className="flex items-center justify-between gap-2">
            <span className="text-meta text-muted">Niyet mektubu (Cover Letter)</span>
            {stories.length > 0 && (
              <Select value="" onChange={insertStory} ariaLabel="STAR Hikâyesi Ekle" className="max-w-48 text-micro">
                <option value="">+ STAR Hikâyesi Ekle</option>
                {stories.map((story) => (
                  <option key={story.id} value={story.id}>
                    {story.title}
                  </option>
                ))}
              </Select>
            )}
          </div>
          <Textarea
            value={coverDraft}
            onChange={(value) => {
              setCoverDraft(value);
              setCoverReview(null);
            }}
            rows={3}
            placeholder="Cover letter (niyet mektubu)…"
          />
          <Button
            size="sm"
            disabled={coverDraft.trim().length < 20 || reviewCover.isPending}
            onClick={() => reviewCover.mutate()}
          >
            Üslubu yerelde denetle
          </Button>
          {coverReview && <CoverLetterReviewCard review={coverReview} />}
          <Button
            variant="primary"
            disabled={!online}
            onClick={() => apply.mutate({ cv_document_id: cvDraft || null, cover_letter: coverDraft || null })}
          >
            Başvur
          </Button>
        </div>
      )}
      {app && !editingApp && (
        <div className="space-y-2 text-meta text-secondary">
          {app.cv_title && (
            <p>
              CV: <strong className="text-primary">{app.cv_title}</strong>
              {app.cv_modified_at ? " · " + new Date(app.cv_modified_at).toLocaleDateString("tr-TR") : ""}
            </p>
          )}
          {app.cover_letter && <p className="whitespace-pre-line text-secondary">{app.cover_letter}</p>}
          {app.salary_expectation && <p>Maaş beklentisi: {app.salary_expectation}</p>}
          {app.company_research && <p className="whitespace-pre-line">Araştırma: {app.company_research}</p>}
          {app.posting_snapshot && Object.keys(app.posting_snapshot).length > 0 && (
            <details className="rounded-control border border-subtle bg-surface px-3 py-2">
              <summary className="cursor-pointer text-meta text-muted">Başvuru anındaki ilan (snapshot)</summary>
              <dl className="mt-2 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-meta text-secondary">
                {[
                  ["Kurum", String(app.posting_snapshot.organization ?? "—")],
                  ["Lokasyon", String(app.posting_snapshot.location ?? "—")],
                  ["Ücret", String(app.posting_snapshot.compensation ?? "—")],
                ].map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="text-muted">{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => {
                setEditingApp(true);
                refetchApp();
              }}
            >
              Düzenle
            </Button>
          </div>
        </div>
      )}
      {app && editingApp && (
        <div className="space-y-2">
          <Select value={cvDraft} onChange={setCvDraft} ariaLabel="Kullanılan CV" className="w-full border-strong">
            <option value="">CV seç (varsa)</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
          </Select>
          <div className="flex items-center justify-between gap-2">
            <span className="text-meta text-muted">Niyet mektubu</span>
            {stories.length > 0 && (
              <Select value="" onChange={insertStory} ariaLabel="STAR Hikâyesi Ekle" className="max-w-48 text-micro">
                <option value="">+ STAR Hikâyesi Ekle</option>
                {stories.map((story) => (
                  <option key={story.id} value={story.id}>
                    {story.title}
                  </option>
                ))}
              </Select>
            )}
          </div>
          <Textarea
            value={coverDraft}
            onChange={(value) => {
              setCoverDraft(value);
              setCoverReview(null);
            }}
            rows={3}
            placeholder="Cover letter…"
          />
          <Button
            size="sm"
            disabled={coverDraft.trim().length < 20 || reviewCover.isPending}
            onClick={() => reviewCover.mutate()}
          >
            Üslubu yerelde denetle
          </Button>
          {coverReview && <CoverLetterReviewCard review={coverReview} />}
          <Input
            value={salaryDraft}
            onChange={setSalaryDraft}
            placeholder="Maaş beklentisi (örn. 3000 EUR)"
            className="w-full"
          />
          <Textarea value={researchDraft} onChange={setResearchDraft} rows={2} placeholder="Şirket araştırması…" />
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={!online}
              onClick={() =>
                updateApp.mutate({
                  cv_document_id: cvDraft || null,
                  cover_letter: coverDraft || null,
                  salary_expectation: salaryDraft || null,
                  company_research: researchDraft || null,
                })
              }
            >
              Kaydet
            </Button>
            <Button size="sm" onClick={() => setEditingApp(false)}>
              Vazgeç
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

function CoverLetterReviewCard({ review }: { review: CoverLetterReview }) {
  const tone = review.score >= 75 ? "ok" : review.score >= 50 ? "warn" : "danger";
  return (
    <div className="rounded-control border border-subtle bg-surface-sunken p-3 text-meta">
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone={tone}>Üslup skoru · {review.score}</Chip>
        <span className="text-muted">{review.matched_story_ids.length} STAR+R hikâyesiyle örtüşüyor</span>
      </div>
      {review.flags.length > 0 && <p className="mt-2 text-secondary">{review.flags.join(" · ")}</p>}
      {review.suggestions.length > 0 && <p className="mt-1 text-muted">Öneri: {review.suggestions.join(" ")}</p>}
    </div>
  );
}

/** Takip tarihi: blur'da kaydedilen tek alanli form. */
export function FollowUpSection({ id, followUpAt }: { id: string; followUpAt: string | null }) {
  const [followUpDraft, setFollowUpDraft] = useState("");
  // Takip tarihi: veri gelince alani doldur; duzenleme taslakta, blur'da kaydedilir.
  useEffect(() => {
    if (followUpAt) {
      setFollowUpDraft(new Date(followUpAt).toISOString().slice(0, 16));
    }
  }, [followUpAt]);
  const followUp = useMutation({
    mutationFn: (follow_up_at: string | null) => api.patch(`/opportunities/${id}`, { follow_up_at }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  return (
    <section>
      <SectionHeader label="Takip" hint={followUpAt ? new Date(followUpAt).toLocaleString("tr-TR") : "yok"} />
      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="datetime-local"
          value={followUpDraft}
          onChange={setFollowUpDraft}
          onBlur={(value) => value && followUp.mutate(new Date(value).toISOString())}
          ariaLabel="Takip tarihi"
        />
        {followUpAt && (
          <Button size="sm" onClick={() => followUp.mutate(null)}>
            Temizle
          </Button>
        )}
      </div>
    </section>
  );
}

/** Gelen e-posta metnini yerelde yorumlar; aksiyon ancak kullanici onayiyla uygulanir. */
const REPLY_STATUS_SOURCES: Record<string, string[]> = {
  applied: ["discovered", "considering", "preparing"],
  interview: ["discovered", "considering", "preparing", "applied"],
  rejected: ["discovered", "considering", "preparing", "applied", "interview", "offer"],
};

export function replySuggestionCanApply(analysis: ReplyAnalysis | null, status: string): boolean {
  if (!analysis || analysis.kind === "unknown") return false;
  const todoAllowed = Boolean(
    analysis.suggested_todo_title && !["accepted", "rejected", "withdrawn", "closed"].includes(status),
  );
  const statusAllowed = Boolean(
    analysis.suggested_status && REPLY_STATUS_SOURCES[analysis.suggested_status]?.includes(status),
  );
  return todoAllowed || statusAllowed;
}

export function ReplyProcessorSection({ id, status, online }: { id: string; status: string; online: boolean }) {
  const toast = useToast();
  const [expanded, setExpanded] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [analysis, setAnalysis] = useState<ReplyAnalysis | null>(null);

  const analyze = useMutation({
    mutationFn: () => api.post<ReplyAnalysis>(`/opportunities/${id}/reply-analysis`, { text: replyText.trim() }),
    onSuccess: setAnalysis,
  });

  const applySuggestion = useMutation({
    mutationFn: async () => {
      if (!analysis) return;
      if (analysis.suggested_todo_title) {
        await api.post(`/opportunities/${id}/todos`, { title: analysis.suggested_todo_title });
      }
      const target = analysis.suggested_status;
      if (!target || !REPLY_STATUS_SOURCES[target]?.includes(status)) return;
      if (target === "interview" && ["discovered", "considering", "preparing"].includes(status)) {
        await api.post(`/opportunities/${id}/transition`, {
          to: "applied",
          note: "Gelen yanıt sınıflandırıcısı: başvuru aşaması doğrulandı",
        });
      }
      await api.post(`/opportunities/${id}/transition`, {
        to: target,
        note: `Gelen yanıt: ${analysis.label}`,
        rejection_reason: target === "rejected" ? "işveren yanıtı" : undefined,
      });
    },
    onSuccess: () => {
      invalidateAfter("opportunity.write", "todo.write");
      toast.push("Önerilen işlem uygulandı", { tone: "ok" });
      setReplyText("");
      setAnalysis(null);
      setExpanded(false);
    },
  });

  const canApply = replySuggestionCanApply(analysis, status);

  return (
    <section>
      <SectionHeader
        label="Gelen yanıtı işle"
        hint="metin yalnızca bu cihazda analiz edilir"
        action={
          <Button size="sm" onClick={() => setExpanded((value) => !value)}>
            <MailSearch size={13} /> {expanded ? "Kapat" : "Yanıt yapıştır"}
          </Button>
        }
      />
      {expanded && (
        <div className="space-y-3">
          <Textarea
            value={replyText}
            onChange={(value) => {
              setReplyText(value);
              setAnalysis(null);
            }}
            rows={6}
            placeholder="İşverenden gelen e-posta veya mesaj metnini buraya yapıştır…"
            ariaLabel="İşveren yanıtı"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={!online || replyText.trim().length < 8 || analyze.isPending}
              onClick={() => analyze.mutate()}
            >
              Yerelde analiz et
            </Button>
            <span className="text-micro text-muted">Hiçbir e-posta hesabına bağlanılmaz.</span>
          </div>
          {analysis && (
            <div className="rounded-control border border-subtle bg-surface-sunken p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Chip
                  tone={analysis.kind === "rejection" ? "danger" : analysis.kind === "unknown" ? "neutral" : "accent"}
                >
                  {analysis.label}
                </Chip>
                <span className="text-micro tabular-nums text-muted">
                  güven %{Math.round(analysis.confidence * 100)}
                </span>
              </div>
              <p className="mt-2 text-meta text-secondary">{analysis.summary}</p>
              {analysis.evidence.length > 0 && (
                <p className="mt-1 text-micro text-muted">Sinyaller: {analysis.evidence.join(" · ")}</p>
              )}
              {canApply && (
                <Button
                  className="mt-3"
                  variant="primary"
                  size="sm"
                  disabled={applySuggestion.isPending}
                  onClick={() => applySuggestion.mutate()}
                >
                  {analysis.suggested_todo_title
                    ? "Teknik ödevi görevlere ekle"
                    : analysis.suggested_status === "interview"
                      ? "Mülakat aşamasına taşı"
                      : analysis.suggested_status === "rejected"
                        ? "Reddedildi olarak işle"
                        : "Başvuruldu olarak işle"}
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/** Görüşmeler: liste ve ekle/sil. */
export function InterviewsSection({ id, online }: { id: string; online: boolean }) {
  const [interviewDraft, setInterviewDraft] = useState({
    stage: "",
    mode: "video",
    scheduled_at: "",
    notes: "",
    salary_stated: "",
  });
  const { data: interviews = [] } = useQuery({
    queryKey: ["interviews", id],
    queryFn: () => api.get<Interview[]>(`/opportunities/${id}/interviews`),
  });
  const { data: salary } = useQuery({
    queryKey: ["salary-consistency", id],
    queryFn: () => api.get<SalaryConsistency>(`/opportunities/${id}/salary-consistency`),
  });
  const addInterview = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(`/opportunities/${id}/interviews`, body),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      setInterviewDraft({ stage: "", mode: "video", scheduled_at: "", notes: "", salary_stated: "" });
    },
  });
  const removeInterview = useMutation({
    mutationFn: (interviewId: string) => api.del(`/interviews/${interviewId}`),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  return (
    <section>
      <SectionHeader label="Görüşmeler" hint={`${interviews.length} kayıt`} />
      {interviews.length > 0 && (
        <ul className="mb-3 space-y-1.5">
          {interviews.map((iv) => (
            <li
              key={iv.id}
              className="flex items-center gap-2 rounded-control border border-subtle px-3 py-2 text-meta"
            >
              <span className="min-w-0 flex-1">
                <strong className="text-primary">{iv.stage}</strong>
                <span className="ml-2 text-muted">
                  {iv.mode}
                  {iv.scheduled_at ? " · " + new Date(iv.scheduled_at).toLocaleString("tr-TR") : ""}
                </span>
                {iv.notes && <span className="block truncate text-muted">{iv.notes}</span>}
                {iv.salary_stated && <span className="block text-muted">Sözlü ücret: {iv.salary_stated}</span>}
              </span>
              <button
                type="button"
                onClick={() => removeInterview.mutate(iv.id)}
                title="Görüşmeyi sil"
                className="text-muted transition hover:text-danger"
              >
                <X size={13} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {salary?.inconsistent && (
        <div className="mb-3 rounded-control border border-warn-border bg-warn-surface p-3 text-meta text-secondary">
          <strong className="text-warn">Ücret tutarlılığı uyarısı</strong>
          <p className="mt-1">{salary.warning}</p>
        </div>
      )}
      <div className="grid gap-2 sm:grid-cols-[1fr_7rem_auto]">
        <Input
          value={interviewDraft.stage}
          onChange={(v) => setInterviewDraft({ ...interviewDraft, stage: v })}
          placeholder="Aşama (örn. teknik, HR…)"
        />
        <Select
          value={interviewDraft.mode}
          onChange={(v) => setInterviewDraft({ ...interviewDraft, mode: v })}
          ariaLabel="Görüşme tipi"
        >
          <option value="video">Video</option>
          <option value="telefon">Telefon</option>
          <option value="yuz_yuze">Yüz yüze</option>
        </Select>
        <Button
          size="sm"
          disabled={!online || !interviewDraft.stage.trim()}
          onClick={() =>
            addInterview.mutate({
              stage: interviewDraft.stage.trim(),
              mode: interviewDraft.mode,
              scheduled_at: interviewDraft.scheduled_at || null,
              notes: interviewDraft.notes || null,
              salary_stated: interviewDraft.salary_stated || null,
            })
          }
        >
          Ekle
        </Button>
      </div>
      <Input
        value={interviewDraft.salary_stated}
        onChange={(salary_stated) => setInterviewDraft({ ...interviewDraft, salary_stated })}
        placeholder="Bu turda söylenen ücret (örn. €60k–€70k)"
        ariaLabel="Sözlü ücret beyanı"
        className="mt-2 w-full"
      />
    </section>
  );
}

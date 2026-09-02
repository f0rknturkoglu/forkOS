import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import { api } from "@/core/api";
import { Button, Input, SectionHeader, Select, Textarea, cx } from "@/core/ui";
import type { Application, Document, Interview } from "@/core/types";

type Requirement = {
  id: string;
  name: string;
  status: string;
  required: boolean;
  document_entity_id: string | null;
};

/** Gereksinimler: belge baglama ve yeni gereksinim ekleme. */
export function RequirementsSection({
  id,
  online,
  documents,
}: {
  id: string;
  online: boolean;
  documents: Document[];
}) {
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
export function ApplicationSection({
  id,
  online,
  documents,
}: {
  id: string;
  online: boolean;
  documents: Document[];
}) {
  const [editingApp, setEditingApp] = useState(false);
  const [coverDraft, setCoverDraft] = useState("");
  const [cvDraft, setCvDraft] = useState("");
  const [salaryDraft, setSalaryDraft] = useState("");
  const [researchDraft, setResearchDraft] = useState("");
  const [appNoteDraft, setAppNoteDraft] = useState("");

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
          <Textarea value={coverDraft} onChange={setCoverDraft} rows={3} placeholder="Cover letter (niyet mektubu)…" />
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
          <Textarea value={coverDraft} onChange={setCoverDraft} rows={3} placeholder="Cover letter…" />
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

/** Görüşmeler: liste ve ekle/sil. */
export function InterviewsSection({ id, online }: { id: string; online: boolean }) {
  const [interviewDraft, setInterviewDraft] = useState({ stage: "", mode: "video", scheduled_at: "", notes: "" });
  const { data: interviews = [] } = useQuery({
    queryKey: ["interviews", id],
    queryFn: () => api.get<Interview[]>(`/opportunities/${id}/interviews`),
  });
  const addInterview = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post(`/opportunities/${id}/interviews`, body),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      setInterviewDraft({ stage: "", mode: "video", scheduled_at: "", notes: "" });
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
            <li key={iv.id} className="flex items-center gap-2 rounded-control border border-subtle px-3 py-2 text-meta">
              <span className="min-w-0 flex-1">
                <strong className="text-primary">{iv.stage}</strong>
                <span className="ml-2 text-muted">
                  {iv.mode}
                  {iv.scheduled_at ? " · " + new Date(iv.scheduled_at).toLocaleString("tr-TR") : ""}
                </span>
                {iv.notes && <span className="block truncate text-muted">{iv.notes}</span>}
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
            })
          }
        >
          Ekle
        </Button>
      </div>
    </section>
  );
}

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ExternalLink, X } from "lucide-react";
import { api } from "@/core/api";
import { Badge, Button, Empty, Input, SectionHeader, cx, relativeTime } from "@/core/ui";
import type { Application, ApplicationHistoryRow, Document, Interview, Opportunity } from "@/core/types";
import { useInvalidate, useOnline } from "@/lib/hooks";
import {
  SCORE_TONE, STATUSES, STATUS_TONES,
  daysLeft, kindLabel, scoreBand, sourceLabel, statusLabel,
} from "./labels";
import type { ScoreBand } from "./labels";


type Requirement = {
  id: string; name: string; status: string; required: boolean; document_entity_id: string | null;
};

/** Sag taraftan acilan fırsat detayı: durum, skor ve gereksinimler. */
export function OpportunityDetail({ id, close }: { id: string; close: () => void }) {
  const online = useOnline();
  const invalidate = useInvalidate();
  const [requirement, setRequirement] = useState("");
  const [editingApp, setEditingApp] = useState(false);
  const [coverDraft, setCoverDraft] = useState("");
  const [cvDraft, setCvDraft] = useState("");
  const [salaryDraft, setSalaryDraft] = useState("");
  const [researchDraft, setResearchDraft] = useState("");
  const [appNoteDraft, setAppNoteDraft] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [rejectionDraft, setRejectionDraft] = useState("");
  const [interviewDraft, setInterviewDraft] = useState({ stage: "", mode: "video", scheduled_at: "", notes: "" });

  const { data: item } = useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => api.get<Opportunity>(`/opportunities/${id}`),
  });
  const { data: requirements = [] } = useQuery({
    queryKey: ["opportunity-requirements", id],
    queryFn: () => api.get<Requirement[]>(`/opportunities/${id}/requirements`),
  });
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });

  const patch = useMutation({
    mutationFn: (status: string) => api.patch(`/opportunities/${id}`, { status }),
    onSuccess: () => invalidate("opportunity", "opportunities", "activity"),
  });
  const addRequirement = useMutation({
    mutationFn: () => api.post(`/opportunities/${id}/requirements`, { name: requirement.trim() }),
    onSuccess: () => { setRequirement(""); invalidate("opportunity-requirements"); },
  });
  const bindDocument = useMutation({
    mutationFn: ({ requirementId, documentId }: { requirementId: string; documentId: string }) =>
      api.patch(`/requirements/${requirementId}/document`, { document_entity_id: documentId || null }),
    onSuccess: () => invalidate("opportunity-requirements", "activity"),
  });

  const transition = useMutation({
    mutationFn: ({ to, note, rejection_reason }: { to: string; note?: string; rejection_reason?: string }) =>
      api.post("/" + "opportunities/" + id + "/transition", { to, note, rejection_reason }),
    onSuccess: () => invalidate("opportunity", "opportunities", "activity"),
    onError: (error: Error) => window.alert("Geçiş başarısız: " + error.message),
  });
  const apply = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/" + "opportunities/" + id + "/apply", body),
    onSuccess: () => invalidate("opportunity", "opportunities", "activity", "applications-funnel"),
  });
  const updateApp = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put("/" + "opportunities/" + id + "/application", body),
    onSuccess: () => { invalidate("application"); setEditingApp(false); },
  });
  const followUp = useMutation({
    mutationFn: (follow_up_at: string | null) => api.patch("/" + "opportunities/" + id, { follow_up_at }),
    onSuccess: () => invalidate("opportunity"),
  });
  const addInterview = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/" + "opportunities/" + id + "/interviews", body),
    onSuccess: () => {
      invalidate("interviews", "activity");
      setInterviewDraft({ stage: "", mode: "video", scheduled_at: "", notes: "" });
    },
  });
  const removeInterview = useMutation({
    mutationFn: (interviewId: string) => api.del("/interviews/" + interviewId),
    onSuccess: () => invalidate("interviews"),
  });

  const { data: app, refetch: refetchApp } = useQuery({
    queryKey: ["application", id],
    queryFn: () => api.get<Application>("/" + "opportunities/" + id + "/application").catch(() => null),
  });
  const { data: history = [] } = useQuery({
    queryKey: ["application-history", id],
    queryFn: () => api.get<ApplicationHistoryRow[]>("/" + "opportunities/" + id + "/history"),
  });
  const { data: interviews = [] } = useQuery({
    queryKey: ["interviews", id],
    queryFn: () => api.get<Interview[]>("/" + "opportunities/" + id + "/interviews"),
  });
  const { data: rejectionOptions = [] } = useQuery({
    queryKey: ["rejection-reasons"],
    queryFn: () => api.get<string[]>("/applications/rejection-reasons"),
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

  // Esc kapatsin; cekmece odak tuzagi degil ama kacis yolu olmali.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [close]);

  const left = daysLeft(item?.deadline_at ?? null);
  const band = scoreBand(item?.score ?? null);

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-[rgb(26_24_21/0.28)]"
      onClick={close}
      role="presentation"
    >
      <aside
        role="dialog"
        aria-label={item?.title ?? "Fırsat"}
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-subtle bg-canvas"
      >
        {/* ── Başlık ── */}
        <header className="sticky top-0 z-10 border-b border-subtle bg-canvas px-6 py-5">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge>{item ? kindLabel(item.kind) : "…"}</Badge>
                {item && (
                  <Badge tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Badge>
                )}
                {band && (
                  <Badge tone={SCORE_TONE[band]}>
                    {band === "killed"
                      ? "elendi"
                      : `${Math.round(item!.score as number)} puan`}
                  </Badge>
                )}
              </div>
              <h2 className="font-serif text-title leading-snug text-primary">
                {item?.title ?? "Yükleniyor…"}
              </h2>
              <p className="mt-1 text-meta text-muted">
                {[item?.organization, item?.location, item?.remote].filter(Boolean).join(" · ") || "—"}
              </p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Kapat"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary"
            >
              <X size={15} />
            </button>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {!item?.trashed_at && (
              <select
                value={item?.status ?? "discovered"}
                disabled={!online || !item}
                aria-label="Durum"
                onChange={(e) => {
                  if (e.target.value === "rejected") { setRejecting(true); return; }
                  if (e.target.value !== item?.status) transition.mutate({ to: e.target.value });
                }}
                className="h-control rounded-control border border-strong bg-surface px-3 text-meta text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50"
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>{statusLabel(status)}</option>
                ))}
              </select>
            )}
            {item?.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="flex h-control items-center gap-2 rounded-control border border-subtle bg-surface px-3 text-meta text-primary transition hover:bg-surface-hover"
              >
                <ExternalLink size={14} /> İlanı aç
              </a>
            )}
            {left !== null && (
              <span className={cx("text-meta", left <= 7 ? "text-warn" : "text-muted")}>
                {left < 0 ? `${Math.abs(left)} gün önce doldu` : `Son tarihe ${left} gün`}
              </span>
            )}
          </div>
        </header>

        <div className="flex flex-col gap-7 px-6 py-6">
          {/* ── Kaynak künyesi ── */}
          <section>
            <SectionHeader label="Künye" />
            <dl className="grid grid-cols-[7rem_1fr] gap-x-4 gap-y-2 text-meta">
              {[
                ["Kaynak", item ? sourceLabel(item.source) : "—"],
                ["Bulunma", item ? new Date(item.found_at).toLocaleString("tr-TR") : "—"],
                ["Ücret", item?.compensation ?? "—"],
              ].map(([label, value]) => (
                <div key={label} className="contents">
                  <dt className="text-muted">{label}</dt>
                  <dd className="text-secondary">{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* ── Uyum puanı ── */}
          {item?.score !== null && item?.score !== undefined && (
            <section>
              <SectionHeader
                label="Uyum puanı"
                hint={band ? scoreBandLabel(band) : undefined}
              />

              <div className="flex items-baseline gap-3">
                <span className="numeral text-[38px] leading-none text-primary">
                  {Math.round(item.score)}
                </span>
                <span className="text-meta text-muted">/ 100</span>
                <span className="ml-auto h-1.5 w-40 overflow-hidden rounded-full bg-surface-sunken">
                  <span
                    className="block h-full rounded-full bg-accent"
                    style={{ width: `${Math.max(0, Math.min(100, item.score))}%` }}
                  />
                </span>
              </div>
            </section>
          )}

          {/* ── Gereksinimler ── */}
          <section>
            <SectionHeader label="Gereksinimler" hint={`${requirements.filter((r) => r.document_entity_id).length}/${requirements.length} hazır`} />
            {requirements.length === 0 ? (
              <p className="py-3 text-meta text-muted">Henüz gereksinim eklenmedi.</p>
            ) : (
              <ul className="mb-3 flex flex-col gap-2">
                {requirements.map((req) => (
                  <li key={req.id} className="flex items-center gap-3">
                    <span
                      className={cx(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
                        req.document_entity_id
                          ? "border-ok bg-ok text-canvas"
                          : "border-strong bg-surface",
                      )}
                      aria-hidden
                    >
                      {req.document_entity_id && <Check size={12} />}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-body">{req.name}</span>
                    <select
                      value={req.document_entity_id ?? ""}
                      disabled={!online}
                      aria-label={`${req.name} için belge`}
                      onChange={(e) => bindDocument.mutate({ requirementId: req.id, documentId: e.target.value })}
                      className="h-8 w-48 rounded-control border border-subtle bg-surface px-2 text-meta text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent"
                    >
                      <option value="">belge eksik</option>
                      {documents.map((doc) => (
                        <option key={doc.id} value={doc.id}>{doc.title}</option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
            )}
            <form
              className="flex gap-2"
              onSubmit={(e) => { e.preventDefault(); if (requirement.trim()) addRequirement.mutate(); }}
            >
              <Input
                value={requirement}
                onChange={setRequirement}
                placeholder="CV, transkript, niyet mektubu…"
                ariaLabel="Yeni gereksinim"
                className="flex-1"
              />
              <Button type="submit" disabled={!online || !requirement.trim()}>Ekle</Button>
            </form>
          </section>

          {/* ── Red nedeni secimi (rejected) ── */}
          {rejecting && (
            <section>
              <SectionHeader label="Red nedeni" />
              <div className="flex flex-wrap gap-1.5">
                {rejectionOptions.map((reason) => (
                  <button
                    key={reason}
                    type="button"
                    onClick={() => setRejectionDraft(reason)}
                    className={rejectionDraft === reason
                      ? "h-7 rounded-control border border-accent bg-accent-surface px-2.5 text-meta font-medium text-accent"
                      : "h-7 rounded-control border border-subtle px-2.5 text-meta text-secondary hover:bg-surface-hover"
                    }
                  >
                    {reason}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Input value={rejectionDraft} onChange={setRejectionDraft} placeholder="Özel neden…" ariaLabel="Red nedeni" className="flex-1" />
                <Button variant="danger" disabled={!rejectionDraft.trim()}
                  onClick={() => { transition.mutate({ to: "rejected", rejection_reason: rejectionDraft.trim() }); setRejecting(false); }}>
                  Reddet
                </Button>
                <Button onClick={() => setRejecting(false)}>Vazgeç</Button>
              </div>
            </section>
          )}
          {item?.status === "rejected" && item.rejection_reason && (
            <section>
              <SectionHeader label="Red nedeni" />
              <div className="flex items-center gap-2 rounded-control border border-danger-border bg-danger-surface px-3 py-2 text-meta text-danger">
                {item.rejection_reason}
              </div>
            </section>
          )}

          {/* ── Başvuru ── */}
          <section>
            <SectionHeader label="Başvuru" hint={app ? `cv: ${app.cv_title ?? "—"}` : "henüz yapılmadı"} />
            {!app && (
              <div className="space-y-2">
                <select
                  value={cvDraft}
                  onChange={(e) => setCvDraft(e.target.value)}
                  aria-label="Kullanılan CV"
                  className="h-control w-full rounded-control border border-strong bg-surface px-3 text-meta text-primary outline-none focus:border-accent"
                >
                  <option value="">CV seç (varsa)</option>
                  {documents.map((doc) => (<option key={doc.id} value={doc.id}>{doc.title}</option>))}
                </select>
                <textarea
                  value={coverDraft}
                  onChange={(e) => setCoverDraft(e.target.value)}
                  rows={3}
                  placeholder="Cover letter (niyet mektubu)…"
                  className="w-full resize-y rounded-control border border-subtle bg-surface p-2 text-meta text-primary outline-none"
                />
                <Button variant="primary" disabled={!online}
                  onClick={() => apply.mutate({ cv_document_id: cvDraft || null, cover_letter: coverDraft || null })}>
                  Başvur
                </Button>
              </div>
            )}
            {app && !editingApp && (
              <div className="space-y-2 text-meta text-secondary">
                {app.cv_title && <p>CV: <strong className="text-primary">{app.cv_title}</strong>{app.cv_modified_at ? " · " + new Date(app.cv_modified_at).toLocaleDateString("tr-TR") : ""}</p>}
                {app.cover_letter && <p className="whitespace-pre-line text-secondary">{app.cover_letter}</p>}
                {app.salary_expectation && <p>Maaş beklentisi: {app.salary_expectation}</p>}
                {app.company_research && <p className="whitespace-pre-line">Araştırma: {app.company_research}</p>}
                {app.posting_snapshot && Object.keys(app.posting_snapshot).length > 0 && (
                  <details className="rounded-control border border-subtle bg-surface px-3 py-2">
                    <summary className="cursor-pointer text-meta text-muted">Başvuru anındaki ilan (snapshot)</summary>
                    <dl className="mt-2 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-meta text-secondary">
                      {[["Kurum", String(app.posting_snapshot.organization ?? "—")],["Lokasyon", String(app.posting_snapshot.location ?? "—")],["Ücret", String(app.posting_snapshot.compensation ?? "—")]].map(([k, v]) => (<div key={k} className="contents"><dt className="text-muted">{k}</dt><dd>{v}</dd></div>))}
                    </dl>
                  </details>
                )}
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => { setEditingApp(true); refetchApp(); }}>Düzenle</Button>
                </div>
              </div>
            )}
            {app && editingApp && (
              <div className="space-y-2">
                <select value={cvDraft} onChange={(e) => setCvDraft(e.target.value)} aria-label="Kullanılan CV" className="h-control w-full rounded-control border border-strong bg-surface px-3 text-meta text-primary outline-none focus:border-accent">
                  <option value="">CV seç (varsa)</option>
                  {documents.map((doc) => (<option key={doc.id} value={doc.id}>{doc.title}</option>))}
                </select>
                <textarea value={coverDraft} onChange={(e) => setCoverDraft(e.target.value)} rows={3} placeholder="Cover letter…" className="w-full resize-y rounded-control border border-subtle bg-surface p-2 text-meta text-primary outline-none" />
                <input value={salaryDraft} onChange={(e) => setSalaryDraft(e.target.value)} placeholder="Maaş beklentisi (örn. 3000 EUR)" className="h-control w-full rounded-control border border-subtle bg-surface px-3 text-meta text-primary outline-none" />
                <textarea value={researchDraft} onChange={(e) => setResearchDraft(e.target.value)} rows={2} placeholder="Şirket araştırması…" className="w-full resize-y rounded-control border border-subtle bg-surface p-2 text-meta text-primary outline-none" />
                <div className="flex gap-2">
                  <Button variant="primary" size="sm" disabled={!online}
                    onClick={() => updateApp.mutate({ cv_document_id: cvDraft || null, cover_letter: coverDraft || null, salary_expectation: salaryDraft || null, company_research: researchDraft || null })}>
                    Kaydet
                  </Button>
                  <Button size="sm" onClick={() => setEditingApp(false)}>Vazgeç</Button>
                </div>
              </div>
            )}
          </section>

          {/* ── Takip tarihi ── */}
          <section>
            <SectionHeader label="Takip" hint={item?.follow_up_at ? new Date(item.follow_up_at).toLocaleString("tr-TR") : "yok"} />
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="datetime-local"
                defaultValue={item?.follow_up_at ? new Date(item.follow_up_at).toISOString().slice(0, 16) : ""}
                onBlur={(e) => e.target.value && followUp.mutate(new Date(e.target.value).toISOString())}
                aria-label="Takip tarihi"
                className="h-control rounded-control border border-subtle bg-surface px-3 text-meta text-primary outline-none"
              />
              {item?.follow_up_at && <Button size="sm" onClick={() => followUp.mutate(null)}>Temizle</Button>}
            </div>
          </section>

          {/* ── Görüşmeler ── */}
          <section>
            <SectionHeader label="Görüşmeler" hint={`${interviews.length} kayıt`} />
            {interviews.length > 0 && (
              <ul className="mb-3 space-y-1.5">
                {interviews.map((iv) => (
                  <li key={iv.id} className="flex items-center gap-2 rounded-control border border-subtle px-3 py-2 text-meta">
                    <span className="min-w-0 flex-1">
                      <strong className="text-primary">{iv.stage}</strong>
                      <span className="ml-2 text-muted">{iv.mode}{iv.scheduled_at ? " · " + new Date(iv.scheduled_at).toLocaleString("tr-TR") : ""}</span>
                      {iv.notes && <span className="block truncate text-muted">{iv.notes}</span>}
                    </span>
                    <button type="button" onClick={() => removeInterview.mutate(iv.id)} title="Görüşmeyi sil" className="text-muted transition hover:text-danger"><X size={13} /></button>
                  </li>
                ))}
              </ul>
            )}
            <div className="grid gap-2 sm:grid-cols-[1fr_7rem_auto]">
              <input value={interviewDraft.stage} onChange={(e) => setInterviewDraft({ ...interviewDraft, stage: e.target.value })} placeholder="Aşama (örn. teknik, HR…)" className="h-control rounded-control border border-subtle bg-surface px-3 text-meta text-primary outline-none" />
              <select value={interviewDraft.mode} onChange={(e) => setInterviewDraft({ ...interviewDraft, mode: e.target.value })} className="h-control rounded-control border border-subtle bg-surface px-2 text-meta text-primary outline-none" aria-label="Görüşme tipi">
                <option value="video">Video</option>
                <option value="telefon">Telefon</option>
                <option value="yuz_yuze">Yüz yüze</option>
              </select>
              <Button size="sm" disabled={!online || !interviewDraft.stage.trim()}
                onClick={() => addInterview.mutate({ stage: interviewDraft.stage.trim(), mode: interviewDraft.mode, scheduled_at: interviewDraft.scheduled_at || null, notes: interviewDraft.notes || null })}>
                Ekle
              </Button>
            </div>
          </section>

          {/* ── Durum geçmişi ── */}
          <section>
            <SectionHeader label="Geçmiş" hint={`${history.length} değişiklik`} />
            {history.length === 0 ? (<p className="text-meta text-muted">Henüz geçiş yok.</p>) : (
              <ol className="space-y-1.5">
                {history.map((row) => (
                  <li key={row.id} className="flex items-center gap-2 text-meta">
                    <span className="w-16 shrink-0 text-muted">{statusLabel(row.from_status ?? "—")}</span>
                    <span className="text-accent">→</span>
                    <span className="font-medium text-primary">{statusLabel(row.to_status)}</span>
                    <span className="ml-auto shrink-0 text-muted">{relativeTime(row.at)}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {item?.notes && (
            <section>
              <SectionHeader label="Not" />
              <p className="whitespace-pre-line text-body text-secondary">{item.notes}</p>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}

/* Skor bandi -> tek kelime etiket (renk karttaki gibi gorselde). */
function scoreBandLabel(band: ScoreBand): string {
  switch (band) {
    case "killed": return "elendi";
    case "strong": return "güçlü";
    case "fair": return "orta";
    default: return "zayıf";
  }
}
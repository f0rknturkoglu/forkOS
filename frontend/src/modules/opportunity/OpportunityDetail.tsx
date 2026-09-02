import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bookmark, Check, ExternalLink, FileText, X } from "lucide-react";
import { api } from "@/core/api";
import { navigate } from "@/app/router";
import { RelatedPanel } from "@/core/RelatedPanel";
import { Button, Chip, Input, SectionHeader, Select, cx, relativeTime, useToast } from "@/core/ui";
import type { ApplicationHistoryRow, Document, Opportunity } from "@/core/types";
import { planDayForToday } from "@/core/tasks";
import type { Todo } from "@/core/types";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { useOnline } from "@/lib/hooks";
import { SCORE_TONE, STATUSES, STATUS_TONES, daysLeft, kindLabel, scoreBand, statusLabel } from "./labels";
import { sourceLabel } from "@/core/labels";
import type { ScoreBand } from "./labels";
import { ApplicationSection, FollowUpSection, InterviewsSection, RequirementsSection } from "./OpportunityDetailSections";

/** Sag taraftan acilan fırsat detayı: durum, skor ve gereksinimler. */
export function OpportunityDetail({ id, close }: { id: string; close: () => void }) {
  const online = useOnline();
  const toast = useToast();
  const [rejecting, setRejecting] = useState(false);
  const [rejectionDraft, setRejectionDraft] = useState("");
  const [stepTitle, setStepTitle] = useState("");
  const { save } = useSaveToLibrary();
  const saveItem = () => {
    if (!item?.url) return;
    void save({ url: item.url, title: item.title, collection: "reference", entity_id: item.id });
  };

  const { data: item } = useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => api.get<Opportunity>(`/opportunities/${id}`),
  });
  const { data: documents = [] } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.get<Document[]>("/documents"),
  });
  const { data: steps = [] } = useQuery({
    queryKey: ["opportunity", id, "todos"],
    queryFn: () => api.get<Todo[]>(`/opportunities/${id}/todos`),
  });
  const { data: researchNotes = [] } = useQuery({
    queryKey: ["opportunity-notes", id],
    queryFn: () => api.get<Array<{ id: string; title: string }>>(`/opportunities/${id}/notes`),
  });

  const createResearchNote = useMutation({
    mutationFn: () => api.post<{ id: string; title: string }>(`/opportunities/${id}/research-note`),
    onSuccess: (note) => {
      invalidateAfter("note.write", "opportunity.write");
      toast.push("Şirket araştırma notu açıldı", { tone: "ok" });
      navigate(`/notes?focus=${note.id}`);
      close();
    },
  });
  const addStep = useMutation({
    mutationFn: () =>
      api.post(`/opportunities/${id}/todos`, {
        title: stepTitle.trim(),
        plan_day: planDayForToday(),
      }),
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

  const transition = useMutation({
    mutationFn: ({ to, note, rejection_reason }: { to: string; note?: string; rejection_reason?: string }) =>
      api.post(`/opportunities/${id}/transition`, { to, note, rejection_reason }),
    onSuccess: () => invalidateAfter("opportunity.write"),
  });

  const { data: history = [] } = useQuery({
    queryKey: ["application-history", id],
    queryFn: () => api.get<ApplicationHistoryRow[]>(`/opportunities/${id}/history`),
  });
  const { data: rejectionOptions = [] } = useQuery({
    queryKey: ["rejection-reasons"],
    queryFn: () => api.get<string[]>("/applications/rejection-reasons"),
  });

  // Esc kapatsin; cekmece odak tuzagi degil ama kacis yolu olmali.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [close]);

  const left = daysLeft(item?.deadline_at ?? null);
  const band = scoreBand(item?.score ?? null);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-canvas/60" onClick={close} role="presentation">
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
                <Chip>{item ? kindLabel(item.kind) : "…"}</Chip>
                {item && <Chip tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Chip>}
                {band && (
                  <Chip tone={SCORE_TONE[band]}>
                    {band === "killed" ? "elendi" : `${Math.round(item!.score as number)} puan`}
                  </Chip>
                )}
                {item?.skill_match && (
                  <Chip tone="ok">
                    %{Math.round(item.skill_match.match_ratio * 100)} Uyum
                  </Chip>
                )}
              </div>
              <h2 className="font-serif text-title leading-snug text-primary">{item?.title ?? "Yükleniyor…"}</h2>
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
              <Select
                value={item?.status ?? "discovered"}
                disabled={!online || !item}
                ariaLabel="Durum"
                onChange={(value) => {
                  if (value === "rejected") {
                    setRejecting(true);
                    return;
                  }
                  if (value !== item?.status) transition.mutate({ to: value });
                }}
                className="border-strong"
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {statusLabel(status)}
                  </option>
                ))}
              </Select>
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
            {item?.url && (
              <Button variant="primary" size="sm" disabled={!online} title="Kütüphaneye kaydet" onClick={saveItem}>
                <Bookmark size={14} /> Kaydet
              </Button>
            )}
            <Button
              variant="secondary"
              size="sm"
              disabled={!online || createResearchNote.isPending}
              title="Şirket araştırma ve mülakat notu"
              onClick={() => createResearchNote.mutate()}
            >
              <FileText size={14} /> {researchNotes.length > 0 ? "Şirket Notu (1)" : "Şirket Notu"}
            </Button>
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
              <SectionHeader label="Uyum puanı" hint={band ? scoreBandLabel(band) : undefined} />

              <div className="flex items-baseline gap-3">
                <span className="numeral text-display-lg leading-none text-primary">{Math.round(item.score)}</span>
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

          <RequirementsSection id={id} online={online} documents={documents} />

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
                    className={
                      rejectionDraft === reason
                        ? "h-7 rounded-control border border-accent bg-accent-surface px-2.5 text-meta font-medium text-accent"
                        : "h-7 rounded-control border border-subtle px-2.5 text-meta text-secondary hover:bg-surface-hover"
                    }
                  >
                    {reason}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Input
                  value={rejectionDraft}
                  onChange={setRejectionDraft}
                  placeholder="Özel neden…"
                  ariaLabel="Red nedeni"
                  className="flex-1"
                />
                <Button
                  variant="danger"
                  disabled={!rejectionDraft.trim()}
                  onClick={() => {
                    transition.mutate({ to: "rejected", rejection_reason: rejectionDraft.trim() });
                    setRejecting(false);
                  }}
                >
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

          <ApplicationSection id={id} online={online} documents={documents} />

          {/* ── Yetenek ve Beceri Uyumu ── */}
          {item?.skill_match && (
            <section className="rounded-panel border border-subtle bg-surface-sunken/40 p-3.5">
              <SectionHeader
                label="Beceri ve Teknoloji Uyumu"
                hint={`%${Math.round(item.skill_match.match_ratio * 100)} eşleşme`}
              />
              <div className="mt-2.5 space-y-2.5">
                {item.skill_match.matched.length > 0 && (
                  <div>
                    <span className="mb-1.5 block text-micro font-medium text-secondary">
                      Eşleşen Yetenekler ({item.skill_match.matched.length}):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {item.skill_match.matched.map((s) => (
                        <Chip key={s} tone="ok">
                          ✓ {s}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}
                {item.skill_match.missing.length > 0 && (
                  <div>
                    <span className="mb-1.5 block text-micro font-medium text-muted">
                      İlanda Geçen Diğer Teknolojiler ({item.skill_match.missing.length}):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {item.skill_match.missing.map((s) => (
                        <Chip key={s} tone="neutral">
                          {s}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* ── Başvuru adımları ── */}
          <section>
            <SectionHeader
              label="Başvuru adımları"
              hint={`${steps.filter((s) => s.status === "done").length}/${steps.length} tamam`}
            />
            {steps.length === 0 ? (
              <p className="py-3 text-meta text-muted">Henüz adım eklenmedi.</p>
            ) : (
              <ul className="mb-3 flex flex-col gap-1.5">
                {steps.map((step) => (
                  <li key={step.id} className="flex items-center gap-2">
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={step.status === "done"}
                      disabled={!online || toggleStep.isPending}
                      onClick={() => toggleStep.mutate(step)}
                      title={step.status === "done" ? "Adımı aç" : "Adımı tamamla"}
                      className={cx(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
                        step.status === "done" ? "border-ok bg-ok text-canvas" : "border-strong bg-surface",
                      )}
                    >
                      {step.status === "done" && <Check size={12} />}
                    </button>
                    <span
                      className={cx(
                        "min-w-0 flex-1 truncate text-body",
                        step.status === "done" && "text-muted line-through",
                      )}
                    >
                      {step.title}
                    </span>
                    <Chip size="xs">başvuru adımı</Chip>
                  </li>
                ))}
              </ul>
            )}
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (stepTitle.trim()) addStep.mutate();
              }}
            >
              <Input
                value={stepTitle}
                onChange={setStepTitle}
                placeholder="Örn. formu doldur, transkript gönder…"
                ariaLabel="Yeni başvuru adımı"
                className="flex-1"
              />
              <Button type="submit" disabled={!online || !stepTitle.trim() || addStep.isPending}>
                Ekle
              </Button>
            </form>
          </section>

          <FollowUpSection id={id} followUpAt={item?.follow_up_at ?? null} />

          <InterviewsSection id={id} online={online} />

          {/* ── Durum geçmişi ── */}
          <section>
            <SectionHeader label="Geçmiş" hint={`${history.length} değişiklik`} />
            {history.length === 0 ? (
              <p className="text-meta text-muted">Henüz geçiş yok.</p>
            ) : (
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

          <RelatedPanel entityId={id} />
        </div>
      </aside>
    </div>
  );
}

/* Skor bandi -> tek kelime etiket (renk karttaki gibi gorselde). */
function scoreBandLabel(band: ScoreBand): string {
  switch (band) {
    case "killed":
      return "elendi";
    case "strong":
      return "güçlü";
    case "fair":
      return "orta";
    default:
      return "zayıf";
  }
}

import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Bookmark,
  CalendarClock,
  Check,
  ExternalLink,
  FileText,
  Plus,
  Save,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/core/api";
import { RelatedPanel } from "@/core/RelatedPanel";
import { Button, Chip, Empty, Input, SectionHeader, Select, Textarea, cx, relativeTime, useToast } from "@/core/ui";
import type { ApplicationHistoryRow, Document, Opportunity, Todo } from "@/core/types";
import { planDayForToday } from "@/core/tasks";
import { useSaveToLibrary } from "@/core/SaveToLibrary";
import { useOnline } from "@/lib/hooks";
import { SCORE_TONE, STATUSES, STATUS_TONES, daysLeft, kindLabel, scoreBand, statusLabel } from "./labels";
import { sourceLabel } from "@/core/labels";
import type { ScoreBand } from "./labels";
import { ApplicationSection, FollowUpSection, InterviewsSection, RequirementsSection } from "./OpportunityDetailSections";

type DetailTab = "overview" | "crm" | "notes";

interface NoteItem {
  id: string;
  title: string;
  body: string;
  updated_at?: string;
}

/** Sağ taraftan açılan ilan detayı: durum, skor, CRM ve şirket notları. */
export function OpportunityDetail({ id, close }: { id: string; close: () => void }) {
  const online = useOnline();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [rejecting, setRejecting] = useState(false);
  const [rejectionDraft, setRejectionDraft] = useState("");
  const [stepTitle, setStepTitle] = useState("");
  const [noteDraft, setNoteDraft] = useState<string | null>(null);

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
  const { data: researchNotes = [], refetch: refetchNotes } = useQuery({
    queryKey: ["opportunity-notes", id],
    queryFn: () => api.get<NoteItem[]>(`/opportunities/${id}/notes`),
  });

  const activeNote = researchNotes[0];

  useEffect(() => {
    if (activeNote) {
      setNoteDraft(activeNote.body);
    }
  }, [activeNote?.id, activeNote?.body]);

  const createResearchNote = useMutation({
    mutationFn: () => api.post<NoteItem>(`/opportunities/${id}/research-note`),
    onSuccess: (note) => {
      invalidateAfter("note.write", "opportunity.write");
      refetchNotes();
      setNoteDraft(note.body);
      toast.push("Şirket araştırma notu hazırlandı", { tone: "ok" });
      setActiveTab("notes");
    },
  });

  const saveNote = useMutation({
    mutationFn: (body: string) => {
      if (!activeNote) return Promise.reject("Not bulunamadı");
      return api.patch(`/notes/${activeNote.id}`, { body });
    },
    onSuccess: () => {
      invalidateAfter("note.write", "opportunity.write");
      refetchNotes();
      toast.push("Şirket notu kaydedildi", { tone: "ok" });
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

  // Esc kapatma
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [close]);

  const left = daysLeft(item?.deadline_at ?? null);
  const band = scoreBand(item?.score ?? null);

  // Hızlı durum aksiyonları
  const handleQuickTransition = (toStatus: string) => {
    if (toStatus === "rejected") {
      setRejecting(true);
      return;
    }
    transition.mutate({ to: toStatus });
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-canvas/60 backdrop-blur-xs" onClick={close} role="presentation">
      <aside
        role="dialog"
        aria-label={item?.title ?? "Fırsat Detayı"}
        onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-2xl flex-col overflow-y-auto border-l border-subtle bg-canvas shadow-2xl"
      >
        {/* ── ÜST BAŞLIK & ROZETLER ── */}
        <header className="sticky top-0 z-10 border-b border-subtle bg-canvas/95 px-6 py-4 backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <Chip>{item ? kindLabel(item.kind) : "…"}</Chip>
                {item && <Chip tone={STATUS_TONES[item.status] ?? "neutral"}>{statusLabel(item.status)}</Chip>}
                {band && (
                  <Chip tone={SCORE_TONE[band]}>
                    {band === "killed" ? "Elendi" : `${Math.round(item!.score as number)} Puan`}
                  </Chip>
                )}
                {item?.skill_match && (
                  <Chip tone="ok">
                    CV Uyumu: %{Math.round(item.skill_match.match_ratio * 100)}
                  </Chip>
                )}
              </div>
              <h2 className="text-heading font-semibold text-primary leading-snug">{item?.title ?? "Yükleniyor…"}</h2>
              <p className="mt-1 text-meta text-muted">
                {[item?.organization, item?.location, item?.remote ? (item.remote === "remote" ? "Uzaktan" : item.remote) : null, item?.compensation]
                  .filter(Boolean)
                  .join(" · ") || "—"}
              </p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Kapat"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-subtle text-muted transition hover:bg-surface-hover hover:text-primary"
            >
              <X size={16} />
            </button>
          </div>

          {/* Aksiyon butonları */}
          <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-subtle/60 pt-3">
            <div className="flex items-center gap-2">
              {item?.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex h-control items-center gap-1.5 rounded-control border border-subtle bg-surface px-3 text-meta font-medium text-primary transition hover:bg-surface-hover"
                >
                  <ExternalLink size={13} /> İlanı Aç
                </a>
              )}
              {item?.url && (
                <Button variant="secondary" size="sm" disabled={!online} title="Kütüphaneye kaydet" onClick={saveItem}>
                  <Bookmark size={13} /> Kaydet
                </Button>
              )}
            </div>

            {left !== null && (
              <span className={cx("text-meta tabular-nums font-medium", left <= 7 ? "text-warn" : "text-muted")}>
                {left < 0 ? `${Math.abs(left)} gün önce doldu` : `Son tarihe ${left} gün`}
              </span>
            )}
          </div>

          {/* ── SEKMELER (TABS) ── */}
          <div className="mt-4 flex border-b border-subtle text-meta font-medium">
            <button
              type="button"
              onClick={() => setActiveTab("overview")}
              className={cx(
                "border-b-2 px-4 py-2 transition-colors",
                activeTab === "overview"
                  ? "border-accent text-accent font-semibold"
                  : "border-transparent text-secondary hover:text-primary",
              )}
            >
              İlan & Yetenekler
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("crm")}
              className={cx(
                "flex items-center gap-1.5 border-b-2 px-4 py-2 transition-colors",
                activeTab === "crm"
                  ? "border-accent text-accent font-semibold"
                  : "border-transparent text-secondary hover:text-primary",
              )}
            >
              <span>Süreç & CRM</span>
              {item?.status && item.status !== "discovered" && (
                <span className="h-2 w-2 rounded-full bg-accent" />
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("notes")}
              className={cx(
                "flex items-center gap-1.5 border-b-2 px-4 py-2 transition-colors",
                activeTab === "notes"
                  ? "border-accent text-accent font-semibold"
                  : "border-transparent text-secondary hover:text-primary",
              )}
            >
              <FileText size={13} />
              <span>Şirket Notları</span>
              {researchNotes.length > 0 && (
                <span className="rounded-full bg-surface-sunken px-1.5 text-micro font-medium text-primary">
                  {researchNotes.length}
                </span>
              )}
            </button>
          </div>
        </header>

        {/* ── İÇERİK ALANI ── */}
        <div className="flex flex-col gap-6 p-6">
          {/* TAB 1: GENEL & İLAN */}
          {activeTab === "overview" && (
            <>
              {/* Yetenek & Beceri Uyumu */}
              {item?.skill_match ? (
                <section className="rounded-panel border border-subtle bg-surface p-4 shadow-xs">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <SectionHeader
                      label="CV & Beceri Eşleşmesi"
                      hint={`CV Uyumu: %${Math.round(item.skill_match.match_ratio * 100)}`}
                    />
                    <Chip tone="ok">%{Math.round(item.skill_match.match_ratio * 100)}</Chip>
                  </div>
                  <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full bg-ok transition-all"
                      style={{ width: `${Math.round(item.skill_match.match_ratio * 100)}%` }}
                    />
                  </div>
                  <div className="space-y-3">
                    {item.skill_match.matched.length > 0 && (
                      <div>
                        <span className="mb-1.5 block text-micro font-medium uppercase tracking-wider text-secondary">
                          CV'n ile Örtüşen Yetenekler ({item.skill_match.matched.length}):
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
                        <span className="mb-1.5 block text-micro font-medium uppercase tracking-wider text-muted">
                          İlandaki Diğer Teknolojiler ({item.skill_match.missing.length}):
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
              ) : item?.score !== null && item?.score !== undefined ? (
                <section className="rounded-panel border border-subtle bg-surface p-4">
                  <SectionHeader label="Uyum Puanı" hint={band ? scoreBandLabel(band) : undefined} />
                  <div className="mt-2 flex items-baseline gap-3">
                    <span className="text-display font-semibold leading-none text-primary tabular-nums">
                      {Math.round(item.score)}
                    </span>
                    <span className="text-meta text-muted">/ 100 puan</span>
                    <span className="ml-auto h-2 w-36 overflow-hidden rounded-full bg-surface-sunken">
                      <span
                        className="block h-full rounded-full bg-accent"
                        style={{ width: `${Math.max(0, Math.min(100, item.score))}%` }}
                      />
                    </span>
                  </div>
                </section>
              ) : null}

              {/* İlan Künyesi */}
              <section className="rounded-panel border border-subtle bg-surface p-4">
                <SectionHeader label="İlan Künyesi" />
                <dl className="mt-3 grid grid-cols-[7rem_1fr] gap-x-4 gap-y-2.5 text-meta">
                  {[
                    ["Kurum", item?.organization || "—"],
                    ["Kaynak", item ? sourceLabel(item.source) : "—"],
                    ["Lokasyon", item?.location || "Belirtilmemiş"],
                    ["Çalışma", item?.remote ? (item.remote === "remote" ? "100% Uzaktan" : item.remote === "hybrid" ? "Hibrit" : "Ofis") : "—"],
                    ["Ücret / Maaş", item?.compensation || "Belirtilmemiş"],
                    ["Tarama Tarihi", item ? new Date(item.found_at).toLocaleDateString("tr-TR") : "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="contents">
                      <dt className="text-muted font-medium">{label}</dt>
                      <dd className="text-primary font-medium">{value}</dd>
                    </div>
                  ))}
                </dl>
              </section>

              {/* Gereksinimler & Belgeler */}
              <div className="rounded-panel border border-subtle bg-surface p-4">
                <RequirementsSection id={id} online={online} documents={documents} />
              </div>

              {/* İlan Notları */}
              {item?.notes && (
                <section className="rounded-panel border border-subtle bg-surface p-4">
                  <SectionHeader label="İlan Notları" />
                  <p className="mt-2 whitespace-pre-line text-body text-secondary">{item.notes}</p>
                </section>
              )}

              {/* İlişkili Kayıtlar */}
              <div className="rounded-panel border border-subtle bg-surface p-4">
                <RelatedPanel entityId={id} />
              </div>
            </>
          )}

          {/* TAB 2: SÜREÇ & CRM */}
          {activeTab === "crm" && (
            <>
              {/* AŞAMA YÖNETİMİ & HIZLI GEÇİŞ */}
              <section className="rounded-panel border border-subtle bg-surface p-4 shadow-xs">
                <SectionHeader label="Başvuru Durumu" hint="Tek tıkla aşamayı güncelle" />
                <div className="mt-3 flex flex-wrap items-center gap-2">
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
                    className="border-strong font-medium"
                  >
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {statusLabel(status)}
                      </option>
                    ))}
                  </Select>

                  {/* Hızlı Butonlar */}
                  {item?.status === "discovered" && (
                    <Button size="sm" variant="primary" onClick={() => handleQuickTransition("considering")}>
                      İncelemeye Al →
                    </Button>
                  )}
                  {item?.status === "considering" && (
                    <Button size="sm" variant="primary" onClick={() => handleQuickTransition("applied")}>
                      Başvuruldu Olarak İşaretle →
                    </Button>
                  )}
                  {item?.status === "applied" && (
                    <Button size="sm" variant="primary" onClick={() => handleQuickTransition("interviewing")}>
                      Mülakata Geçildi →
                    </Button>
                  )}
                  {item?.status === "interviewing" && (
                    <Button size="sm" variant="primary" onClick={() => handleQuickTransition("offer")}>
                      Teklif Alındı!
                    </Button>
                  )}
                  {item?.status !== "rejected" && (
                    <Button size="sm" variant="ghost" onClick={() => setRejecting(true)} className="text-danger hover:bg-danger-surface">
                      Reddedildi
                    </Button>
                  )}
                </div>

                {/* Red Nedeni Modalı / Satırı */}
                {rejecting && (
                  <div className="mt-3 rounded-control border border-danger-border bg-danger-surface/40 p-3">
                    <span className="mb-2 block text-meta font-medium text-danger">Red Nedeni Seçin veya Yazın:</span>
                    <div className="mb-2 flex flex-wrap gap-1.5">
                      {rejectionOptions.map((reason) => (
                        <button
                          key={reason}
                          type="button"
                          onClick={() => setRejectionDraft(reason)}
                          className={cx(
                            "rounded-control border px-2.5 py-1 text-meta transition",
                            rejectionDraft === reason
                              ? "border-danger bg-danger text-canvas font-medium"
                              : "border-danger-border bg-surface text-danger hover:bg-danger-surface",
                          )}
                        >
                          {reason}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Input
                        value={rejectionDraft}
                        onChange={setRejectionDraft}
                        placeholder="Özel red nedeni…"
                        ariaLabel="Red nedeni"
                        className="flex-1"
                      />
                      <Button
                        variant="danger"
                        size="sm"
                        disabled={!rejectionDraft.trim()}
                        onClick={() => {
                          transition.mutate({ to: "rejected", rejection_reason: rejectionDraft.trim() });
                          setRejecting(false);
                        }}
                      >
                        Kaydet
                      </Button>
                      <Button size="sm" onClick={() => setRejecting(false)}>
                        Vazgeç
                      </Button>
                    </div>
                  </div>
                )}
                {item?.status === "rejected" && item.rejection_reason && (
                  <div className="mt-3 rounded-control border border-danger-border bg-danger-surface px-3 py-2 text-meta text-danger">
                    <strong>Red Nedeni:</strong> {item.rejection_reason}
                  </div>
                )}
              </section>

              {/* TAKİP TARİHİ (Follow Up) */}
              <div className="rounded-panel border border-subtle bg-surface p-4">
                <FollowUpSection id={id} followUpAt={item?.follow_up_at ?? null} />
              </div>

              {/* MÜLAKATLAR */}
              <div className="rounded-panel border border-subtle bg-surface p-4">
                <InterviewsSection id={id} online={online} />
              </div>

              {/* BAŞVURU FORMU & KULLANILAN CV */}
              <div className="rounded-panel border border-subtle bg-surface p-4">
                <ApplicationSection id={id} online={online} documents={documents} />
              </div>

              {/* KONTROL LİSTESİ / BAŞVURU ADIMLARI */}
              <section className="rounded-panel border border-subtle bg-surface p-4">
                <SectionHeader
                  label="Başvuru Adımları & Görevler"
                  hint={`${steps.filter((s) => s.status === "done").length}/${steps.length} tamamlandı`}
                />
                {steps.length === 0 ? (
                  <p className="py-2 text-meta text-muted">Henüz görev adımı eklenmedi.</p>
                ) : (
                  <ul className="my-3 flex flex-col gap-2">
                    {steps.map((step) => (
                      <li key={step.id} className="flex items-center gap-2 rounded-control border border-subtle bg-surface-sunken/20 px-3 py-2">
                        <button
                          type="button"
                          role="checkbox"
                          aria-checked={step.status === "done"}
                          disabled={!online || toggleStep.isPending}
                          onClick={() => toggleStep.mutate(step)}
                          title={step.status === "done" ? "Adımı aç" : "Adımı tamamla"}
                          className={cx(
                            "flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded border transition",
                            step.status === "done" ? "border-ok bg-ok text-canvas" : "border-strong bg-surface hover:border-accent",
                          )}
                        >
                          {step.status === "done" && <Check size={11} />}
                        </button>
                        <span
                          className={cx(
                            "min-w-0 flex-1 truncate text-body",
                            step.status === "done" && "text-muted line-through",
                          )}
                        >
                          {step.title}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <form
                  className="mt-2 flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
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
                    <Plus size={13} /> Ekle
                  </Button>
                </form>
              </section>

              {/* SÜREÇ GEÇMİŞİ */}
              <section className="rounded-panel border border-subtle bg-surface p-4">
                <SectionHeader label="Süreç Geçmişi" hint={`${history.length} geçiş kaydı`} />
                {history.length === 0 ? (
                  <p className="py-2 text-meta text-muted">Henüz aşama değişikliği kaydedilmedi.</p>
                ) : (
                  <ol className="mt-3 space-y-2">
                    {history.map((row) => (
                      <li key={row.id} className="flex items-center gap-2 text-meta">
                        <span className="w-20 shrink-0 text-muted">{statusLabel(row.from_status ?? "—")}</span>
                        <span className="text-accent">→</span>
                        <span className="font-medium text-primary">{statusLabel(row.to_status)}</span>
                        <span className="ml-auto shrink-0 text-muted tabular-nums">{relativeTime(row.at)}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          )}

          {/* TAB 3: ŞİRKET NOTLARI & MÜLAKAT HAZIRLIĞI */}
          {activeTab === "notes" && (
            <section className="rounded-panel border border-subtle bg-surface p-4 shadow-xs">
              <div className="flex items-center justify-between gap-3 border-b border-subtle pb-3">
                <div>
                  <SectionHeader
                    label={activeNote ? activeNote.title : "Şirket & Mülakat Notu"}
                    hint={activeNote?.updated_at ? `Son kayıt: ${relativeTime(activeNote.updated_at)}` : undefined}
                  />
                  <p className="text-meta text-muted">
                    Bu ilan ve kurum için tüm araştırmalarını ve mülakat notlarını buradan yönet.
                  </p>
                </div>
                {activeNote && (
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!online || saveNote.isPending || noteDraft === activeNote.body}
                    onClick={() => noteDraft !== null && saveNote.mutate(noteDraft)}
                  >
                    <Save size={13} /> {saveNote.isPending ? "Kaydediliyor…" : "Kaydet"}
                  </Button>
                )}
              </div>

              {!activeNote ? (
                <div className="py-8 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent-surface text-accent">
                    <FileText size={24} />
                  </div>
                  <h3 className="text-body font-semibold text-primary">Henüz Şirket Notu Oluşturulmadı</h3>
                  <p className="mx-auto mt-1 max-w-sm text-meta text-muted">
                    {item?.organization || "Şirket"} hakkında faaliyet alanı, teknoloji yığını ve mülakat soruları için tek tıkla şablon not oluştur.
                  </p>
                  <Button
                    variant="primary"
                    className="mt-4"
                    disabled={!online || createResearchNote.isPending}
                    onClick={() => createResearchNote.mutate()}
                  >
                    <Plus size={14} /> Şirket Araştırma Notu Oluştur
                  </Button>
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  <Textarea
                    value={noteDraft ?? ""}
                    onChange={setNoteDraft}
                    onBlur={() => {
                      if (noteDraft !== null && noteDraft !== activeNote.body) {
                        saveNote.mutate(noteDraft);
                      }
                    }}
                    rows={16}
                    placeholder="Şirket araştırması, görüşülecek kişiler, teknik sorular…"
                    className="font-mono text-meta leading-relaxed"
                  />
                  <div className="flex items-center justify-between text-micro text-muted">
                    <span>* Otomatik kaydeder (veya yukarıdaki Kaydet butonunu kullan).</span>
                    <span>Opportunities'den ayrılmadan notlar güvenle saklanır.</span>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}

/* Skor bandı -> tek kelime etiket */
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

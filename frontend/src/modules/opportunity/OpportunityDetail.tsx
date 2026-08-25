import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ExternalLink, X } from "lucide-react";
import { api } from "@/core/api";
import { Badge, Button, Empty, Input, SectionHeader, cx } from "@/core/ui";
import type { Document, Opportunity } from "@/core/types";
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
                onChange={(e) => patch.mutate(e.target.value)}
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

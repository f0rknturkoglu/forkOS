import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  Clock,
  Compass,
  FileCheck,
  HelpCircle,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, relativeTime, useToast } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type DeepEvaluationOut = components["schemas"]["DeepEvaluationOut"];
type RequirementAssessmentOut = components["schemas"]["RequirementAssessmentOut"];

function classificationTone(classification: string): "ok" | "warn" | "danger" | "neutral" {
  if (classification === "strong") return "ok";
  if (classification === "partial") return "warn";
  if (classification === "missing") return "danger";
  return "neutral";
}

function classificationLabel(classification: string): string {
  if (classification === "strong") return "Güçlü Uyum";
  if (classification === "partial") return "Kısmi Uyum";
  if (classification === "missing") return "Eksik";
  return "Belirsiz";
}

function overallFitTone(fit: string): "ok" | "warn" | "danger" | "neutral" {
  if (fit === "strong_fit" || fit === "good_fit") return "ok";
  if (fit === "moderate_fit") return "warn";
  return "danger";
}

function overallFitLabel(fit: string): string {
  if (fit === "strong_fit") return "Çok Yüksek Uyum";
  if (fit === "good_fit") return "Yüksek Uyum";
  if (fit === "moderate_fit") return "Orta Seviye Uyum";
  if (fit === "poor_fit") return "Düşük Uyum";
  return fit;
}

export function OpportunityDeepEvaluationSection({
  opportunityId,
  online,
}: {
  opportunityId: string;
  online: boolean;
}) {
  const toast = useToast();

  const {
    data: evaluation,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["opportunity", opportunityId, "deep-evaluation"],
    queryFn: () => api.get<DeepEvaluationOut>(`/opportunities/${opportunityId}/deep-evaluation`),
  });

  const evaluateMutation = useMutation({
    mutationFn: () => api.post<DeepEvaluationOut>(`/opportunities/${opportunityId}/deep-evaluate`),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      refetch();
      toast.push("Derin uzman değerlendirmesi başarıyla tamamlandı.", { tone: "ok" });
    },
    onError: (err: any) => {
      toast.push(err?.message || "Değerlendirme sırasında bir hata oluştu.", { tone: "danger" });
    },
  });

  if (isLoading) {
    return (
      <div className="py-6 text-center text-meta text-muted">
        Derin değerlendirme verileri yükleniyor…
      </div>
    );
  }

  if (!evaluation) {
    return (
      <div className="rounded-control border border-subtle bg-surface-sunken p-5 text-center">
        <Sparkles className="mx-auto mb-2 text-accent" size={28} />
        <h4 className="text-body font-semibold text-primary">Derin Kariyer Uzmanı Değerlendirmesi</h4>
        <p className="mx-auto mt-1 max-w-md text-meta text-secondary">
          İlan metnini, kanıtlanmış teknik becerilerinizi ve kariyer başarılarınızı (STAR hikâyeleri)
          yapay zekâ destekli kariyer uzmanı gözüyle inceler; kanıta dayalı uyum haritası çıkarır.
        </p>
        <div className="mt-4">
          <Button
            size="sm"
            disabled={!online || evaluateMutation.isPending}
            onClick={() => evaluateMutation.mutate()}
          >
            {evaluateMutation.isPending ? "Değerlendiriliyor…" : "Uzman Değerlendirmesini Başlat"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Staleness Banner */}
      {evaluation.is_stale && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-warn/30 bg-warn/10 p-3 text-warn">
          <div className="flex items-center gap-2 text-meta">
            <AlertTriangle size={16} className="shrink-0" />
            <span>
              İlan açıklaması veya aday profil verileriniz güncellendiği için bu değerlendirme bayatlamış olabilir.
            </span>
          </div>
          <Button
            size="sm"
            disabled={!online || evaluateMutation.isPending}
            onClick={() => evaluateMutation.mutate()}
          >
            <RefreshCw size={13} className={evaluateMutation.isPending ? "animate-spin" : ""} />
            {evaluateMutation.isPending ? "Yenileniyor…" : "Yeniden Değerlendir"}
          </Button>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-control border border-subtle bg-surface p-3">
          <span className="text-micro font-medium uppercase text-muted">Genel Rol Uyumu</span>
          <div className="mt-1 flex items-center gap-2">
            <Chip tone={overallFitTone(evaluation.role_fit)}>
              {overallFitLabel(evaluation.role_fit)}
            </Chip>
          </div>
        </div>

        <div className="rounded-control border border-subtle bg-surface p-3">
          <span className="text-micro font-medium uppercase text-muted">Kıdem Seviyesi</span>
          <div className="mt-1 text-body font-medium text-primary">
            {evaluation.seniority_fit}
          </div>
        </div>

        <div className="rounded-control border border-subtle bg-surface p-3">
          <span className="text-micro font-medium uppercase text-muted">Konum / Çalışma Modeli</span>
          <div className="mt-1 text-body font-medium text-primary">
            {evaluation.location_fit}
          </div>
        </div>
      </div>

      {/* Summary Narrative */}
      {evaluation.overall_assessment && (
        <div className="rounded-control border border-subtle bg-surface-sunken p-3.5">
          <span className="mb-1 block text-micro font-medium uppercase tracking-wider text-secondary">
            Uzman Değerlendirme Özeti
          </span>
          <p className="text-body text-secondary leading-relaxed">
            {evaluation.overall_assessment}
          </p>
        </div>
      )}

      {/* Must-Have Requirements */}
      {evaluation.must_have && evaluation.must_have.length > 0 && (
        <div>
          <span className="mb-2 block text-micro font-medium uppercase tracking-wider text-secondary">
            Temel Gereksinimler & Kanıtlar ({evaluation.must_have.length})
          </span>
          <div className="space-y-2">
            {evaluation.must_have.map((req, idx) => (
              <div
                key={idx}
                className="rounded-control border border-subtle bg-surface p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-body font-medium text-primary">
                    {req.requirement}
                  </span>
                  <Chip tone={classificationTone(req.classification)}>
                    {classificationLabel(req.classification)}
                  </Chip>
                </div>
                {req.reason && (
                  <p className="mt-1 text-meta text-secondary">
                    {req.reason}
                  </p>
                )}
                {req.candidate_evidence_refs && req.candidate_evidence_refs.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-micro text-muted">Aday Kanıtı:</span>
                    {req.candidate_evidence_refs.map((ref, rIdx) => (
                      <span
                        key={rIdx}
                        className="rounded bg-surface-sunken px-1.5 py-0.5 font-mono text-micro text-primary"
                      >
                        {ref}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nice-To-Have Requirements */}
      {evaluation.nice_to_have && evaluation.nice_to_have.length > 0 && (
        <div>
          <span className="mb-2 block text-micro font-medium uppercase tracking-wider text-muted">
            Tercih Sebebi Gereksinimler ({evaluation.nice_to_have.length})
          </span>
          <div className="space-y-2">
            {evaluation.nice_to_have.map((req, idx) => (
              <div
                key={idx}
                className="rounded-control border border-subtle bg-surface p-2.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-meta text-primary">{req.requirement}</span>
                  <Chip tone={classificationTone(req.classification)}>
                    {classificationLabel(req.classification)}
                  </Chip>
                </div>
                {req.reason && <p className="mt-0.5 text-meta text-muted">{req.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths & Missing Grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-control border border-ok/20 bg-ok/5 p-3">
          <span className="mb-2 flex items-center gap-1.5 text-micro font-medium uppercase text-ok">
            <CheckCircle2 size={13} />
            Öne Çıkan Güçlü Yönler
          </span>
          {evaluation.strengths && evaluation.strengths.length > 0 ? (
            <ul className="space-y-1 text-meta text-primary">
              {evaluation.strengths.map((str, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-ok">•</span>
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-meta text-muted">Belirtilmedi.</p>
          )}
        </div>

        <div className="rounded-control border border-danger/20 bg-danger/5 p-3">
          <span className="mb-2 flex items-center gap-1.5 text-micro font-medium uppercase text-danger">
            <XCircle size={13} />
            Eksik veya Geliştirilmesi Gerekenler
          </span>
          {evaluation.missing_requirements && evaluation.missing_requirements.length > 0 ? (
            <ul className="space-y-1 text-meta text-primary">
              {evaluation.missing_requirements.map((mis, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-danger">•</span>
                  <span>{mis}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-meta text-muted">Eksik tespit edilmedi.</p>
          )}
        </div>
      </div>

      {/* Work Authorization & Compensation */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {evaluation.work_authorization && (
          <div className="rounded-control border border-subtle bg-surface p-3">
            <span className="text-micro font-medium uppercase text-secondary">Çalışma İzni & Sponsorluk</span>
            <div className="mt-1 text-meta text-primary">
              {String((evaluation.work_authorization as any).status || "Belirtilmemiş")}
            </div>
            {(evaluation.work_authorization as any).notes && (
              <p className="mt-1 text-meta text-muted">
                {String((evaluation.work_authorization as any).notes)}
              </p>
            )}
          </div>
        )}

        {evaluation.compensation && (
          <div className="rounded-control border border-subtle bg-surface p-3">
            <span className="text-micro font-medium uppercase text-secondary">Ücret & Beklenti Uyumu</span>
            <div className="mt-1 text-meta text-primary">
              {String((evaluation.compensation as any).match || "Belirtilmemiş")}
            </div>
            {(evaluation.compensation as any).notes && (
              <p className="mt-1 text-meta text-muted">
                {String((evaluation.compensation as any).notes)}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Metadata footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-subtle pt-2 text-micro text-muted">
        <span>Değerlendirme: {relativeTime(evaluation.created_at)}</span>
        <span className="font-mono">
          Sağlayıcı: {evaluation.provider} ({evaluation.model})
        </span>
      </div>
    </div>
  );
}

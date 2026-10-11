import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Copy,
  FileCheck2,
  FileText,
  HelpCircle,
  Package,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Empty, Input, relativeTime, useToast } from "@/core/ui";
import type { components } from "@/generated/api-schema";

type ApplicationPackageOut = components["schemas"]["ApplicationPackageOut"];
type ApplicationAnswerOut = components["schemas"]["ApplicationAnswerOut"];
type CvChangeItemOut = components["schemas"]["CvChangeItemOut"];

function readinessTone(readiness: string): "ok" | "warn" | "danger" | "neutral" {
  if (readiness === "READY") return "ok";
  if (readiness === "NEEDS_INPUT") return "warn";
  if (readiness === "UNSUPPORTED_CLAIMS" || readiness === "RENDER_FAILED") return "danger";
  return "neutral";
}

function readinessLabel(readiness: string): string {
  if (readiness === "READY") return "Başvuruya Hazır";
  if (readiness === "NEEDS_INPUT") return "Kullanıcı Girdisi Bekleniyor";
  if (readiness === "UNSUPPORTED_CLAIMS") return "Doğrulanamayan İddia Var";
  if (readiness === "STALE_EVALUATION") return "Değerlendirme Bayat";
  if (readiness === "RENDER_FAILED") return "Doküman Üretilemedi";
  return readiness;
}

function answerClassificationTone(classification: string): "ok" | "warn" | "danger" | "neutral" {
  if (classification === "safe_verified") return "ok";
  if (classification === "needs_user_input") return "warn";
  return "danger";
}

function answerClassificationLabel(classification: string): string {
  if (classification === "safe_verified") return "Doğrulanmış Bilgi";
  if (classification === "needs_user_input") return "Girdi Gerekiyor";
  if (classification === "sensitive_user_decision") return "Hassas Tercih";
  return classification;
}

export function OpportunityApplicationPackageSection({
  opportunityId,
  online,
}: {
  opportunityId: string;
  online: boolean;
}) {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<"answers" | "cv_changes" | "cover_letter">("answers");
  const [answerDrafts, setAnswerDrafts] = useState<Record<string, string>>({});

  const {
    data: pkg,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["opportunity", opportunityId, "application-package"],
    queryFn: () => api.get<ApplicationPackageOut>(`/opportunities/${opportunityId}/application-package`),
  });

  const prepareMutation = useMutation({
    mutationFn: () => api.post<ApplicationPackageOut>(`/opportunities/${opportunityId}/prepare-package`),
    onSuccess: (result) => {
      invalidateAfter("opportunity.write");
      refetch();
      toast.push(`Başvuru paketi üretildi: ${readinessLabel(result.readiness)}.`, {
        tone: result.readiness === "READY" ? "ok" : "warn",
      });
    },
    onError: (err: any) => {
      toast.push(err?.message || "Başvuru paketi hazırlanırken hata oluştu.", { tone: "danger" });
    },
  });

  const resolveAnswerMutation = useMutation({
    mutationFn: ({ question, answer }: { question: string; answer: string }) =>
      api.post<ApplicationPackageOut>(`/opportunities/${opportunityId}/application-package/resolve-answer`, {
        question,
        answer,
      }),
    onSuccess: () => {
      invalidateAfter("opportunity.write");
      refetch();
      toast.push("Soru yanıtı kaydedildi ve hazırlık durumu güncellendi.", { tone: "ok" });
    },
    onError: (err: any) => {
      toast.push(err?.message || "Yanıt kaydedilemedi.", { tone: "danger" });
    },
  });

  const reviewCoverMutation = useMutation({
    mutationFn: (decision: "approved" | "rejected") =>
      api.post<ApplicationPackageOut>(`/opportunities/${opportunityId}/application-package/review-cover-letter`, {
        decision,
      }),
    onSuccess: (result) => {
      invalidateAfter("opportunity.write");
      refetch();
      toast.push(`Ön yazı incelemesi kaydedildi: ${readinessLabel(result.readiness)}.`, { tone: "ok" });
    },
    onError: (err: any) => {
      toast.push(err?.message || "Ön yazı incelemesi kaydedilemedi.", { tone: "danger" });
    },
  });

  const copyCoverLetter = () => {
    if (pkg?.cover_letter) {
      navigator.clipboard.writeText(pkg.cover_letter);
      toast.push("Ön yazı panoya kopyalandı.", { tone: "ok" });
    }
  };

  if (isLoading) {
    return <div className="py-6 text-center text-meta text-muted">Başvuru paketi kontrol ediliyor…</div>;
  }

  if (!pkg) {
    return (
      <div className="rounded-control border border-subtle bg-surface-sunken p-5 text-center">
        <Package className="mx-auto mb-2 text-accent" size={28} />
        <h4 className="text-body font-semibold text-primary">Kanıta Dayalı Başvuru Paketi</h4>
        <p className="mx-auto mt-1 max-w-md text-meta text-secondary">
          Bu pozisyona özel özelleştirilmiş CV revizyonu, STAR hikâyelerinizden beslenen ön yazı ve başvuru tarama
          soruları için kanıtlanmış yanıt taslakları hazırlar.
        </p>
        <div className="mt-4">
          <Button size="sm" disabled={!online || prepareMutation.isPending} onClick={() => prepareMutation.mutate()}>
            {prepareMutation.isPending ? "Paket Hazırlanıyor…" : "Başvuru Paketini Hazırla"}
          </Button>
        </div>
      </div>
    );
  }

  const unsupportedClaims = pkg.fact_verification?.filter((v) => v.status === "unsupported") || [];

  return (
    <div className="stack-y-4">
      {/* Header / Readiness Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-subtle bg-surface p-3.5">
        <div className="flex items-center gap-3">
          <span className="text-body font-medium text-primary">Hazırlık Durumu:</span>
          <Chip tone={readinessTone(pkg.readiness)}>{readinessLabel(pkg.readiness)}</Chip>
          {pkg.updated_at && <span className="text-meta text-muted">Güncellendi: {relativeTime(pkg.updated_at)}</span>}
        </div>
        <Button size="sm" disabled={!online || prepareMutation.isPending} onClick={() => prepareMutation.mutate()}>
          <RefreshCw size={13} className={prepareMutation.isPending ? "animate-spin" : ""} />
          {prepareMutation.isPending ? "Yenileniyor…" : "Paketi Yeniden Oluştur"}
        </Button>
      </div>

      {/* Unsupported Claims Alert Gate */}
      {pkg.generated_documents && pkg.generated_documents.length > 0 && (
        <div className="stack-y-2 rounded-control border border-subtle bg-surface p-3">
          <h4 className="text-body font-medium text-primary">Üretilen belgeler</h4>
          <p className="text-meta text-muted">
            Master CV korunur. Taslak belge bağlantısı, paketin onaylandığı anlamına gelmez.
          </p>
          {pkg.generated_documents.map((document, index) =>
            document.document_id ? (
              <a
                key={document.document_id}
                href={`/api/documents/${encodeURIComponent(document.document_id)}/file`}
                target="_blank"
                rel="noreferrer"
                className="block text-meta text-accent underline"
              >
                {document.title} ({document.mime})
              </a>
            ) : (
              <p key={index} className="text-meta text-warn">
                {document.title}: gerçek belge henüz yok.
              </p>
            ),
          )}
        </div>
      )}
      {unsupportedClaims.length > 0 && (
        <div className="rounded-control border border-danger/30 bg-danger/10 p-3.5 text-danger">
          <div className="flex items-start gap-2">
            <ShieldAlert size={18} className="mt-0.5 shrink-0" />
            <div>
              <strong className="text-body font-semibold">Doğrulanamayan İddia Kapısı (Sıfır Halüsinasyon)</strong>
              <p className="mt-0.5 text-meta">
                Özelleştirilmiş CV taslağında doğrulanmış profilinizde veya hikâyelerinizde bulunmayan iddialar tespit
                edildi. Güvenlik gereği paket otomatik onaylanmaz.
              </p>
              <ul className="mt-2 list-inside list-disc text-meta">
                {unsupportedClaims.map((claim, idx) => (
                  <li key={idx}>
                    "{claim.claim}" {claim.note ? `— ${claim.note}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Warnings / Missing Inputs */}
      {pkg.warnings && pkg.warnings.length > 0 && (
        <div className="rounded-control border border-warn/30 bg-warn/10 p-3 text-warn">
          <div className="flex items-start gap-2">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <div className="text-meta">
              <strong className="font-medium">Dikkat Edilmesi Gereken Noktalar:</strong>
              <ul className="mt-1 list-inside list-disc">
                {pkg.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Sub-tabs: Answers | CV Changes | Cover Letter */}
      <div className="flex gap-2 border-b border-subtle pb-2">
        <button
          type="button"
          onClick={() => setActiveTab("answers")}
          className={`rounded-control px-3 py-1.5 text-meta font-medium transition ${
            activeTab === "answers" ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary"
          }`}
        >
          Başvuru Soruları & Yanıtlar ({pkg.application_answers?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("cv_changes")}
          className={`rounded-control px-3 py-1.5 text-meta font-medium transition ${
            activeTab === "cv_changes" ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary"
          }`}
        >
          CV Uyarlama Denetimi ({pkg.cv_change_audit?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("cover_letter")}
          className={`rounded-control px-3 py-1.5 text-meta font-medium transition ${
            activeTab === "cover_letter" ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary"
          }`}
        >
          Ön Yazı
        </button>
      </div>

      {/* Tab: Application Answers */}
      {activeTab === "answers" && (
        <div className="stack-y-3">
          {pkg.application_answers && pkg.application_answers.length > 0 ? (
            pkg.application_answers.map((ans, idx) => {
              const draftValue =
                answerDrafts[ans.question] !== undefined ? answerDrafts[ans.question] : ans.proposed_answer;

              return (
                <div key={idx} className="rounded-control border border-subtle bg-surface p-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <strong className="text-body text-primary">{ans.question}</strong>
                    <Chip tone={answerClassificationTone(ans.classification)}>
                      {answerClassificationLabel(ans.classification)}
                    </Chip>
                  </div>

                  <p className="mt-1.5 whitespace-pre-line text-meta text-secondary">{ans.proposed_answer}</p>

                  {ans.warning && (
                    <p className="mt-1 flex items-center gap-1 text-micro text-warn">
                      <AlertTriangle size={12} />
                      {ans.warning}
                    </p>
                  )}

                  {ans.classification !== "safe_verified" && (
                    <div className="mt-3 flex gap-2 border-t border-subtle pt-2">
                      <Input
                        value={draftValue}
                        onChange={(val) => setAnswerDrafts((prev) => ({ ...prev, [ans.question]: val }))}
                        placeholder="Yanıtınızı girin veya düzenleyin…"
                        className="flex-1"
                      />
                      <Button
                        size="sm"
                        disabled={!online || !draftValue.trim() || resolveAnswerMutation.isPending}
                        onClick={() =>
                          resolveAnswerMutation.mutate({
                            question: ans.question,
                            answer: draftValue.trim(),
                          })
                        }
                      >
                        Kaydet & Onayla
                      </Button>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <Empty>Bu ilan için başvuru sorusu tanımlanmadı.</Empty>
          )}
        </div>
      )}

      {/* Tab: CV Changes Audit */}
      {activeTab === "cv_changes" && (
        <div className="stack-y-3">
          <p className="text-meta text-secondary">
            Master CV'niz korunarak ilandaki gereksinimlere göre yapılan düzenlemeler, sıralamalar ve vurgular aşağıda
            listelenmiştir.
          </p>
          {pkg.cv_change_audit && pkg.cv_change_audit.length > 0 ? (
            <div className="stack-y-2">
              {pkg.cv_change_audit.map((change, idx) => (
                <div key={idx} className="rounded-control border border-subtle bg-surface p-3">
                  <div className="flex items-center gap-2">
                    <Chip>{change.change_type}</Chip>
                    <span className="text-body font-medium text-primary">{change.original || "Değişiklik"}</span>
                  </div>
                  {change.reason && (
                    <p className="mt-1.5 text-meta text-secondary">
                      <strong className="text-muted">Gerekçe:</strong> {change.reason}
                    </p>
                  )}
                  {change.new && (
                    <p className="mt-1 text-meta text-primary font-mono bg-surface-sunken p-1.5 rounded">
                      {change.new}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <Empty>Özel bir CV değişikliği kaydedilmedi.</Empty>
          )}
        </div>
      )}

      {/* Tab: Cover Letter */}
      {activeTab === "cover_letter" && (
        <div className="stack-y-3">
          {pkg.cover_letter && (
            <div className="flex flex-wrap items-center gap-2">
              <Chip
                tone={
                  pkg.cover_letter_review?.status === "approved"
                    ? "ok"
                    : pkg.cover_letter_review?.status === "rejected"
                      ? "danger"
                      : "warn"
                }
              >
                {pkg.cover_letter_review?.status === "approved"
                  ? "İncelendi ve onaylandı"
                  : pkg.cover_letter_review?.status === "rejected"
                    ? "Reddedildi"
                    : "İnsan incelemesi bekliyor"}
              </Chip>
              <Button
                size="sm"
                disabled={!online || reviewCoverMutation.isPending}
                onClick={() => reviewCoverMutation.mutate("approved")}
              >
                Ön Yazıyı Onayla
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={!online || reviewCoverMutation.isPending}
                onClick={() => reviewCoverMutation.mutate("rejected")}
              >
                Reddet
              </Button>
            </div>
          )}
          <div className="flex justify-end">
            <Button size="sm" onClick={copyCoverLetter}>
              <Copy size={13} />
              Ön Yazıyı Kopyala
            </Button>
          </div>
          {pkg.cover_letter ? (
            <div className="rounded-control border border-subtle bg-surface p-4">
              <p className="whitespace-pre-line text-body text-primary leading-relaxed font-sans">{pkg.cover_letter}</p>
            </div>
          ) : (
            <Empty>Ön yazı oluşturulmadı.</Empty>
          )}
        </div>
      )}
    </div>
  );
}

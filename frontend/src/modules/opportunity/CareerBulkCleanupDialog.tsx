import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Checkbox, Chip, Modal, Spinner } from "@/core/ui";

interface ProtectionBreakdown {
  applied: number;
  shortlisted: number;
  interviews: number;
  manual: number;
  notes: number;
  linked: number;
}

interface CleanupPreview {
  matched_total: number;
  protected_total: number;
  deletable_total: number;
  breakdown: ProtectionBreakdown;
}

interface CleanupResult {
  deleted_count: number;
  skipped_count: number;
  suppressed_count: number;
}

export function CareerBulkCleanupDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [lowScore, setLowScore] = useState(true);
  const [dismissed, setDismissed] = useState(true);
  const [confirmed, setConfirmed] = useState(false);
  const [result, setResult] = useState<CleanupResult | null>(null);

  // Canlı önizleme
  const previewQuery = useQuery({
    queryKey: ["opportunity-cleanup-preview", lowScore, dismissed],
    queryFn: () =>
      api.post<CleanupPreview>("/opportunities/cleanup/preview", {
        low_score: lowScore,
        dismissed,
      }),
    enabled: open && (lowScore || dismissed) && result === null,
  });

  const preview = previewQuery.data;

  // Kalıcı silme mutasyonu
  const executeMutation = useMutation({
    mutationFn: () =>
      api.post<CleanupResult>("/opportunities/cleanup/execute", {
        low_score: lowScore,
        dismissed,
        confirm: true,
        expected_deletable: preview?.deletable_total,
      }),
    onSuccess: (data) => {
      setResult(data);
      invalidateAfter("opportunity.write");
    },
  });

  const handleClose = () => {
    setResult(null);
    setConfirmed(false);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Toplu İlan Temizliği"
      hint="Gereksiz veya elenmiş ilanları kalıcı olarak temizleyin"
      className="sm:max-w-xl"
    >
      {result ? (
        <div className="stack-y-4 py-2">
          <div className="flex items-center gap-3 text-ok">
            <CheckCircle2 size={24} className="shrink-0" />
            <div>
              <h3 className="text-heading text-primary">Toplu temizlik tamamlandı</h3>
              <p className="text-meta text-muted">
                İlanlar veritabanından kalıcı olarak kaldırıldı ve yeniden içeri alınmayı önlemek için engelleme kaydı eklendi.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 rounded-card border border-subtle bg-surface-sunken p-3 text-center">
            <div>
              <p className="text-meta text-muted">Silinen</p>
              <p className="text-title font-bold text-danger tabular-nums">{result.deleted_count}</p>
            </div>
            <div>
              <p className="text-meta text-muted">Korunan</p>
              <p className="text-title font-bold text-ok tabular-nums">{result.skipped_count}</p>
            </div>
            <div>
              <p className="text-meta text-muted">Engellenen</p>
              <p className="text-title font-bold text-primary tabular-nums">{result.suppressed_count}</p>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button variant="primary" onClick={handleClose}>
              Tamam
            </Button>
          </div>
        </div>
      ) : (
        <div className="stack-y-4">
          <p className="text-body text-secondary">
            Veritabanındaki eşleşen tüm ilanlar taranır. Başvurulmuş, kısa listeye alınmış, not veya bağlantı eklenmiş ilanlar
            otomatik olarak korunur.
          </p>

          <div className="stack-y-3 rounded-card border border-subtle bg-surface-sunken p-3">
            <p className="label-caps text-muted">Temizlik Kriterleri</p>
            <div className="stack-y-2">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <Checkbox
                  checked={lowScore}
                  onChange={(e) => {
                    setLowScore(e.target.checked);
                    setConfirmed(false);
                  }}
                />
                <div>
                  <span className="text-body font-medium text-primary">Düşük skorlu ilanlar (0 – 40 puan)</span>
                  <p className="text-meta text-muted">
                    Uygunluk skoru 40 veya altında kalan, profille uyuşmayan ilanlar.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer">
                <Checkbox
                  checked={dismissed}
                  onChange={(e) => {
                    setDismissed(e.target.checked);
                    setConfirmed(false);
                  }}
                />
                <div>
                  <span className="text-body font-medium text-primary">Elenmiş ilanlar (-1 puan veya elendi durumu)</span>
                  <p className="text-meta text-muted">
                    Manuel veya filtre kuralıyla elenen keşif kayıtları.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {previewQuery.isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Spinner label="İlanlar taranıyor…" />
            </div>
          ) : preview ? (
            <div className="stack-y-3">
              <div className="grid grid-cols-3 gap-2 rounded-card border border-subtle bg-surface-sunken p-3 text-center">
                <div>
                  <p className="text-meta text-muted">Eşleşen Toplam</p>
                  <p className="text-heading font-medium text-primary tabular-nums">{preview.matched_total}</p>
                </div>
                <div>
                  <p className="text-meta text-muted">Güvenle Korunan</p>
                  <p className="text-heading font-medium text-ok tabular-nums">{preview.protected_total}</p>
                </div>
                <div>
                  <p className="text-meta text-muted">Silinecek İlan</p>
                  <p className="text-heading font-medium text-danger tabular-nums">{preview.deletable_total}</p>
                </div>
              </div>

              {preview.protected_total > 0 && (
                <div className="rounded-card border border-subtle bg-surface-sunken p-3">
                  <div className="flex items-center gap-1.5 text-ok text-meta font-medium mb-1.5">
                    <ShieldCheck size={16} />
                    <span>Otomatik Korunan İlanlar ({preview.protected_total})</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {preview.breakdown.applied > 0 && (
                      <Chip tone="ok">Başvuru: {preview.breakdown.applied}</Chip>
                    )}
                    {preview.breakdown.shortlisted > 0 && (
                      <Chip tone="ok">Kısa liste: {preview.breakdown.shortlisted}</Chip>
                    )}
                    {preview.breakdown.interviews > 0 && (
                      <Chip tone="ok">Mülakat: {preview.breakdown.interviews}</Chip>
                    )}
                    {preview.breakdown.manual > 0 && (
                      <Chip tone="ok">Manuel eklenen: {preview.breakdown.manual}</Chip>
                    )}
                    {preview.breakdown.notes > 0 && (
                      <Chip tone="ok">Not içeren: {preview.breakdown.notes}</Chip>
                    )}
                    {preview.breakdown.linked > 0 && (
                      <Chip tone="ok">Bağlantılı: {preview.breakdown.linked}</Chip>
                    )}
                  </div>
                </div>
              )}

              {preview.deletable_total > 0 ? (
                <div className="stack-y-2 pt-2 border-t border-subtle">
                  <label className="flex items-center gap-2 cursor-pointer text-meta text-danger">
                    <Checkbox
                      checked={confirmed}
                      onChange={(e) => setConfirmed(e.target.checked)}
                    />
                    <span>
                      {preview.deletable_total} ilanın kalıcı olarak silinmesini ve tekrar içeri alınmamasını onaylıyorum.
                    </span>
                  </label>
                </div>
              ) : (
                <p className="text-meta text-muted text-center py-2">
                  Seçilen kriterlerle silinecek korumasız ilan bulunamadı.
                </p>
              )}
            </div>
          ) : null}

          {executeMutation.isError && (
            <div className="flex items-center gap-2 rounded-card border border-danger/40 bg-surface-sunken p-2.5 text-danger text-meta">
              <AlertTriangle size={16} className="shrink-0" />
              <span>İşlem gerçekleştirilemedi: {String(executeMutation.error)}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-subtle">
            <Button variant="ghost" onClick={handleClose}>
              Vazgeç
            </Button>
            <Button
              variant="danger"
              disabled={
                !confirmed ||
                !preview ||
                preview.deletable_total === 0 ||
                executeMutation.isPending
              }
              onClick={() => executeMutation.mutate()}
            >
              <Trash2 size={14} />
              <span>{executeMutation.isPending ? "Siliniyor…" : "Kalıcı Olarak Temizle"}</span>
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

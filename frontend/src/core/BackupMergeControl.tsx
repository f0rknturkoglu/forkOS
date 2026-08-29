import { invalidateAfter } from "@/core/invalidation";
import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ShieldAlert, UploadCloud } from "lucide-react";
import { inspectBackup, mergeRestore, type BackupInspect, type BackupMergeResult } from "@/core/backup";
import { Button, FileInput, cx, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";

/**
 * "Birleştirerek içe aktar" akışı (Faz 16).
 *
 * Dosya secilince ONCE `/backup/inspect` preflight'i calisir: versiyon,
 * tablo/satir sayilari, bilinmeyen tablolar, secret ayarlar ve butunluk
 * raporlanir. Kullanici raporu gorup onayladiktan sonra merge import
 * calisir. Bu UI, tam geri donus (disaster restore) DEGILDIR -- o islem
 * app disindadir (`make disaster-restore`), tek tik destructive buton yok.
 */
export function BackupMergeControl({ className }: { className?: string }) {
  const toast = useToast();
  const online = useOnline();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<BackupInspect | null>(null);

  const inspect = useMutation({
    mutationKey: ["backup-inspect"],
    mutationFn: (value: File) => inspectBackup(value),
    onSuccess: (report) => {
      setInspection(report);
      setFile(fileRef.current?.files?.[0] ?? null);
    },
    onError: (error: Error) => toast.push(`Yedek incelenemedi: ${error.message}`, { tone: "danger" }),
  });

  const merge = useMutation({
    mutationKey: ["backup-merge"],
    mutationFn: (value: File) => mergeRestore(value),
    onSuccess: (result: BackupMergeResult) => {
      invalidateAfter("backup.write");
      toast.push(`${result.restored} kayıt eklendi · ${result.skipped} kayıt atlandı (mevcutlara dokunulmadı).`, {
        tone: "ok",
      });
      setInspection(null);
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (error: Error) => toast.push(`Birleştirme başarısız: ${error.message}`, { tone: "danger" }),
  });

  const blocked = inspection?.integrity_ok === false || (inspection?.missing_sections.length ?? 0) > 0;

  async function pick(value: File) {
    setInspection(null);
    setFile(value);
    inspect.mutate(value);
  }

  async function confirmMerge() {
    if (!file) return;
    const ok = await confirmDialog({
      title: "Birleştirerek içe aktarılsın mı?",
      body:
        "Yedekteki kayıtlar EKLENİR; mevcut veriye dokunulmaz (çakışanlar atlanır). " +
        "Bu tam geri dönüş DEĞİLDİR. İstediğin kadar tekrarlayabilirsin — işlem güvenli ve idempotent.",
      confirmLabel: "Birleştirerek içe aktar",
    });
    if (ok) merge.mutate(file);
  }

  return (
    <div className={cx("flex flex-wrap items-center gap-2", className)}>
      <Button
        size="sm"
        onClick={() => fileRef.current?.click()}
        disabled={!online || inspect.isPending || merge.isPending}
      >
        <UploadCloud size={13} />
        {inspect.isPending ? "İnceleniyor…" : "Birleştirerek içe aktar"}
      </Button>
      <FileInput
        ref={fileRef}
        accept=".gz,.json,application/gzip,application/json"
        onChange={(event) => {
          const value = event.target.files?.[0];
          if (value) pick(value);
          event.target.value = "";
        }}
      />

      {inspection && (
        <div className="w-full rounded-card border border-subtle bg-surface-sunken px-3 py-2 text-meta">
          <p className="flex items-center gap-1.5 text-secondary">
            <ShieldAlert size={13} className="shrink-0 text-icon" /> Dosya incelendi
          </p>
          <ul className="mt-1 space-y-0.5 text-muted">
            <li>
              Format v{inspection.version}
              {inspection.app ? ` (${inspection.app})` : ""} · {inspection.table_counts.entities} entity ·{" "}
              {inspection.table_counts.links} link · {inspection.table_counts.events} event
            </li>
            {inspection.secret_settings > 0 && (
              <li className="text-warn">{inspection.secret_settings} secret ayar içeri alınmayacak.</li>
            )}
            {inspection.unknown_tables.length > 0 && (
              <li className="text-warn">Bilinmeyen tablolar yok sayılacak: {inspection.unknown_tables.join(", ")}</li>
            )}
            {inspection.integrity_ok === false && (
              <li className="text-danger">Bütünlük bozuk — manifest satır sayıları uyuşmuyor.</li>
            )}
          </ul>
          <p className="mt-1.5 text-muted">
            Birleştirme mevcut kayıtlara dokunmaz; yalnızca eksikler eklenir. Tam geri dönüş için felaket kurtarma akışı
            kullanılır (Sistem Durumu → Yedekleme notu).
          </p>
          <Button
            size="sm"
            variant="primary"
            className="mt-2"
            disabled={!online || blocked || merge.isPending}
            onClick={confirmMerge}
          >
            {merge.isPending ? "Aktarılıyor…" : "Evet, birleştir"}
          </Button>
        </div>
      )}
    </div>
  );
}

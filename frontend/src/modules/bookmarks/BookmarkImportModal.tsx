import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import type { Collection } from "@/core/types";
import { Button, Field, FileInput, Modal, Select, useToast } from "@/core/ui";

interface BookmarkImportModalProps {
  open: boolean;
  onClose: () => void;
}

export function BookmarkImportModal({ open, onClose }: BookmarkImportModalProps) {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileContent, setFileContent] = useState("");
  const [fileName, setFileName] = useState("");
  const [targetCollection, setTargetCollection] = useState<Collection>("read_later");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      setFileContent((event.target?.result as string) || "");
    };
    reader.readAsText(file);
  };

  const importMutation = useMutation({
    mutationFn: () =>
      api.post<{ imported: number }>("/bookmarks/import", {
        content: fileContent,
        collection: targetCollection,
      }),
    onSuccess: (res) => {
      invalidateAfter("bookmark.write");
      toast.push(`${res.imported} yer imi basariyla aktarildi`, { tone: "ok" });
      onClose();
      setFileContent("");
      setFileName("");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Bilinmeyen hata";
      toast.push(`Ice aktarma basarisiz: ${msg}`, { tone: "danger" });
    },
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Yer Imlerini Ice Aktar"
      hint="Netscape HTML (Chrome, Firefox, Safari) veya Pocket JSON dosyasi yukleyin"
      className="max-w-md"
      footer={
        <div className="flex w-full items-center justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={onClose}>
            Iptal
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={!fileContent.trim() || importMutation.isPending}
            onClick={() => importMutation.mutate()}
          >
            <Upload size={14} />
            <span>{importMutation.isPending ? "Aktariliyor..." : "Ice Aktar"}</span>
          </Button>
        </div>
      }
    >
      <div className="space-y-4 font-sans">
        <Field label="Dosya Sec (.html veya .json)">
          <div className="flex flex-col gap-2">
            <FileInput ref={fileInputRef} accept=".html,.htm,.json" onChange={handleFileChange} />
            <Button type="button" size="sm" variant="secondary" onClick={() => fileInputRef.current?.click()}>
              <Upload size={14} />
              <span>{fileName ? "Dosyayi Degistir" : "HTML veya JSON Dosyasi Sec"}</span>
            </Button>
          </div>
        </Field>

        {fileName && (
          <p className="text-meta text-primary font-mono bg-surface-sunken p-2 rounded-control border border-subtle">
            Secilen dosya: {fileName} ({Math.round(fileContent.length / 1024)} KB)
          </p>
        )}

        <Field label="Hedef Koleksiyon" hint="Ice aktarilan ogeler bu koleksiyona kaydedilir">
          <Select value={targetCollection} onChange={(c) => setTargetCollection(c as Collection)}>
            <option value="read_later">Daha Sonra Oku</option>
            <option value="inbox">Gelen Kutusu</option>
            <option value="archive">Arsiv</option>
            <option value="learning">Ogrenme</option>
            <option value="projects">Projeler</option>
          </Select>
        </Field>
      </div>
    </Modal>
  );
}

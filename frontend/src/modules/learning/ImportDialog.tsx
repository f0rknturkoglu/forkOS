/**
 * Konu agacini JSON'dan ice aktarma.
 *
 * Amac: agaci disarida (ornegin bir dil modeline yazdirarak) uretip buraya
 * yapistirmak. Bu yuzden ekran, kopyalanabilir bir SOZLESME metni tasir --
 * modele ne isteyecegini yazmak kullanicinin isi olmasin.
 *
 * Ayni JSON iki kez yuklenirse kopya olusmaz (backend baslikla eslestirir),
 * bu yuzden "gelistirilmis surumu tekrar yukle" guvenli bir akistir.
 */
import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Copy, FileUp, Upload, X } from "lucide-react";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Chip, Field, FileInput, Input, Section, Select, Textarea, cx } from "@/core/ui";
import type { StudyArea } from "@/core/types";
import { useOnline } from "@/lib/hooks";

interface ImportResult {
  area_id: string;
  area_title: string;
  topics_created: number;
  topics_matched: number;
  resources_created: number;
  resources_skipped: number;
}

/** Yapay zekaya verilecek istem + sema. Tek yerde durur ki sozlesme sapmasin. */
const IMPORT_PROMPT = `Bana bir çalışma konusu ağacı üret ve SADECE JSON döndür.

Şema:
{
  "area": "Alan adı",
  "topics": [
    {
      "title": "Konu başlığı",
      "status": "not_started" | "in_progress" | "done",
      "target_min": dakika (isteğe bağlı),
      "resources": [
        { "title": "Kaynak adı", "url": "https://...", "kind": "link|video|article|course|book|doc|exercise" }
      ],
      "children": [ ...aynı yapıda alt konular... ]
    }
  ]
}

Kurallar:
- Şemada olmayan alan EKLEME (fazladan alan reddedilir).
- En fazla 500 konu, en fazla 6 seviye iç içe.
- "title" zorunlu; diğer her şey isteğe bağlı.

Konu: <buraya ne öğrenmek istediğini yaz>`;

const EXAMPLE = `{
  "area": "Makine Öğrenmesi",
  "topics": [
    {
      "title": "Doğrusal Modeller",
      "status": "in_progress",
      "resources": [
        { "title": "ISLR bölüm 3", "url": "https://www.statlearning.com", "kind": "book" }
      ],
      "children": [{ "title": "Regularizasyon" }]
    }
  ]
}`;

export function ImportDialog({ areas, onClose }: { areas: StudyArea[]; onClose: () => void }) {
  const [text, setText] = useState("");
  const [areaId, setAreaId] = useState("");
  const [newArea, setNewArea] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [copied, setCopied] = useState(false);
  const file = useRef<HTMLInputElement | null>(null);
  const online = useOnline();

  const runImport = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(text);
      } catch (cause) {
        throw new Error(`JSON okunamadı: ${(cause as Error).message}`);
      }
      // Alan secimi govdedeki "area" alanini EZER -- kullanici burada ne
      // sectiyse o gecerlidir.
      const body: Record<string, unknown> = { ...parsed };
      if (areaId) {
        body.area_id = areaId;
        delete body.area;
      } else if (newArea.trim()) {
        body.area = newArea.trim();
        delete body.area_id;
      }
      return api.post<ImportResult>("/study/import", body);
    },
    onMutate: () => {
      setError(null);
      setResult(null);
    },
    onSuccess: (data) => {
      setResult(data);
      invalidateAfter("study.write");
    },
    onError: (cause: Error) => setError(cause.message),
  });

  const readFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const picked = event.target.files?.[0];
    if (!picked) return;
    picked
      .text()
      .then((content) => {
        setText(content);
        setError(null);
      })
      .catch((cause: Error) => setError(`Dosya okunamadı: ${cause.message}`));
  };

  const copyPrompt = () => {
    navigator.clipboard
      ?.writeText(IMPORT_PROMPT)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1800);
      })
      .catch(() => setError("Panoya kopyalanamadı."));
  };

  return (
    <Section
      title="JSON ile konu ağacı yükle"
      hint="Aynı dosyayı tekrar yüklemek kopya oluşturmaz"
      action={
        <Button size="sm" onClick={onClose}>
          <X size={13} /> Kapat
        </Button>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-3">
          <Field label="JSON">
            <Textarea value={text} onChange={setText} rows={14} placeholder={EXAMPLE} className="w-full font-mono" />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Hedef alan" hint="Boş bırakırsan JSON'daki “area” kullanılır">
              <Select value={areaId} onChange={setAreaId} ariaLabel="Hedef alan" className="w-full">
                <option value="">— JSON'daki alan —</option>
                {areas.map((area) => (
                  <option key={area.id} value={area.id}>
                    {area.title}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="ya da yeni alan adı">
              <Input
                value={newArea}
                onChange={setNewArea}
                placeholder="Makine Öğrenmesi"
                disabled={Boolean(areaId)}
                className="w-full"
              />
            </Field>
          </div>

          <div className="flex flex-wrap gap-2">
            <FileInput ref={file} accept="application/json,.json" onChange={readFile} />
            <Button onClick={() => file.current?.click()}>
              <FileUp size={14} /> Dosya seç
            </Button>
            <Button
              variant="primary"
              disabled={!online || !text.trim() || runImport.isPending}
              onClick={() => runImport.mutate()}
            >
              <Upload size={14} /> Yükle
            </Button>
          </div>

          {error && (
            <p className="rounded-card border border-danger-border bg-danger-surface px-3 py-2 text-meta text-danger">
              {error}
            </p>
          )}
          {result && (
            <div className="rounded-card border border-ok-border bg-ok-surface px-3 py-2 text-meta text-ok">
              <strong>{result.area_title}</strong> güncellendi — {result.topics_created} yeni konu,{" "}
              {result.topics_matched} eşleşen konu, {result.resources_created} yeni kaynak
              {result.resources_skipped > 0 && `, ${result.resources_skipped} zaten vardı`}.
            </div>
          )}
        </div>

        <aside className="space-y-2 rounded-card border border-subtle bg-surface-sunken p-3">
          <div className="flex items-center gap-2">
            <span className="label-caps text-secondary">Yapay zekaya sor</span>
            <Button size="sm" onClick={copyPrompt} className={cx(copied && "border-ok text-ok")}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Kopyalandı" : "İstemi kopyala"}
            </Button>
          </div>
          <p className="text-meta text-secondary">
            İstemi kopyala, bir dil modeline ver, dönen JSON'u sol tarafa yapıştır.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <Chip size="xs">title zorunlu</Chip>
            <Chip size="xs">en fazla 500 konu</Chip>
            <Chip size="xs">en fazla 6 seviye</Chip>
            <Chip size="xs">fazladan alan reddedilir</Chip>
          </div>
          <pre className="mt-2 max-h-64 overflow-auto rounded-control border border-subtle bg-surface p-2.5 font-mono text-micro leading-4 text-secondary">
            {EXAMPLE}
          </pre>
        </aside>
      </div>
    </Section>
  );
}

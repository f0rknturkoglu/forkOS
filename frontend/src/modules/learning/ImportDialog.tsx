/**
 * Konu agacini JSON'dan ice aktarma (Faz 9).
 *
 * Amac: agaci disarida (ornegin bir dil modeline yazdirarak) uretip buraya
 * yapistirmak. Bu yuzden ekran, kopyalanabilir bir SOZLESME metni tasir --
 * modele ne isteyecegini yazmak kullanicinin isi olmasin.
 *
 * Akis iki adimlidir ve bilinclidir:
 *   1) "Onizleme" (`POST /study/import/preview`) hicbir sey YAZMAZ; yalnizca
 *      ne olacagini soyler (yeni/eslesen alan, eklenecek/guncellenecek
 *      konular, cakismalar, kaynak sayaclari).
 *   2) "Uygula" (`POST /study/import`) yalnizca GORULEN onizleme icin
 *      etkinlesir; girdi degisirse onizleme bayatlar ve dugme tekrar kapanir.
 *
 * `prune` varsayilan KAPALI ve ayri onaylidir: silmez, arsivler.
 * Istem metni yalnizca PANOYA kopyalanir; uygulama disariya veri gondermez.
 */
import { useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Copy, FileUp, Eye, Upload, X } from "lucide-react";
import type { components } from "@/generated/api-schema";
import { api } from "@/core/api";
import { invalidateAfter } from "@/core/invalidation";
import { Button, Checkbox, Chip, Field, FileInput, Input, Modal, Select, Textarea, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { normalizeImportTree } from "./importTree";

type StudyArea = components["schemas"]["StudyAreaOut"];
type ImportPreview = components["schemas"]["ImportPreviewOut"];
type ImportResult = components["schemas"]["TopicImportOut"];
type ImportNode = components["schemas"]["ImportNodePreview"];
type ImportConflict = components["schemas"]["ImportConflictOut"];

/** Onizleme listelerinde cizilen satir sayisi; kalan sayi olarak yazilir. */
const PREVIEW_ROWS = 8;

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

export function ImportDialog({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: (areaId: string) => void;
}) {
  const online = useOnline();
  const toast = useToast();
  const file = useRef<HTMLInputElement | null>(null);

  const [text, setText] = useState("");
  const [areaId, setAreaId] = useState("");
  const [newArea, setNewArea] = useState("");
  const [updateExisting, setUpdateExisting] = useState(true);
  const [prune, setPrune] = useState(false);
  const [stripPrefix, setStripPrefix] = useState(false);
  const [preview, setPreview] = useState<{ data: ImportPreview; signature: string } | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [fileNotice, setFileNotice] = useState<string | null>(null);

  const areas = useQuery({
    queryKey: ["study-areas", "import"],
    queryFn: () => api.get<StudyArea[]>("/study/areas"),
    enabled: open,
  });

  // Onizleme yalnizca bu girdiler degismediyse gecerlidir; biri degisirse
  // "Uygula" kapanir (bayat diff uygulanmaz).
  const signature = JSON.stringify([text, areaId, newArea, updateExisting, stripPrefix, prune]);
  const freshPreview = preview?.signature === signature ? preview.data : null;

  /** Istek govdesi: yalnizca sema alanlari gider (backend fazladan alan reddeder). */
  const payload = (): Record<string, unknown> => {
    let parsed: Record<string, unknown>;
    try {
      parsed = normalizeImportTree(JSON.parse(text));
    } catch (cause) {
      throw new Error(`JSON okunamadı: ${(cause as Error).message}`);
    }
    const topics = parsed.topics;
    if (!Array.isArray(topics) || topics.length === 0) {
      throw new Error('JSON içinde boş olmayan bir "topics" dizisi olmalı.');
    }
    const body: Record<string, unknown> = {
      topics,
      update_existing: updateExisting,
      strip_common_prefix: stripPrefix,
      prune,
    };
    if (areaId) body.area_id = areaId;
    else if (newArea.trim()) body.area = newArea.trim();
    else if (typeof parsed.area === "string" && parsed.area.trim()) body.area = parsed.area.trim();
    else throw new Error('Hedef alan seç ya da JSON\'a "area" ekle.');
    return body;
  };

  const runPreview = useMutation({
    mutationFn: (input: { body: Record<string, unknown>; signature: string }) =>
      api.post<ImportPreview>("/study/import/preview", input.body),
    onSuccess: (data, variables) => {
      setPreview({ data, signature: variables.signature });
      setResult(null);
      setError(null);
      toast.push(`Önizleme hazır: ${data.totals.nodes} konu. Eklemek için Uygula’ya bas.`, { tone: "ok" });
    },
    onError: (cause: Error) => {
      setError(cause.message);
      toast.push(`Önizleme başarısız: ${cause.message}`, { tone: "danger" });
    },
  });

  const runImport = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<ImportResult>("/study/import", body),
    onSuccess: (data) => {
      setResult(data);
      setError(null);
      setFileNotice(null);
      invalidateAfter("study.write");
      toast.push(
        data.topics_created +
          data.resources_created +
          data.topics_updated +
          data.resources_updated +
          data.topics_archived +
          data.resources_archived ===
          0
          ? `${data.area_title}: tüm konular ve kaynaklar zaten mevcut; kopya oluşturulmadı.`
          : `${data.area_title}: ${data.topics_created} yeni konu, ${data.resources_created} yeni kaynak; ${data.topics_updated} konu ve ${data.resources_updated} kaynak güncellendi.`,
        { tone: "ok" },
      );
    },
    onError: (cause: Error) => {
      setError(cause.message);
      toast.push(`İçe aktarma başarısız: ${cause.message}`, { tone: "danger" });
    },
  });

  const startPreview = () => {
    try {
      runPreview.mutate({ body: payload(), signature });
    } catch (cause) {
      setError((cause as Error).message);
      setPreview(null);
    }
  };

  const startImport = () => {
    try {
      runImport.mutate(payload());
    } catch (cause) {
      setError((cause as Error).message);
    }
  };

  const readFile = (event: ChangeEvent<HTMLInputElement>) => {
    if (runPreview.isPending || runImport.isPending) return;
    const picked = event.target.files?.[0];
    if (!picked) return;
    event.target.value = "";
    setFileNotice(`${picked.name} okunuyor…`);
    picked
      .text()
      .then((content) => {
        normalizeImportTree(JSON.parse(content));
        setText(content);
        setPreview(null);
        setResult(null);
        setError(null);
        const message = `${picked.name} okundu. Henüz eklenmedi; önce Önizle, ardından Uygula’ya bas.`;
        setFileNotice(message);
        toast.push(message, { tone: "ok" });
      })
      .catch((cause: Error) => {
        setText("");
        setPreview(null);
        setResult(null);
        setFileNotice(null);
        const message = `Dosya okunamadı: ${cause.message}`;
        setError(message);
        toast.push(message, { tone: "danger" });
      });
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

  const busy = runPreview.isPending || runImport.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="JSON ile konu ağacı yükle"
      hint="Önizlemeden sonra uygula; aynı dosyayı tekrar yüklemek kopya oluşturmaz"
      className="sm:max-w-5xl [&>footer]:sticky [&>footer]:bottom-0 [&>footer]:z-10 [&>footer]:bg-surface"
      footer={
        result ? (
          <div className="sticky bottom-0 flex justify-end gap-2 bg-surface">
            <span role="status" className="mr-auto text-meta text-ok">
              İçe aktarma tamamlandı · {result.area_title}
            </span>
            <Button variant="primary" onClick={() => onDone(result.area_id)}>
              Tamam
            </Button>
          </div>
        ) : (
          <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 bg-surface">
            <span role="status" className="mr-auto text-meta text-secondary">
              {busy
                ? "İşlem sürüyor…"
                : error
                  ? "İşlem tamamlanmadı; hata ayrıntısını kontrol et."
                  : freshPreview
                    ? "Önizleme hazır. Uygula ile ekle."
                    : "1. JSON seç · 2. Önizle · 3. Uygula"}
            </span>
            <Button onClick={onClose}>Kapat</Button>
            <Button disabled={!online || !text.trim() || busy} onClick={startPreview}>
              <Eye size={14} /> Önizle
            </Button>
            <Button variant="primary" disabled={!online || !freshPreview || busy} onClick={startImport}>
              <Upload size={14} /> Uygula
            </Button>
          </div>
        )
      }
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 stack-y-3 lg:col-span-2">
          {fileNotice && (
            <p
              role="status"
              className="rounded-control border border-accent bg-accent-surface p-3 text-meta text-primary"
            >
              {fileNotice}
            </p>
          )}
          <Field label="JSON" hint="Ya da dosya seç">
            <Textarea
              value={text}
              onChange={(next) => {
                // Onizleme SILINMEZ: eski diff "gecersiz" olarak gorunur ve
                // "Uygula" kapanir; kullanici neyi yeniden onizleyecegini gorur.
                setText(next);
                setFileNotice(null);
                setResult(null);
                setError(null);
              }}
              rows={14}
              disabled={busy}
              placeholder={EXAMPLE}
              ariaLabel="İçe aktarılacak JSON"
              className="font-mono"
            />
          </Field>

          <div className="flex flex-wrap items-center gap-2">
            <FileInput ref={file} accept="application/json,.json" onChange={readFile} />
            <Button size="sm" disabled={busy} onClick={() => file.current?.click()}>
              <FileUp size={13} /> Dosya seç
            </Button>
            {runPreview.isPending && (
              <span role="status" className="text-meta text-muted">
                Önizleme hazırlanıyor…
              </span>
            )}
            {runImport.isPending && (
              <span role="status" className="text-meta text-muted">
                İçe aktarılıyor…
              </span>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Hedef alan" hint="Boş bırakırsan JSON'daki “area” kullanılır">
              <Select value={areaId} onChange={setAreaId} ariaLabel="Hedef alan" className="w-full">
                <option value="">— JSON'daki alan —</option>
                {(areas.data ?? []).map((area) => (
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

          <div className="stack-y-2">
            <Checkbox
              checked={updateExisting}
              onChange={setUpdateExisting}
              label="Eşleşen konuları güncelle (durum, hedef süre, sıra)"
            />
            <div className="rounded-card border border-warn-border bg-warn-surface p-2.5">
              <Checkbox checked={prune} onChange={setPrune} label="Ağaçta olmayan konu ve kaynakları arşivle (prune)" />
              <p className="mt-1 text-meta text-warn">
                Silmez, arşivler; listede görünmezler. Geri almak için arşivden açman gerekir.
              </p>
            </div>
          </div>

          {error && (
            <p role="alert" aria-live="assertive" className="text-meta text-danger">
              {error}
            </p>
          )}

          {freshPreview ? (
            <PreviewPanel preview={freshPreview} stripPrefix={stripPrefix} onStripPrefixChange={setStripPrefix} />
          ) : (
            preview && (
              <p role="status" className="text-meta text-warn">
                Girdi değişti; önizleme geçersiz. Yeniden önizle.
              </p>
            )
          )}

          {result && (
            <div
              role="status"
              className="stack-y-1 rounded-card border border-ok-border bg-ok-surface p-3 text-meta text-ok"
            >
              <p className="text-body">
                <strong>{result.area_title}</strong> güncellendi.
              </p>
              <p>
                {result.topics_created} yeni konu, {result.topics_updated} güncellenen, {result.topics_matched} eşleşen
                konu; {result.resources_created} yeni kaynak, {result.resources_updated} güncellenen,{" "}
                {result.resources_skipped} zaten vardı.
              </p>
              {(result.topics_archived > 0 || result.resources_archived > 0) && (
                <p>
                  Arşivlenen: {result.topics_archived} konu, {result.resources_archived} kaynak.
                </p>
              )}
            </div>
          )}
        </div>

        <aside className="min-w-0 stack-y-2 self-start rounded-card border border-subtle bg-surface-sunken p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="label-caps text-secondary">Yapay zekaya sor</span>
            <Button size="sm" onClick={copyPrompt} className={cx(copied && "border-ok text-ok")}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Kopyalandı" : "İstemi kopyala"}
            </Button>
          </div>
          <p className="text-meta text-secondary">
            İstemi kopyala, bir dil modeline ver, dönen JSON'u sol tarafa yapıştır. Uygulama bu metni yalnızca panoya
            kopyalar; hiçbir yere göndermez.
          </p>
          <p className="text-meta text-secondary">
            Zenginleştirilmiş JSON desteklenir: kaynak türü, dil ve doğrulama bilgileri notlarda; uygulama ve tamamlama
            ölçütleri alıştırma kaynağında korunur.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <Chip size="xs">title zorunlu</Chip>
            <Chip size="xs">en fazla 500 konu</Chip>
            <Chip size="xs">en fazla 6 seviye</Chip>
            <Chip size="xs">fazladan alan reddedilir</Chip>
          </div>
          <pre className="mt-2 max-h-56 overflow-auto rounded-control border border-subtle bg-surface p-2.5 font-mono text-micro leading-4 text-secondary">
            {EXAMPLE}
          </pre>
          <p className="text-meta text-muted">
            <X size={12} className="inline" /> İçe aktarma yalnızca sen “Uygula” dediğinde yazılır; önizleme hiçbir
            kaydı değiştirmez.
          </p>
        </aside>
      </div>
    </Modal>
  );
}

/** Onizleme/diff: alan eslesmesi, konu listeleri, cakismalar ve sayaclar. */
function PreviewPanel({
  preview,
  stripPrefix,
  onStripPrefixChange,
}: {
  preview: ImportPreview;
  stripPrefix: boolean;
  onStripPrefixChange: (checked: boolean) => void;
}) {
  const totals = preview.totals;
  return (
    <div className="stack-y-3 rounded-card border border-subtle bg-surface-sunken p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone={preview.area.exists ? "accent" : "ok"}>{preview.area.exists ? "Eşleşen alan" : "Yeni alan"}</Chip>
        <span className="text-body text-primary">{preview.area.title}</span>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-meta sm:grid-cols-4">
        <PreviewStat label="Toplam düğüm" value={totals.nodes} />
        <PreviewStat label="Derinlik" value={totals.depth} />
        <PreviewStat label="Eklenecek konu" value={totals.creates} />
        <PreviewStat label="Güncellenecek konu" value={totals.updates} />
        <PreviewStat label="Eşleşen konu" value={totals.matches} />
        <PreviewStat label="Yeni kaynak" value={preview.resources_new} />
        <PreviewStat label="Zaten olan kaynak" value={preview.resources_duplicate} />
      </dl>

      <NodeList label="Eklenecek konular" nodes={preview.creates ?? []} />
      <NodeList label="Güncellenecek konular" nodes={preview.updates ?? []} changes />
      <NodeList label="Eşleşen konular" nodes={preview.matches ?? []} />
      <ConflictList label="Çakışmalar" conflicts={preview.conflicts ?? []} />
      <ConflictList label="Hatalı satırlar" conflicts={preview.invalid ?? []} />

      {preview.suggested_prefix && (
        <div className="rounded-card border border-subtle bg-surface p-2.5">
          <Checkbox
            checked={stripPrefix}
            onChange={onStripPrefixChange}
            label={`Ortak başlık önekini temizle: “${preview.suggested_prefix}”`}
          />
          <p className="mt-1 text-meta text-muted">
            Seçersen konu başlıklarından bu önek atılır; değişirse önizlemeyi yenile.
          </p>
        </div>
      )}
    </div>
  );
}

function PreviewStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="numeral text-secondary">{value}</dd>
    </div>
  );
}

function NodeList({ label, nodes, changes = false }: { label: string; nodes: ImportNode[]; changes?: boolean }) {
  if (nodes.length === 0) return null;
  const shown = nodes.slice(0, PREVIEW_ROWS);
  return (
    <div>
      <p className="label-caps text-secondary">
        {label} ({nodes.length})
      </p>
      <ul className="mt-1 stack-y-0.5">
        {shown.map((node) => (
          <li key={`${label}-${node.path}`} className="text-meta text-secondary">
            <span className="text-muted">{node.path}</span>
            {changes && node.changes && node.changes.length > 0 && ` — ${node.changes.join(", ")}`}
            {node.resources > 0 && ` · ${node.resources} kaynak`}
          </li>
        ))}
      </ul>
      {nodes.length > shown.length && (
        <p className="text-meta text-muted">… ve {nodes.length - shown.length} tane daha.</p>
      )}
    </div>
  );
}

function ConflictList({ label, conflicts }: { label: string; conflicts: ImportConflict[] }) {
  if (conflicts.length === 0) return null;
  const shown = conflicts.slice(0, PREVIEW_ROWS);
  return (
    <div role="alert">
      <p className="label-caps text-danger">
        {label} ({conflicts.length})
      </p>
      <ul className="mt-1 stack-y-0.5">
        {shown.map((conflict) => (
          <li key={`${label}-${conflict.path}`} className="text-meta text-danger">
            <span className="text-secondary">{conflict.path}</span> — {conflict.reason}
          </li>
        ))}
      </ul>
      {conflicts.length > shown.length && (
        <p className="text-meta text-muted">… ve {conflicts.length - shown.length} tane daha.</p>
      )}
    </div>
  );
}

import { useState } from "react";
import { Quote } from "lucide-react";

import { useSaveToLibrary } from "@/core/SaveToLibrary";
import type { MediaItem } from "@/core/types";
import { Button, Field, Input, Modal, Select, Textarea } from "@/core/ui";
import { externalLinks } from "./shared";

/** Alintinin baglami: kitap sayfasi, manga bolumu, film/podcast zaman kodu, serbest. */
type ContextKind = "free" | "page" | "chapter" | "time";

const CONTEXT_LABELS: Record<ContextKind, string> = {
  free: "Serbest metin",
  page: "Sayfa",
  chapter: "Bölüm / cilt",
  time: "Zaman kodu",
};

const CONTEXT_PLACEHOLDERS: Record<ContextKind, string> = {
  free: "örn. 2. baskı, 14. sahne",
  page: "örn. 45",
  chapter: "örn. 3. cilt, 12. bölüm",
  time: "örn. 01:23:45",
};

/** Baglami tek satirlik okunabilir oneke cevirir (storage: bookmark.note). */
function contextPrefix(kind: ContextKind, value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (kind === "page") return `s. ${trimmed}`;
  if (kind === "chapter") return trimmed;
  if (kind === "time") return trimmed;
  return trimmed;
}

/**
 * Medyadan alinti kaydetme.
 *
 * Ayri bir highlight tablosu ACMADIK: alinti metni `bookmark.selection`'ta,
 * baglami `bookmark.note`'unda durur ve kayit medyaya `highlights` iliskisiyle
 * baglanir (mevcut Entity/Link/Bookmark altyapisi yeterli).
 */
export function HighlightDialog({ item, open, onClose }: { item: MediaItem; open: boolean; onClose: () => void }) {
  const { save, online } = useSaveToLibrary();
  const [quote, setQuote] = useState("");
  const [kind, setKind] = useState<ContextKind>("free");
  const [context, setContext] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setQuote("");
    setKind("free");
    setContext("");
    setError(null);
  }

  async function submit() {
    if (!quote.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      // Alinti bir yer imidir: dis baglanti (yoksa saglayici arama adresi) URL olur.
      const url = externalLinks(
        item.kind,
        item.title,
        (item.meta ?? {}) as Record<string, unknown>,
        item.provider,
        item.provider_id,
        (item.provider_ids ?? {}) as Record<string, unknown>,
      )[0]?.[1];
      await save({
        url: url ?? "https://forkos.local/media",
        title: item.title,
        collection: "read_later",
        source: "manual",
        selection: quote.trim(),
        note: contextPrefix(kind, context),
        entity_id: item.id,
        relation: "highlights",
      });
      reset();
      onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Alıntı kaydedilemedi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Alıntı ekle"
      hint={item.title}
      footer={
        <div className="flex justify-end gap-2">
          <Button
            disabled={saving}
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Vazgeç
          </Button>
          <Button variant="primary" disabled={!online || saving || !quote.trim()} onClick={() => void submit()}>
            <Quote size={13} aria-hidden="true" /> Alıntıyı kaydet
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        <Field label="Alıntı">
          <Textarea rows={4} value={quote} onChange={setQuote} placeholder="Kitaptan/bölümden almak istediğin cümle…" />
        </Field>
        <div className="grid gap-3 sm:grid-cols-[160px_minmax(0,1fr)]">
          <Field label="Bağlam türü">
            <Select value={kind} onChange={(value) => setKind(value as ContextKind)} ariaLabel="Alıntı bağlam türü">
              {(Object.keys(CONTEXT_LABELS) as ContextKind[]).map((id) => (
                <option key={id} value={id}>
                  {CONTEXT_LABELS[id]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Bağlam" hint={kind === "time" ? "Saat:dakika:saniye biçiminde yaz." : undefined}>
            <Input
              value={context}
              onChange={setContext}
              placeholder={CONTEXT_PLACEHOLDERS[kind]}
              ariaLabel="Alıntı bağlamı"
              className="w-full"
            />
          </Field>
        </div>
        {!online && (
          <p role="status" className="text-meta text-muted">
            Çevrimdışıyken alıntı kaydedilemez.
          </p>
        )}
        {error && (
          <p role="alert" className="text-meta text-danger">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

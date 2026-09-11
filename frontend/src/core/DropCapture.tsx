import { invalidateAfter } from "@/core/invalidation";
import { useEffect, useRef, useState } from "react";
import { Download, FileText, Link2, ListChecks } from "lucide-react";
import { api } from "./api";
import { openCapture } from "./CaptureDialog";
import { useToast } from "./ui";
import { useOnline } from "@/lib/hooks";

/**
 * Pencereye birakilan seyi yakalar.
 *
 * Ayrimi birakilan icerik yapar, kullaniciya soru sorulmaz:
 *   baglanti -> gelen kutusuna yer imi (/capture, client_uuid ile idempotent)
 *   duz metin -> gorev (/todos)
 *   dosya     -> yerel belge olarak yuklenir (/documents/upload)
 *
 * Offline'da yazma kapali (plan bolum 7), o yuzden katman hic acilmaz.
 */

const URL_PATTERN = /https?:\/\/[^\s<>"']+/i;

type Kind = "link" | "text" | "file";

function readDrop(transfer: DataTransfer): { kind: Kind; value: string; file?: File } | null {
  if (transfer.files.length > 0) return { kind: "file", value: transfer.files[0].name, file: transfer.files[0] };

  const uri = transfer.getData("text/uri-list").trim();
  if (uri) {
    // uri-list yorum satiri icerebilir (# ile baslar).
    const first = uri
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line && !line.startsWith("#"));
    if (first) return { kind: "link", value: first };
  }

  const text = transfer.getData("text/plain").trim();
  if (!text) return null;
  const match = text.match(URL_PATTERN);
  return match ? { kind: "link", value: match[0] } : { kind: "text", value: text };
}

export function DropCapture() {
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);
  // dragenter/dragleave ic elemanlarda da tetikleniyor; sayac olmadan
  // katman her cocuk gecisinde titriyor.
  const depth = useRef(0);
  const toast = useToast();

  const online = useOnline();

  useEffect(() => {
    if (!online) return;

    const hasPayload = (event: DragEvent) =>
      Array.from(event.dataTransfer?.types ?? []).some(
        (type) => type === "Files" || type === "text/uri-list" || type === "text/plain",
      );

    const onEnter = (event: DragEvent) => {
      if (!hasPayload(event)) return;
      depth.current += 1;
      setActive(true);
    };
    const onOver = (event: DragEvent) => {
      if (!hasPayload(event)) return;
      event.preventDefault(); // olmazsa tarayici dosyayi kendi acar
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
    };
    const onLeave = () => {
      depth.current = Math.max(0, depth.current - 1);
      if (depth.current === 0) setActive(false);
    };
    const onDrop = async (event: DragEvent) => {
      if (!event.dataTransfer) return;
      event.preventDefault();
      depth.current = 0;
      setActive(false);

      const dropped = readDrop(event.dataTransfer);
      if (!dropped) return;

      if (dropped.kind === "file") {
        if (dropped.file) {
          setBusy(true);
          try {
            const form = new FormData();
            form.append("file", dropped.file);
            form.append("category", "other");
            const res = await api.post<{ title?: string }>("/documents/upload", form);
            invalidateAfter("document.write");
            toast.push(`"${res?.title || dropped.value}" belgelere eklendi.`, {
              tone: "ok",
              action: {
                label: "aç",
                run: () => {
                  location.hash = "/documents";
                },
              },
            });
          } catch {
            toast.push(`"${dropped.value}" yüklenemedi.`, { tone: "danger" });
          } finally {
            setBusy(false);
          }
          return;
        }
        toast.push(`"${dropped.value}" — dosya okunamadı.`, { tone: "warn" });
        return;
      }

      setBusy(true);
      try {
        if (dropped.kind === "link") {
          const result = await api.post<{ duplicate: boolean }>("/capture", {
            url: dropped.value,
            collection: "inbox",
            source: "drop",
            client_uuid: crypto.randomUUID(),
          });
          invalidateAfter("bookmark.write");
          toast.push(result.duplicate ? "Zaten kayıtlıydı — yine de gelen kutusunda." : "Gelen kutusuna eklendi", {
            tone: result.duplicate ? "warn" : "ok",
            action: {
              label: "aç",
              run: () => {
                location.hash = "/today?triage=inbox";
              },
            },
          });
        } else {
          // Metin birakma: evrensel yakalama kutusunu acar (Faz 22) --
          // kullanici Task/Note/Link turunu gorup secer, sessiz siniflandirma yok.
          openCapture({ text: dropped.value.slice(0, 500) });
        }
      } catch {
        toast.push("Yakalanamadı — yerel sunucuya ulaşılamıyor olabilir.", { tone: "danger" });
      } finally {
        setBusy(false);
      }
    };

    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragover", onOver);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, [online, toast]);

  if (!active && !busy) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-fullscreen flex items-center justify-center bg-canvas/80 p-6 backdrop-blur-sm"
    >
      <div className="rounded-overlay border-2 border-dashed border-accent bg-surface px-8 py-7 text-center shadow-overlay">
        <Download size={26} className="mx-auto text-accent" />
        <p className="mt-3  text-title text-primary">{busy ? "Kaydediliyor…" : "Bırak, yakalayayım"}</p>
        <ul className="mt-3 space-y-1 text-meta text-secondary">
          <li className="flex items-center justify-center gap-1.5">
            <Link2 size={13} className="text-icon" /> Bağlantı → gelen kutusu
          </li>
          <li className="flex items-center justify-center gap-1.5">
            <ListChecks size={13} className="text-icon" /> Metin → görev
          </li>
          <li className="flex items-center justify-center gap-1.5">
            <FileText size={13} className="text-icon" /> Dosya → belgeler
          </li>
        </ul>
      </div>
    </div>
  );
}

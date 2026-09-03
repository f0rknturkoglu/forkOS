/**
 * Not editoru: markdown yazma + canli onizleme + [[ ]] otomatik tamamlama.
 *
 * Wikilink ve #etiket AYRISTIRMASI BACKEND'DE yapilir (core/refs.py); burasi
 * yalnizca yazmayi kolaylastirir. Yani editorden gecmeyen bir yol (API'den
 * dogrudan yazma, import) da ayni baglari uretir -- kural tek yerde.
 */
import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Eye, Pencil, Save, X } from "lucide-react";
import { api, qs } from "./api";
import { invalidateAfter } from "./invalidation";
import { Markdown } from "./Markdown";
import { wikilinkTargets } from "./markdownParser";
import { Button, Chip, Input, Section, Textarea, cx } from "./ui";
import type { Entity, Note } from "./types";
import { useDebounced, useOnline } from "@/lib/hooks";

/** Imlecin hemen solunda kapanmamis bir "[[" var mi? Varsa yazilan parca. */
export function openWikilinkQuery(text: string, caret: number): string | null {
  const before = text.slice(0, caret);
  const start = before.lastIndexOf("[[");
  if (start === -1) return null;
  const fragment = before.slice(start + 2);
  // Kapanmis ya da satir atlamis: artik acik bir wikilink degil.
  if (fragment.includes("]]") || fragment.includes("\n")) return null;
  return fragment;
}

/** `[[parca` yerine `[[Baslik]]` koyar; imlecin yeni yerini de doner. */
export function completeWikilink(text: string, caret: number, title: string): { value: string; caret: number } {
  const start = text.slice(0, caret).lastIndexOf("[[");
  if (start === -1) return { value: text, caret };
  const inserted = `[[${title}]]`;
  return {
    value: text.slice(0, start) + inserted + text.slice(caret),
    caret: start + inserted.length,
  };
}

export function NoteEditor({
  note,
  relateTo,
  onDone,
  onCancel,
}: {
  /** Verilirse duzenleme, verilmezse yeni not. */
  note?: Note;
  /** Yeni not bu kayda baglanir (notes_about). */
  relateTo?: string;
  onDone?: (note: Note) => void;
  onCancel?: () => void;
}) {
  const [body, setBody] = useState(note?.body ?? "");
  const [tagText, setTagText] = useState((note?.tags ?? []).join(", "));
  const [mode, setMode] = useState<"write" | "preview">("write");
  const [caret, setCaret] = useState(0);
  const area = useRef<HTMLTextAreaElement | null>(null);
  const online = useOnline();

  const query = openWikilinkQuery(body, caret);
  const debounced = useDebounced(query ?? "", 150);
  const { data: candidates = [] } = useQuery({
    queryKey: ["search", "wikilink", debounced],
    enabled: query !== null && debounced.trim().length > 0,
    queryFn: () => api.get<Entity[]>("/search" + qs({ q: debounced, limit: 6 })),
  });

  const tags = tagText
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  const save = useMutation({
    mutationFn: () =>
      note
        ? api.patch<Note>(`/notes/${note.id}`, { body, tags })
        : api.post<Note>("/notes", { body, tags, relate_to: relateTo ?? null }),
    onSuccess: (saved) => {
      invalidateAfter("note.write");
      onDone?.(saved);
      if (!note) {
        setBody("");
        setTagText("");
      }
    },
  });

  const insert = (title: string) => {
    const next = completeWikilink(body, caret, title);
    setBody(next.value);
    setCaret(next.caret);
    // İmleci eklemenin sonuna al ki yazmaya devam edilebilsin.
    requestAnimationFrame(() => {
      area.current?.focus();
      area.current?.setSelectionRange(next.caret, next.caret);
    });
  };

  return (
    <Section
      title={note ? "Notu düzenle" : "Yeni not"}
      hint="[[bağlantı]] · #etiket · **markdown**"
      action={
        <div className="flex gap-1.5">
          <Button size="sm" variant={mode === "write" ? "primary" : "ghost"} onClick={() => setMode("write")}>
            <Pencil size={13} /> Yaz
          </Button>
          <Button size="sm" variant={mode === "preview" ? "primary" : "ghost"} onClick={() => setMode("preview")}>
            <Eye size={13} /> Önizle
          </Button>
        </div>
      }
    >
      {mode === "write" ? (
        <div className="relative">
          <Textarea
            ref={area}
            value={body}
            onChange={(value) => setBody(value)}
            onCaret={setCaret}
            rows={10}
            placeholder={"# Başlık\n\nNotun… [[Başka Konu]] ile bağla, #etiket ver."}
            className="w-full font-mono"
          />
          {query !== null && candidates.length > 0 && (
            <div className="absolute inset-x-0 bottom-2 z-popover mx-2 overflow-hidden rounded-overlay border border-subtle bg-surface shadow-overlay">
              {candidates.map((entity) => (
                <button
                  key={entity.id}
                  type="button"
                  onClick={() => insert(entity.title)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-meta text-secondary transition hover:bg-surface-hover hover:text-primary"
                >
                  <span className="min-w-0 flex-1 truncate">{entity.title}</span>
                  <Chip size="xs">{entity.type}</Chip>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="min-h-[10rem] rounded-card border border-subtle bg-surface-sunken p-3">
          <Markdown source={body} unresolved={[]} />
        </div>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <label className="block">
          <span className="mb-1 block text-meta text-secondary">
            Etiketler <span className="text-muted">(virgülle; gövdedeki #etiketlerle birleşir)</span>
          </span>
          <Input value={tagText} onChange={setTagText} placeholder="matematik, ders" className="w-full" />
        </label>
        <div className="flex gap-1.5">
          {onCancel && (
            <Button onClick={onCancel}>
              <X size={14} /> Vazgeç
            </Button>
          )}
          <Button variant="primary" disabled={!online || !body.trim() || save.isPending} onClick={() => save.mutate()}>
            <Save size={14} /> Kaydet
          </Button>
        </div>
      </div>

      {/* Yazarken hangi baglantilarin kuruldugu gorunsun. */}
      {wikilinkTargets(body).length > 0 && (
        <p className={cx("mt-2 flex flex-wrap items-center gap-1.5 text-meta text-muted")}>
          Bağlanacak:
          {wikilinkTargets(body).map((target) => (
            <Chip key={target} size="xs">
              {target}
            </Chip>
          ))}
        </p>
      )}
    </Section>
  );
}

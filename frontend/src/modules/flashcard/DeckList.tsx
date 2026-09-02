import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileUp, Layers, Plus, Trash2 } from "lucide-react";
import { Button, Chip, Empty, FileInput, IconButton, Input, RowList, Section, useToast } from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import { createDeck, deleteDeck, importDeck, listDecks } from "./api";
import { refreshFlashcards } from "./invalidate";
import type { FlashcardDeck } from "./types";

function DeckRow({
  deck,
  online,
  onOpen,
  onDelete,
}: {
  deck: FlashcardDeck;
  online: boolean;
  onOpen: (id: string) => void;
  onDelete: (deck: FlashcardDeck) => void;
}) {
  return (
    <li className="group min-w-0 px-1 py-2.5 transition hover:bg-surface-hover">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => onOpen(deck.id)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <Layers size={15} className="shrink-0 text-icon" />
          <span className="truncate text-body text-primary">{deck.title}</span>
          <span className="flex flex-wrap items-center gap-1.5">
            {deck.due_count > 0 && <Chip tone="danger">{deck.due_count} tekrar</Chip>}
            {deck.new_count > 0 && <Chip tone="accent">{deck.new_count} yeni</Chip>}
            <Chip variant="outline">{deck.card_count} kart</Chip>
          </span>
        </button>
        <IconButton
          title={`"${deck.title}" destesini sil`}
          disabled={!online}
          tone="danger"
          onClick={() => onDelete(deck)}
        >
          <Trash2 size={14} />
        </IconButton>
      </div>
    </li>
  );
}

export function DeckList({ onOpen }: { onOpen: (deckId: string) => void }) {
  const online = useOnline();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [importDeckName, setImportDeckName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: decks = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: listDecks,
  });

  const create = useMutation({
    mutationFn: () => createDeck(title.trim()),
    onSuccess: () => {
      setTitle("");
      refreshFlashcards();
      toast.push("Destek oluşturuldu.", { tone: "ok" });
    },
    onError: () => toast.push("Destek oluşturulamadı.", { tone: "danger" }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteDeck(id),
    onSuccess: () => {
      refreshFlashcards();
      toast.push("Destek silindi.", { tone: "ok" });
    },
    onError: () => toast.push("Destek silinemedi.", { tone: "danger" }),
  });

  const doImport = useMutation({
    mutationFn: () => importDeck(file as File, importDeckName.trim() || undefined),
    onSuccess: (result) => {
      setFile(null);
      setImportDeckName("");
      if (fileRef.current) fileRef.current.value = "";
      refreshFlashcards();
      const skippedNote = result.skipped > 0 ? ` (${result.skipped} atlandı)` : "";
      toast.push(`${result.added} kart "${result.deck_title}" destesine aktarıldı${skippedNote}.`, {
        tone: "ok",
      });
    },
    onError: (error: unknown) =>
      toast.push(`İçe aktarılamadı: ${error instanceof Error ? error.message : "dosya okunamadı"}`, {
        tone: "danger",
      }),
  });

  const confirmRemove = async (deck: FlashcardDeck) => {
    const ok = await confirmDialog({
      title: `"${deck.title}" destesini sil?`,
      body: `${deck.card_count} kart da kalici olarak silinir.`,
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(deck.id);
  };

  return (
    <div className="space-y-5">
      <Section title="Destekler" hint={decks.length ? `${decks.length} destek` : undefined}>
        {isLoading ? (
          <p className="py-6 text-center text-meta text-muted">Yükleniyor…</p>
        ) : decks.length === 0 ? (
          <Empty title="Henüz destek yok">
            İlk kart desteni oluştur ya da Anki (.apkg) / CSV dosyası içe aktar.
          </Empty>
        ) : (
          <RowList as="ul">
            {decks.map((deck) => (
              <DeckRow
                key={deck.id}
                deck={deck}
                online={online}
                onOpen={onOpen}
                onDelete={confirmRemove}
              />
            ))}
          </RowList>
        )}
      </Section>

      <Section title="Yeni destek" flat>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={title}
            onChange={setTitle}
            placeholder="Destek adı (örn. Almanca)"
            ariaLabel="Yeni destek adı"
            className="min-w-56 flex-1"
            onKeyDown={(event) => {
              if (event.key === "Enter" && title.trim() && online) create.mutate();
            }}
          />
          <Button
            variant="primary"
            disabled={!online || !title.trim() || create.isPending}
            onClick={() => create.mutate()}
          >
            <Plus size={14} /> Oluştur
          </Button>
        </div>
      </Section>

      <Section title="İçe aktar" flat>
        <p className="mb-2.5 text-meta text-muted">
          Anki paketi (.apkg) ya da CSV/TXT (front,back veya sekme ayraçlı) dosyası. Aynı isimli
          destek varsa kartlar oraya eklenir; medya dosyaları atlanır.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={importDeckName}
            onChange={setImportDeckName}
            placeholder="Destek adı (opsiyonel)"
            ariaLabel="İçe aktarılacak destek adı"
            className="min-w-44 flex-1"
          />
          <FileInput
            ref={fileRef}
            accept=".apkg,.csv,.txt"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <Button onClick={() => fileRef.current?.click()}>
            <FileUp size={14} /> Dosya seç
          </Button>
          <Button
            variant="primary"
            disabled={!online || !file || doImport.isPending}
            onClick={() => doImport.mutate()}
          >
            {file ? `Aktar: ${file.name}` : "Aktar"}
          </Button>
        </div>
      </Section>
    </div>
  );
}

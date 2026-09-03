import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ChevronLeft, Eye, EyeOff, Pencil, Play, Plus, Trash2 } from "lucide-react";
import { Button, Chip, Empty, IconButton, Input, RowList, Section, useToast } from "@/core/ui";
import { RelatedPanel } from "@/core/RelatedPanel";
import { confirmDialog } from "@/core/dialog";
import { useOnline } from "@/lib/hooks";
import { addCard, deleteCard, listCards, listDecks, patchCard, renameDeck } from "./api";
import { refreshFlashcards } from "./invalidate";
import { ReviewSession } from "./ReviewSession";
import type { FlashcardCard } from "./types";

function CardRow({
  card,
  online,
  onToggle,
  onDelete,
}: {
  card: FlashcardCard;
  online: boolean;
  onToggle: (card: FlashcardCard) => void;
  onDelete: (card: FlashcardCard) => void;
}) {
  return (
    <li className="group min-w-0 px-1 py-2.5 transition hover:bg-surface-hover">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-body text-primary">{card.front}</p>
          <p className="mt-0.5 text-meta text-secondary">{card.back}</p>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {card.reps > 0 && <Chip variant="outline">{card.interval_days} gün</Chip>}
            {card.suspended && <Chip tone="warn">Askıda</Chip>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton
            title={card.suspended ? "Tekrara aç" : "Askıya al"}
            disabled={!online}
            onClick={() => onToggle(card)}
          >
            {card.suspended ? <Eye size={14} /> : <EyeOff size={14} />}
          </IconButton>
          <IconButton
            title={`"${card.front}" kartını sil`}
            tone="danger"
            disabled={!online}
            onClick={() => onDelete(card)}
          >
            <Trash2 size={14} />
          </IconButton>
        </div>
      </div>
    </li>
  );
}

export function DeckDetail({ deckId, onBack }: { deckId: string; onBack: () => void }) {
  const online = useOnline();
  const toast = useToast();
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  // Tek destek ucu yok; baslik/ozet destek listesi uzerinden gelir.
  const { data: decks = [] } = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: listDecks,
  });
  const deck = decks.find((item) => item.id === deckId);

  const { data: cards = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks", deckId, "cards"],
    queryFn: () => listCards(deckId),
  });

  const create = useMutation({
    mutationFn: () => addCard(deckId, front.trim(), back.trim()),
    onSuccess: () => {
      setFront("");
      setBack("");
      refreshFlashcards();
    },
    onError: () => toast.push("Kart eklenemedi.", { tone: "danger" }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteCard(id),
    onSuccess: () => {
      refreshFlashcards();
      toast.push("Kart silindi.", { tone: "ok" });
    },
    onError: () => toast.push("Kart silinemedi.", { tone: "danger" }),
  });

  const toggle = useMutation({
    mutationFn: (card: FlashcardCard) => patchCard(card.id, { suspended: !card.suspended }),
    onSuccess: () => refreshFlashcards(),
  });

  const rename = useMutation({
    mutationFn: (title: string) => renameDeck(deckId, title),
    onSuccess: () => {
      setRenaming(false);
      refreshFlashcards();
      toast.push("Destek adı güncellendi.", { tone: "ok" });
    },
    onError: () => toast.push("Destek adı güncellenemedi.", { tone: "danger" }),
  });

  const confirmRemove = async (card: FlashcardCard) => {
    const ok = await confirmDialog({
      title: "Kart silinsin mi?",
      body: `"${card.front}" — ${card.back}`,
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) remove.mutate(card.id);
  };

  const closeReview = () => {
    setReviewing(false);
    // Tekrar sonrasi destek ozeti (due/new) ve kart listesi tazelenir.
    refreshFlashcards();
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <IconButton title="Desteklere dön" onClick={onBack}>
            <ChevronLeft size={16} />
          </IconButton>
          {renaming ? (
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={renameValue}
                onChange={setRenameValue}
                ariaLabel="Destek adı"
                className="min-w-52"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && renameValue.trim() && online) rename.mutate(renameValue.trim());
                }}
              />
              <Button
                variant="primary"
                size="sm"
                disabled={!online || !renameValue.trim() || rename.isPending}
                onClick={() => rename.mutate(renameValue.trim())}
              >
                <Check size={14} /> Kaydet
              </Button>
            </div>
          ) : (
            <>
              <h1 className="min-w-0 truncate font-serif text-title text-primary">{deck?.title ?? "Kartlar"}</h1>
              <IconButton
                title="Destek adını değiştir"
                onClick={() => {
                  setRenameValue(deck?.title ?? "");
                  setRenaming(true);
                }}
              >
                <Pencil size={14} />
              </IconButton>
            </>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {deck && deck.due_count > 0 && <Chip tone="danger">{deck.due_count} tekrar</Chip>}
          {deck && deck.new_count > 0 && <Chip tone="accent">{deck.new_count} yeni</Chip>}
          <Button variant="primary" disabled={!online || cards.length === 0} onClick={() => setReviewing(true)}>
            <Play size={14} /> Tekrar başlat
          </Button>
        </div>
      </div>

      {reviewing ? (
        <ReviewSession deckId={deckId} onClose={closeReview} />
      ) : (
        <>
          <Section title="Kart ekle" flat>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={front}
                onChange={setFront}
                placeholder="Ön yüz (soru)"
                ariaLabel="Kart ön yüzü"
                className="min-w-48 flex-1"
              />
              <Input
                value={back}
                onChange={setBack}
                placeholder="Arka yüz (cevap)"
                ariaLabel="Kart arka yüzü"
                className="min-w-48 flex-1"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && front.trim() && back.trim() && online) create.mutate();
                }}
              />
              <Button
                variant="primary"
                disabled={!online || !front.trim() || !back.trim() || create.isPending}
                onClick={() => create.mutate()}
              >
                <Plus size={14} /> Ekle
              </Button>
            </div>
          </Section>

          <Section title="Kartlar" hint={cards.length ? `${cards.length} kart` : undefined}>
            {isLoading ? (
              <p className="py-6 text-center text-meta text-muted">Yükleniyor…</p>
            ) : cards.length === 0 ? (
              <Empty title="Bu destekte kart yok">
                İlk kartı yukarıdaki formla ekle ya da destek listesinden CSV/Anki dosyası içe aktar.
              </Empty>
            ) : (
              <RowList as="ul">
                {cards.map((card) => (
                  <CardRow
                    key={card.id}
                    card={card}
                    online={online}
                    onToggle={(item) => toggle.mutate(item)}
                    onDelete={confirmRemove}
                  />
                ))}
              </RowList>
            )}
          </Section>

          <RelatedPanel entityId={deckId} title="Bağlı kayıtlar" />
        </>
      )}
    </div>
  );
}

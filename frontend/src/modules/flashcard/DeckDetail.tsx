import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ChevronLeft, Eye, EyeOff, Pencil, Play, Plus, Search, Trash2 } from "lucide-react";
import {
  Button,
  Checkbox,
  Chip,
  Empty,
  Field,
  FilterChip,
  IconButton,
  Input,
  RowList,
  Section,
  SkeletonRows,
  Textarea,
  useToast,
} from "@/core/ui";
import { RelatedPanel } from "@/core/RelatedPanel";
import { confirmDialog } from "@/core/dialog";
import { useDebounced, useOnline } from "@/lib/hooks";
import { addCard, deleteCard, listCards, listDecks, patchCard, renameDeck } from "./api";
import { EditCardDialog } from "./EditCardDialog";
import { refreshFlashcards } from "./invalidate";
import { ReviewSession } from "./ReviewSession";
import { SrsBar } from "./SrsBar";
import type { FlashcardCard } from "./types";

const FILTERS = [
  { id: "all", label: "Tümü" },
  { id: "due", label: "Tekrar Bekleyenler" },
  { id: "lapses", label: "Zorlandıklarım" },
  { id: "suspended", label: "Askıdakiler" },
] as const;
type Filter = (typeof FILTERS)[number]["id"];

function CardRow({
  card,
  online,
  onEdit,
  onToggle,
  onDelete,
}: {
  card: FlashcardCard;
  online: boolean;
  onEdit: (card: FlashcardCard) => void;
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
            {card.lapses > 0 && <Chip tone="danger">{card.lapses} kez unutuldu</Chip>}
            {card.suspended && <Chip tone="warn">Askıda</Chip>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <IconButton title={`"${card.front}" kartını düzenle`} disabled={!online} onClick={() => onEdit(card)}>
            <Pencil size={14} />
          </IconButton>
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
  const [reversible, setReversible] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [editing, setEditing] = useState<FlashcardCard | null>(null);
  const [reviewQueue, setReviewQueue] = useState<FlashcardCard[] | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const query = useDebounced(search.trim(), 250);

  // Tek destek ucu yok; baslik/ozet destek listesi uzerinden gelir.
  const { data: decks = [] } = useQuery({ queryKey: ["flashcard", "decks"], queryFn: () => listDecks() });
  const deck = decks.find((item) => item.id === deckId);

  const { data: cards = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks", deckId, "cards", filter, query],
    queryFn: () =>
      listCards(deckId, {
        due: filter === "due",
        onlyLapses: filter === "lapses",
        q: query,
      }),
  });

  const visible = useMemo(
    () => (filter === "suspended" ? cards.filter((card) => card.suspended) : cards),
    [cards, filter],
  );

  const create = useMutation({
    mutationFn: () => addCard(deckId, front.trim(), back.trim(), reversible),
    onSuccess: () => {
      setFront("");
      setBack("");
      setReversible(false);
      refreshFlashcards();
      toast.push("Kart eklendi.", { tone: "ok" });
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

  /** Tekrar oturumu: once vadesi gelenler + yeniler (backend kuyrugu). */
  const startReview = async () => {
    const queue = await listCards(deckId, { due: true });
    setReviewQueue(queue);
  };

  const closeReview = () => {
    setReviewQueue(null);
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
              <h1 className="min-w-0 truncate text-title text-primary">{deck?.title ?? "Kartlar"}</h1>
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
          <Button variant="primary" disabled={!online || cards.length === 0} onClick={() => void startReview()}>
            <Play size={14} /> Tekrar başlat
          </Button>
        </div>
      </div>

      {deck && <SrsBar deck={deck} />}

      {reviewQueue ? (
        <ReviewSession
          cards={reviewQueue}
          deckId={deckId}
          onClose={closeReview}
          onRepeatMissed={(missed) => setReviewQueue(missed)}
        />
      ) : (
        <>
          <Section title="Kart ekle" hint="Enter değil, Kaydet: uzun sorular tek satıra sığmaz" flat>
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label="Ön yüz (soru)">
                <Textarea
                  value={front}
                  onChange={setFront}
                  placeholder="Haus"
                  ariaLabel="Kart ön yüzü"
                  className="h-20"
                />
              </Field>
              <Field label="Arka yüz (cevap)">
                <Textarea
                  value={back}
                  onChange={setBack}
                  placeholder="Ev"
                  ariaLabel="Kart arka yüzü"
                  className="h-20"
                />
              </Field>
            </div>
            <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
              <Checkbox
                checked={reversible}
                onChange={setReversible}
                label="Çift yönlü kart oluştur (tersini de ekle)"
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

          <Section title="Kartlar" hint={visible.length ? `${visible.length} kart` : undefined}>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              {FILTERS.map((item) => (
                <FilterChip
                  key={item.id}
                  label={item.label}
                  active={filter === item.id}
                  onClick={() => setFilter(item.id)}
                />
              ))}
              <div className="relative min-w-[10rem] flex-1">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-icon"
                />
                <Input
                  value={search}
                  onChange={setSearch}
                  placeholder="Kart ara…"
                  ariaLabel="Kart ara"
                  className="pl-8"
                />
              </div>
            </div>

            {isLoading ? (
              <SkeletonRows rows={4} className="h-9" />
            ) : visible.length === 0 ? (
              <Empty title="Kart yok">
                {filter === "all" && !query
                  ? "İlk kartı yukarıdaki formla ekle ya da destek listesinden CSV/Anki dosyası içe aktar."
                  : "Bu filtreye uyan kart yok."}
              </Empty>
            ) : (
              <RowList as="ul">
                {visible.map((card) => (
                  <CardRow
                    key={card.id}
                    card={card}
                    online={online}
                    onEdit={setEditing}
                    onToggle={(item) => toggle.mutate(item)}
                    onDelete={confirmRemove}
                  />
                ))}
              </RowList>
            )}
          </Section>

          <RelatedPanel entityId={deckId} title="Bağlı kaynaklar" />
        </>
      )}

      <EditCardDialog card={editing} onClose={() => setEditing(null)} />
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { Layers, Play } from "lucide-react";
import { navigate } from "@/app/router";
import { Button, Chip, Section, Skeleton } from "@/core/ui";
import { listDecks } from "./api";

/**
 * Not sayfasindaki yan panel rozedi: bu nota bagli kart desteleri.
 *
 * Bag `link` tablosunda "studies"/"generated_from" iliskisidir (not -> deste);
 * backend `linked_to` filtresiyle tek cagride sorulur. Kart yoksa panel hic
 * cizilmez -- bos bir kutu not sayfasini kalabaliklastirmasin.
 */
export function NoteFlashcardPanel({ noteId }: { noteId: string }) {
  const { data: decks = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks", "linked", noteId],
    queryFn: () => listDecks(noteId),
  });

  if (isLoading) {
    return (
      <Section title="Kartlar">
        <Skeleton className="h-10 w-full" />
      </Section>
    );
  }
  if (decks.length === 0) return null;

  const total = decks.reduce((sum, deck) => sum + deck.card_count, 0);

  return (
    <Section title="Bu notun kartları" hint={`${total} kart`}>
      <ul className="space-y-2">
        {decks.map((deck) => (
          <li key={deck.id} className="flex items-center gap-2 text-meta">
            <Layers size={14} className="shrink-0 text-icon" />
            <span className="min-w-0 flex-1 truncate text-secondary">{deck.title}</span>
            {deck.due_count > 0 && <Chip tone="danger">{deck.due_count} tekrar</Chip>}
            <Chip variant="outline">{deck.card_count} kart</Chip>
            <Button size="sm" onClick={() => navigate(`/flashcard?deck=${deck.id}`)}>
              <Play size={13} /> Tekrar et
            </Button>
          </li>
        ))}
      </ul>
    </Section>
  );
}

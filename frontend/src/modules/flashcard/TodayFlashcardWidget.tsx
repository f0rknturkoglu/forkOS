import { useQuery } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { navigate } from "@/app/router";
import { Button, Chip, Empty, Section, Skeleton, cx } from "@/core/ui";
import { listDecks } from "./api";

/**
 * Bugun panelindeki kart hatirlaticisi: hangi destede kac tekrar bekliyor.
 *
 * Kartlar bir "okuma" isi degil, bitirilecek bir oturum: bu yuzden widget
 * sayiyi ve tek tiklamayla baslatma dugmesini tasir (Bugun'un sag sutunu).
 */
export function TodayFlashcardWidget() {
  const { data: decks = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: () => listDecks(),
  });

  const due = decks.filter((deck) => deck.due_count > 0 || deck.new_count > 0);
  const totalDue = due.reduce((sum, deck) => sum + deck.due_count, 0);
  const totalNew = due.reduce((sum, deck) => sum + deck.new_count, 0);

  if (isLoading) {
    return (
      <Section title="Kart tekrarı">
        <Skeleton className="h-16 w-full" />
      </Section>
    );
  }

  return (
    <Section
      title="Kart tekrarı"
      hint={totalDue + totalNew > 0 ? `${totalDue + totalNew} kart` : undefined}
      action={
        totalDue + totalNew > 0 ? (
          <Button size="sm" variant="primary" onClick={() => navigate("/flashcard?review=due")}>
            <Play size={13} /> Hemen çalış
          </Button>
        ) : undefined
      }
    >
      {due.length === 0 ? (
        <Empty>Bugün için bekleyen kart yok. Yeni kart ekleyerek desteleri büyütebilirsin.</Empty>
      ) : (
        <ul className="stack-y-1.5">
          {due.slice(0, 4).map((deck) => (
            <li key={deck.id}>
              <button
                type="button"
                onClick={() => navigate(`/flashcard?deck=${deck.id}`)}
                className={cx(
                  "flex w-full items-center gap-2 rounded-control px-2 py-1.5 text-left text-meta transition",
                  "text-secondary hover:bg-surface-hover hover:text-primary",
                )}
              >
                <span className="min-w-0 flex-1 truncate">{deck.title}</span>
                {deck.due_count > 0 && <Chip tone="danger">{deck.due_count} tekrar</Chip>}
                {deck.new_count > 0 && <Chip tone="accent">{deck.new_count} yeni</Chip>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

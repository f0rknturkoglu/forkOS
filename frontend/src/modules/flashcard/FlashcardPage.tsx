import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Flame, Layers, Play } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { Button, Chip, Empty, PageFrame, SkeletonRows } from "@/core/ui";
import {
  Workspace,
  WorkspacePaneHeader,
  WorkspaceRailButton,
  WorkspaceRailContent,
  WorkspaceRailGroup,
  WorkspaceScrollArea,
} from "@/core/workspace/Workspace";
import { DeckDetail } from "./DeckDetail";
import { DeckList } from "./DeckList";
import { ReviewSession } from "./ReviewSession";
import { listCards, listDecks, missedCards } from "./api";
import type { FlashcardCard } from "./types";

export function FlashcardPage() {
  const route = useHashRoute();
  // Deep-link: registry rotasi /flashcard?deck={id} buradan acilir.
  const [deckId, setDeckId] = useState(() => route.params.get("deck") ?? "");
  const reviewMode = route.params.get("review");
  const { data: decks = [] } = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: () => listDecks(),
  });
  const selected = decks.find((deck) => deck.id === deckId);

  /**
   * Oturum modu URL'de yasar: ?review=due (bugunun tekrarlari) ya da
   * ?review=missed (zayif noktalar). Komutlar ve Today widget'i buraya gelir.
   */
  const [session, setSession] = useState<{ cards: FlashcardCard[]; title: string } | null>(null);
  const dueReview = useQuery({
    queryKey: ["flashcard", "review", "due", deckId],
    queryFn: async () => {
      if (deckId) return listCards(deckId, { due: true });
      const queues = await Promise.all(decks.map((deck) => listCards(deck.id, { due: true })));
      return queues.flat();
    },
    enabled: reviewMode === "due",
  });
  const missedReview = useQuery({
    queryKey: ["flashcard", "review", "missed"],
    queryFn: () => missedCards(30),
    enabled: reviewMode === "missed",
  });

  useEffect(() => {
    if (reviewMode === "due" && dueReview.data) setSession({ cards: dueReview.data, title: "Bugünün tekrarı" });
  }, [reviewMode, dueReview.data]);
  useEffect(() => {
    if (reviewMode === "missed" && missedReview.data) {
      setSession({ cards: missedReview.data, title: "Zayıf noktalar" });
    }
  }, [reviewMode, missedReview.data]);

  const sessionLoading =
    (reviewMode === "due" && dueReview.isLoading) || (reviewMode === "missed" && missedReview.isLoading);
  const openDeck = (id: string) => {
    setDeckId(id);
    navigate(`/flashcard?deck=${id}`);
  };
  const closeDeck = () => {
    setDeckId("");
    navigate("/flashcard");
  };

  return (
    <PageFrame className="py-3">
      <Workspace
        railAt="lg"
        rail={
          decks.length ? (
            <WorkspaceRailContent className="max-h-56 lg:max-h-workspace-body">
              <WorkspaceRailGroup label="Destekler" hint={decks.length}>
                {decks.map((deck) => (
                  <WorkspaceRailButton
                    key={deck.id}
                    label={deck.title}
                    count={
                      deck.due_count
                        ? `${deck.due_count} tekrar`
                        : deck.new_count
                          ? `${deck.new_count} yeni`
                          : `${deck.card_count} kart`
                    }
                    active={deck.id === deckId}
                    icon={<Layers size={13} />}
                    onClick={() => openDeck(deck.id)}
                  />
                ))}
              </WorkspaceRailGroup>
            </WorkspaceRailContent>
          ) : undefined
        }
      >
        <WorkspacePaneHeader
          eyebrow="Kartlar"
          title={selected?.title ?? "Tekrar çalışma alanı"}
          hint={selected ? `${selected.card_count} kart` : `${decks.length} deste`}
          action={
            <div className="flex items-center gap-2">
              {selected?.due_count ? <Chip tone="danger">{selected.due_count} tekrar</Chip> : null}
              <Button size="sm" variant="ghost" onClick={() => navigate("/flashcard?review=missed")}>
                <Flame size={13} /> Zayıf noktalar
              </Button>
              <Button size="sm" variant="primary" onClick={() => navigate("/flashcard?review=due")}>
                <Play size={13} /> Bugünün tekrarı
              </Button>
            </div>
          }
        />
        <WorkspaceScrollArea className="p-3">
          {reviewMode ? (
            sessionLoading || !session ? (
              session ? null : (
                <SkeletonRows rows={5} className="h-16" />
              )
            ) : session.cards.length === 0 ? (
              <Empty variant="page" title="Kuyruk boş">
                {reviewMode === "missed"
                  ? "Henüz unutulmuş kart yok — tekrar etmeye devam."
                  : "Bugün için bekleyen kart yok."}
              </Empty>
            ) : (
              <ReviewSession
                cards={session.cards}
                title={session.title}
                onClose={() => navigate("/flashcard")}
                onRepeatMissed={(missed) => setSession({ cards: missed, title: "Zayıf noktalar" })}
              />
            )
          ) : deckId ? (
            <DeckDetail deckId={deckId} onBack={closeDeck} />
          ) : (
            <DeckList onOpen={openDeck} showDecks={false} />
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

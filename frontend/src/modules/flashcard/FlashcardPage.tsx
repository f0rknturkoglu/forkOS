import { useEffect, useRef, useState } from "react";
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
  WorkspaceToolbar,
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
  const decksQuery = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: () => listDecks(),
  });
  const decks = decksQuery.data ?? [];
  const returnTo = route.params.get("return") === "learning-review" ? "/learning?view=review" : "/flashcard";
  useEffect(() => {
    setDeckId(route.params.get("deck") ?? "");
  }, [route.params]);
  const selected = decks.find((deck) => deck.id === deckId);

  /**
   * Oturum modu URL'de yasar: ?review=due (bugunun tekrarlari) ya da
   * ?review=missed (zayif noktalar). Komutlar ve Today widget'i buraya gelir.
   */
  const [session, setSession] = useState<{ cards: FlashcardCard[]; title: string } | null>(null);
  const sessionKey = `${reviewMode ?? ""}:${deckId}`;
  const startedKey = useRef<string | null>(null);
  useEffect(() => {
    startedKey.current = null;
    setSession(null);
  }, [sessionKey]);
  const dueReview = useQuery({
    queryKey: ["flashcard", "review", "due", deckId, deckId ? "" : decks.map((deck) => deck.id).join(",")],
    queryFn: async () => {
      if (deckId) return listCards(deckId, { due: true });
      const queues = await Promise.all(decks.map((deck) => listCards(deck.id, { due: true })));
      return queues.flat();
    },
    enabled: reviewMode === "due" && (Boolean(deckId) || decksQuery.isSuccess),
  });
  const missedReview = useQuery({
    queryKey: ["flashcard", "review", "missed"],
    queryFn: () => missedCards(30),
    enabled: reviewMode === "missed",
  });

  useEffect(() => {
    if (reviewMode === "due" && dueReview.data && startedKey.current !== sessionKey) {
      startedKey.current = sessionKey;
      setSession({ cards: dueReview.data, title: "Bugünün tekrarı" });
    }
  }, [reviewMode, dueReview.data, sessionKey]);
  useEffect(() => {
    if (reviewMode === "missed" && missedReview.data && startedKey.current !== sessionKey) {
      startedKey.current = sessionKey;
      setSession({ cards: missedReview.data, title: "Zayıf noktalar" });
    }
  }, [reviewMode, missedReview.data, sessionKey]);

  const sessionError = reviewMode === "due" ? (decksQuery.error ?? dueReview.error) : missedReview.error;
  const retrySession = () => {
    if (reviewMode === "due") {
      void decksQuery.refetch();
      void dueReview.refetch();
    } else void missedReview.refetch();
  };
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
    <PageFrame>
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
        />
        <WorkspaceToolbar
          left={selected?.due_count ? <Chip tone="danger">{selected.due_count} tekrar</Chip> : null}
          right={
            <div className="flex items-center gap-2">
              {returnTo !== "/flashcard" && (
                <Button size="sm" variant="ghost" onClick={() => navigate(returnTo)}>
                  Günlük tekrara dön
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => navigate("/flashcard?review=missed")}>
                <Flame size={13} /> Zayıf noktalar
              </Button>
              <Button size="sm" variant="primary" onClick={() => navigate("/flashcard?review=due")}>
                <Play size={13} /> Bugünün tekrarı
              </Button>
            </div>
          }
        />
        <WorkspaceScrollArea className="p-4">
          {reviewMode ? (
            sessionError ? (
              <Empty variant="page" title="Tekrar kuyruğu yüklenemedi">
                <Button size="sm" onClick={retrySession}>
                  Yeniden dene
                </Button>
              </Empty>
            ) : sessionLoading || !session ? (
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
                onClose={() => navigate(returnTo)}
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

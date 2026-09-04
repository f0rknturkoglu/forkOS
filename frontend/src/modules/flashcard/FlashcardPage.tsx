import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import { navigate, useHashRoute } from "@/app/router";
import { Chip, PageFrame } from "@/core/ui";
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
import { listDecks } from "./api";

export function FlashcardPage() {
  const route = useHashRoute();
  // Deep-link: registry rotasi /flashcard?deck={id} buradan acilir.
  const [deckId, setDeckId] = useState(() => route.params.get("deck") ?? "");
  const { data: decks = [] } = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: listDecks,
  });
  const selected = decks.find((deck) => deck.id === deckId);
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
          action={selected?.due_count ? <Chip tone="danger">{selected.due_count} tekrar</Chip> : undefined}
        />
        <WorkspaceScrollArea className="p-3">
          {deckId ? (
            <DeckDetail deckId={deckId} onBack={closeDeck} />
          ) : (
            <DeckList onOpen={openDeck} showDecks={false} />
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

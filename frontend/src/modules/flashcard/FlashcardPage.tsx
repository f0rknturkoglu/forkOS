import { useState } from "react";
import { useHashRoute } from "@/app/router";
import { PageFrame, PageHeader } from "@/core/ui";
import { DeckDetail } from "./DeckDetail";
import { DeckList } from "./DeckList";

export function FlashcardPage() {
  const route = useHashRoute();
  // Deep-link: registry rotasi /flashcard?deck={id} buradan acilir.
  const [deckId, setDeckId] = useState(() => route.params.get("deck") ?? "");

  return (
    <PageFrame>
      <PageHeader title="Kartlar" />
      {deckId ? (
        <DeckDetail deckId={deckId} onBack={() => setDeckId("")} />
      ) : (
        <DeckList onOpen={setDeckId} />
      )}
    </PageFrame>
  );
}

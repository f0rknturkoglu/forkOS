import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Kbd, Section, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { listCards, reviewCard } from "./api";
import type { FlashcardCard } from "./types";

/** Derece -> (puan, etiket, klavye tusu). 0=Again, 1=Hard, 2=Good, 3=Easy. */
const GRADES = [
  { grade: 0, label: "Yine", key: "1" },
  { grade: 1, label: "Zor", key: "2" },
  { grade: 2, label: "İyi", key: "3" },
  { grade: 3, label: "Kolay", key: "4" },
] as const;

export function ReviewSession({
  deckId,
  onClose,
}: {
  deckId: string;
  onClose: () => void;
}) {
  const online = useOnline();
  // Sıradaki kartlar (due once, sonra yeni). Veri gelince donuyor: oturum
  // boyunca yeniden cekim listeyi kaydirmasin.
  const { data = [], isLoading } = useQuery({
    queryKey: ["flashcard", "decks", deckId, "queue"],
    queryFn: () => listCards(deckId, true),
  });
  const [session, setSession] = useState<FlashcardCard[] | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (!session && data.length > 0) setSession(data);
  }, [data, session]);

  const current = session?.[index];

  const review = useMutation({
    mutationFn: ({ cardId, grade }: { cardId: string; grade: number }) => reviewCard(cardId, grade),
    onSuccess: () => {
      setDone((value) => value + 1);
      if (session && index + 1 >= session.length) {
        setFinished(true);
        return;
      }
      setIndex((value) => value + 1);
      setRevealed(false);
    },
  });

  const grade = (value: number) => {
    if (!current || !revealed || review.isPending) return;
    review.mutate({ cardId: current.id, grade: value });
  };

  if (isLoading && !session) {
    return <p className="py-6 text-center text-meta text-muted">Tekrar kuyruğu yükleniyor…</p>;
  }

  if (finished) {
    return (
      <Section title="Tekrar bitti">
        <div className="py-4 text-center">
          <p className="font-serif text-title text-primary">{done} kart tekrar edildi</p>
          <p className="mt-1 text-meta text-muted">Oturum tamamlandı.</p>
          <div className="mt-4 flex justify-center gap-2">
            <Button variant="primary" onClick={onClose}>
              Kapat
            </Button>
          </div>
        </div>
      </Section>
    );
  }

  if (!session || !current) {
    return (
      <Section title="Tekrar">
        <p className="py-6 text-center text-meta text-muted">Sırada kart yok — hepsi güncel.</p>
      </Section>
    );
  }

  return (
    <Section
      title="Tekrar"
      hint={`${index + 1} / ${session.length}`}
      action={
        <Button size="sm" variant="ghost" onClick={onClose}>
          Durdur
        </Button>
      }
    >
      <div
        className="flex flex-col items-center gap-5 py-6"
        onKeyDown={(event) => {
          if (event.key === " " || event.key === "Enter") {
            event.preventDefault();
            if (!revealed) setRevealed(true);
            return;
          }
          const shortcut = GRADES.findIndex((entry) => entry.key === event.key);
          if (shortcut >= 0) grade(shortcut);
        }}
      >
        <div
          tabIndex={0}
          className="w-full max-w-xl cursor-pointer rounded-card border border-subtle bg-surface px-6 py-8 text-center outline-none focus-visible:ring-2 focus-visible:ring-accent"
          onClick={() => setRevealed(true)}
        >
          <p className="font-serif text-xl text-primary">{current.front}</p>
          {revealed && (
            <p className="mt-4 border-t border-subtle pt-4 text-body text-secondary">{current.back}</p>
          )}
          {!revealed && (
            <p className="mt-4 text-meta text-muted">Çevirmek için tıkla ya da boşluk</p>
          )}
        </div>

        <div className={cx("flex flex-wrap justify-center gap-2", !revealed && "invisible")} aria-hidden={!revealed}>
          {GRADES.map(({ grade: value, label, key }) => (
            <Button
              key={value}
              variant={value === 2 ? "primary" : "secondary"}
              disabled={!online || review.isPending}
              onClick={() => grade(value)}
            >
              <Kbd>{key}</Kbd> {label}
            </Button>
          ))}
        </div>
      </div>
    </Section>
  );
}

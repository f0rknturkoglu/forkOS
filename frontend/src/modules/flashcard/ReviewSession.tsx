import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Flame, RotateCcw } from "lucide-react";
import { Markdown } from "@/core/Markdown";
import { Button, Chip, Kbd, Section, cx } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { reviewCard } from "./api";
import { predictNextIntervals, type GradeTone } from "./srs";
import type { FlashcardCard } from "./types";

/** Derece -> buton varyanti (kirmizi -> yesil). */
const TONE_VARIANT: Record<GradeTone, "danger" | "warn" | "primary" | "ok"> = {
  danger: "danger",
  warn: "warn",
  primary: "primary",
  ok: "ok",
};

/**
 * Tekrar oturumu.
 *
 * Kart 3B cevrilir (perspective + rotateY): "one bak, cevir, derecelendir"
 * akisi tek bir fiziksel hareket olur. Derecelendirme butonlari karti
 * cevirmeden ONCE gizli, cevirdikten sonra her birinin ustunde SM-2'nin
 * hesapladigi sonraki aralik yazar (Anki'nin en cok sevilen davranisi).
 */
export function ReviewSession({
  cards,
  title = "Tekrar",
  deckId,
  onClose,
  onRepeatMissed,
}: {
  /** Oturum kuyrugu: cagiran taraf belirler (deste ya da cram). */
  cards: FlashcardCard[];
  title?: string;
  deckId?: string;
  onClose: () => void;
  /** Verilirse "yanlislari tekrar et" butonu bu kuyrukla yeni oturum baslatir. */
  onRepeatMissed?: (cards: FlashcardCard[]) => void;
}) {
  const online = useOnline();
  const [queue, setQueue] = useState<FlashcardCard[]>(cards);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const [done, setDone] = useState(0);
  const [again, setAgain] = useState<FlashcardCard[]>([]);

  useEffect(() => {
    setQueue(cards);
    setIndex(0);
    setRevealed(false);
    setFinished(false);
    setDone(0);
    setAgain([]);
  }, [cards]);

  const current = queue[index];

  const review = useMutation({
    mutationFn: ({ cardId, grade }: { cardId: string; grade: number }) => reviewCard(cardId, grade),
    onSuccess: (_result, variables) => {
      setDone((value) => value + 1);
      if (variables.grade === 0 && current) setAgain((rows) => [...rows, current]);
      if (index + 1 >= queue.length) {
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

  const predictions = useMemo(
    () =>
      current
        ? predictNextIntervals({
            interval_days: current.interval_days,
            ease: current.ease,
            isNew: current.due_at === null,
          })
        : [],
    [current],
  );

  // Klavye: bosluk/Enter cevirir, 1-4 derecelendirir. Metin alanlarinda susar.
  useEffect(() => {
    if (!current || finished) return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        if (!revealed) setRevealed(true);
        return;
      }
      const shortcut = predictions.findIndex((entry) => String(entry.grade + 1) === event.key);
      if (shortcut >= 0) grade(shortcut);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, finished, revealed, review.isPending, predictions]);

  if (finished) {
    const successRate = done > 0 ? Math.round(((done - again.length) / done) * 100) : 0;
    return (
      <Section title="Oturum tamamlandı">
        <div className="space-y-4 py-4 text-center">
          <CheckCircle2 size={28} className="mx-auto text-ok" />
          <p className="text-title text-primary">{done} kart tekrar edildi</p>
          <div className="flex flex-wrap items-center justify-center gap-2 text-meta">
            <Chip tone={successRate >= 80 ? "ok" : successRate >= 50 ? "warn" : "danger"}>
              %{successRate} hatırlandı
            </Chip>
            {again.length > 0 && <Chip tone="danger">{again.length} kez "Yine" dendi</Chip>}
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {again.length > 0 && onRepeatMissed && (
              <Button variant="warn" onClick={() => onRepeatMissed(again)}>
                <Flame size={14} /> Yanlış yapılan kartları şimdi tekrar et
              </Button>
            )}
            <Button variant="primary" onClick={onClose}>
              Kapat
            </Button>
            <Button
              onClick={() => {
                setQueue(cards);
                setIndex(0);
                setRevealed(false);
                setFinished(false);
                setDone(0);
                setAgain([]);
              }}
            >
              <RotateCcw size={14} /> Baştan
            </Button>
          </div>
        </div>
      </Section>
    );
  }

  if (!current) {
    return (
      <Section title={title}>
        <p className="py-6 text-center text-meta text-muted">Sırada kart yok — hepsi güncel.</p>
      </Section>
    );
  }

  const progress = queue.length > 0 ? (index / queue.length) * 100 : 0;

  return (
    <Section
      title={title}
      hint={`${index + 1} / ${queue.length}`}
      action={
        <Button size="sm" variant="ghost" onClick={onClose}>
          Durdur
        </Button>
      }
      bodyClassName="space-y-4"
    >
      {/* Oturum ilerlemesi: kalan kart sayisiyla birlikte. */}
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-control bg-surface-sunken">
          <div className="h-full rounded-control bg-accent transition-all" style={{ width: `${progress}%` }} />
        </div>
        <span className="shrink-0 text-meta tabular-nums text-muted">
          %{Math.round(progress)} · Kalan {queue.length - index} kart
        </span>
      </div>

      <div className="flex flex-col items-center gap-5 py-2">
        {/* 3B cevrilen kart: on ve arka ayni yuvada durur, kart donunce arka yuz gelir. */}
        <div
          role="button"
          tabIndex={0}
          aria-label={revealed ? "Kart cevabı" : "Kart sorusu — çevirmek için tıkla"}
          onClick={() => setRevealed((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              setRevealed((value) => !value);
            }
          }}
          className="w-full max-w-xl cursor-pointer outline-none [perspective:1000px] focus-visible:ring-2 focus-visible:ring-accent"
        >
          <div
            className={cx(
              "relative h-72 w-full transition-transform duration-500 [transform-style:preserve-3d]",
              revealed && "[transform:rotateY(180deg)]",
            )}
          >
            <CardFace side="front" text={current.front} />
            <CardFace side="back" text={current.back} />
          </div>
        </div>

        <p className="text-meta text-muted">
          {revealed ? (
            <>
              Derecelendirmek için <Kbd>1</Kbd>
              <Kbd>2</Kbd>
              <Kbd>3</Kbd>
              <Kbd>4</Kbd> ya da bir butona bas
            </>
          ) : (
            "Çevirmek için tıkla ya da boşluk"
          )}
        </p>

        <div className={cx("grid w-full max-w-xl grid-cols-2 gap-2 sm:grid-cols-4", !revealed && "invisible")}>
          {predictions.map((entry) => (
            <Button
              key={entry.grade}
              variant={TONE_VARIANT[entry.tone]}
              disabled={!online || review.isPending}
              onClick={() => grade(entry.grade)}
            >
              <Kbd>{entry.grade + 1}</Kbd> {entry.label}
              <span className="text-micro opacity-80">{entry.hint}</span>
            </Button>
          ))}
        </div>
      </div>

      {deckId && again.length > 0 && (
        <p className="text-center text-meta text-muted">Bu oturumda {again.length} kart "Yine" aldı.</p>
      )}
    </Section>
  );
}

/** Kartin tek yuzu. `backface-visibility` ile yalnizca bakan yuz gorunur. */
function CardFace({ side, text }: { side: "front" | "back"; text: string }) {
  const front = side === "front";
  return (
    <div
      className={cx(
        "absolute inset-0 overflow-y-auto rounded-card border border-subtle bg-surface px-6 py-6 shadow-card",
        "[backface-visibility:hidden]",
        !front && "[transform:rotateY(180deg)]",
      )}
    >
      <p className={cx("mb-3 text-micro uppercase tracking-wide", front ? "text-muted" : "text-accent")}>
        {front ? "Soru" : "Cevap"}
      </p>
      <Markdown source={text} className={cx("text-body", front ? "text-primary" : "text-secondary")} />
    </div>
  );
}

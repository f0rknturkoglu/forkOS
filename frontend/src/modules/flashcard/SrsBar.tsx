import type { FlashcardDeck } from "./types";

/**
 * Anki tarzi SRS dagilim cubugu: yeni (mavi) / tekrar bekleyen (kirmizi) /
 * olgun (yesil). Bir destenin "ne durumda" oldugunu tek bakista soyler.
 *
 * Renkler tema tokenlarindan gelir (bg-accent/danger/ok) -- sabit hex yok.
 */
export function SrsBar({ deck, className }: { deck: FlashcardDeck; className?: string }) {
  const segments = [
    { label: "yeni", value: deck.new_count, className: "bg-accent" },
    { label: "tekrar bekleyen", value: deck.due_count, className: "bg-danger" },
    {
      label: "olgun",
      // Olgun kart = araligi 21 gunu asan, vadesi gelmemis kartlar.
      value: Math.max(0, deck.card_count - deck.new_count - deck.due_count),
      className: "bg-ok",
    },
  ].filter((segment) => segment.value > 0);
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const barClass = `flex h-1.5 overflow-hidden rounded-control bg-surface-sunken ${className ?? ""}`;

  if (total === 0) return <div className={barClass} aria-hidden />;

  return (
    <div
      className={barClass}
      role="img"
      aria-label={`${deck.title}: ${segments.map((segment) => `${segment.value} ${segment.label}`).join(", ")}`}
    >
      {segments.map((segment) => (
        <span
          key={segment.label}
          title={`${segment.value} ${segment.label}`}
          className={segment.className}
          style={{ width: `${(segment.value / total) * 100}%` }}
        />
      ))}
    </div>
  );
}

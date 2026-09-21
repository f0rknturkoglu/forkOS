import { useState } from "react";
import { FeedStreamList, FeedSourceFailures } from "@/core/FeedStreamList";
import { FEED_FILTERS, useFeedStream, type FeedFilter } from "@/core/feedStream";
import { Section, cx } from "@/core/ui";

/**
 * Home bileşeni: Okuma akışının ÖZETİ.
 *
 * Akış mantığının tamamı `core/feedStream` içindedir; burada yalnız Home'a
 * uygun kompakt sunum var. Tam liste ve kaynak seçimi Okuma Akışı sayfasında
 * (`/feed`) -- burası "bugün okunacak ne var?" sorusunun kısa cevabı.
 */
export function FeedStreamWidget() {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const stream = useFeedStream(filter);

  return (
    <Section
      title="Okuma akışı"
      hint={
        <span className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          {FEED_FILTERS.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={filter === option.id}
              onClick={() => setFilter(option.id)}
              className={cx(
                "border-b transition",
                filter === option.id
                  ? "border-accent text-primary"
                  : "border-transparent text-muted hover:text-primary",
              )}
            >
              {option.label}
            </button>
          ))}
        </span>
      }
      action={
        <a href="#/feed" className="text-meta text-accent hover:underline">
          {stream.unread ? `${stream.unread} okunmamış` : "akış"} →
        </a>
      }
      bodyClassName="px-3.5 py-1"
    >
      <FeedSourceFailures failures={stream.failures} />
      {stream.items.length === 0 && stream.loading ? (
        <p className="px-2 py-4 text-center text-meta text-muted">Akış yükleniyor…</p>
      ) : (
        <FeedStreamList items={stream.items} />
      )}
    </Section>
  );
}

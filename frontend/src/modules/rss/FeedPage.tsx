import { useState } from "react";
import { Rss } from "lucide-react";
import { FeedStreamList, FeedSourceFailures } from "@/core/FeedStreamList";
import { FEED_FILTERS, useFeedStream, type FeedFilter } from "@/core/feedStream";
import { Button, PageFrame, Tabs } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";

/**
 * Okuma Akışı (`/feed`) — kendi başına açılabilen okuma yüzeyi.
 *
 * Home bileşeni (`today.feed-stream`) ile AYNI veri katmanını kullanır
 * (`core/feedStream`): tek bir fetch/birleştirme/hata semantiği vardır, ikinci
 * bir kopya yoktur. Burada sunum daha rahat: kaynak sekmeleri, kaynak
 * açıklamaları ve okuyucuya giden yol görünür.
 */
export function FeedPage() {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const stream = useFeedStream(filter);

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Kütüphane"
          title="RSS & Akış"
        >
          <Tabs
            value={filter}
            onChange={(next) => setFilter(next as FeedFilter)}
            items={FEED_FILTERS.map((option) => ({ id: option.id, label: option.label }))}
            ariaLabel="Akış kaynağı"
          />
        </WorkspacePaneHeader>

        <WorkspaceScrollArea className="min-w-0 overflow-x-hidden p-3">
          {stream.unread !== null && (
            <div className="mb-2 flex justify-end text-meta text-muted">
              <span>{stream.unread} okunmamış RSS yazısı</span>
            </div>
          )}

          <FeedSourceFailures failures={stream.failures} />

          <div className="min-w-0 max-w-full overflow-hidden rounded-card border border-subtle bg-surface px-3">
            {stream.items.length === 0 && stream.loading ? (
              <p className="px-3 py-8 text-center text-meta text-muted">Akış yükleniyor…</p>
            ) : (
              <FeedStreamList items={stream.items} empty="Bu kaynakta yeni bir şey yok." />
            )}
          </div>

          {stream.sources.some((source) => source.failed) && (
            <div className="mt-2 flex justify-end">
              <Button size="sm" onClick={() => stream.sources.forEach((source) => source.failed && source.retry())}>
                <Rss size={14} /> Başarısız kaynakları yeniden dene
              </Button>
            </div>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

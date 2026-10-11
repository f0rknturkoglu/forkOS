import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { FeedSourceFailures } from "@/core/FeedStreamList";
import { useFeedStream, type FeedFilter } from "@/core/feedStream";
import { Button, Input, PageFrame, Select, Tabs } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { useExperience, openSourceDiscovery } from "@/core/onboarding/experience";
import { EditorialFeed } from "./EditorialFeed";
export function FeedPage() {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const [limit, setLimit] = useState(24);
  const [bundleId, setBundleId] = useState("");
  const [date, setDate] = useState("");
  const experience = useExperience();
  const stream = useFeedStream(filter, { limit, bundleId, date });
  useEffect(() => {
    if (!stream.available.some((option) => option.id === filter)) setFilter("all");
  }, [filter, stream.available]);
  useEffect(() => {
    setLimit(24);
  }, [filter, bundleId, date]);
  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          title="Okuma akışı"
          action={
            <span data-onboarding="feed-sources">
              <Button onClick={openSourceDiscovery}>
                <Plus size={14} />
                Kaynaklar
              </Button>
            </span>
          }
        >
          <div className="flex flex-wrap items-center gap-3">
            <Tabs
              value={filter}
              onChange={(value) => setFilter(value as FeedFilter)}
              items={stream.available}
              ariaLabel="Akış kaynağı"
            />
            {Boolean(experience.data?.feed.bundles.length) && (
              <Select ariaLabel="Seçki" value={bundleId} onChange={setBundleId}>
                <option value="">Bütün seçkiler</option>
                {experience.data?.feed.bundles.map((bundle) => (
                  <option key={bundle.id} value={bundle.id}>
                    {bundle.title}
                  </option>
                ))}
              </Select>
            )}
            {filter === "hf" && (
              <Input type="date" ariaLabel="Daily Papers tarihi; boşsa son seçki" value={date} onChange={setDate} />
            )}
          </div>
        </WorkspacePaneHeader>
        <WorkspaceScrollArea className="min-w-0 overflow-x-hidden p-4 sm:p-5">
          {stream.unread !== null && <p className="mb-3 text-meta text-muted">{stream.unread} okunmamış RSS yazısı</p>}
          <FeedSourceFailures failures={stream.failures} />
          {stream.preferencesError ? (
            <div role="alert" className="py-8 text-center stack-y-3">
              <p>Akış tercihleri okunamadı.</p>
              <Button onClick={stream.retryPreferences}>Yeniden dene</Button>
            </div>
          ) : stream.loading && !stream.items.length ? (
            <p role="status" className="py-8 text-center text-secondary">
              Akış yükleniyor…
            </p>
          ) : stream.items.length ? (
            <EditorialFeed items={stream.items} />
          ) : (
            <div className="mx-auto max-w-xl py-12 text-center stack-y-4">
              <h2 className="font-serif text-title">
                {stream.sources.length ? "Bu seçkide henüz içerik yok" : "Ne okumak istersin?"}
              </h2>
              <Button variant="primary" onClick={openSourceDiscovery}>
                <Plus size={16} />
                Kaynak seç
              </Button>
              {date && (
                <p className="text-meta text-muted">{date} için seçki bulunamadı. Başka bir gün seçebilirsin.</p>
              )}
            </div>
          )}
          {stream.hasMore && (
            <div className="mt-5 flex justify-center">
              <Button onClick={() => setLimit((value) => Math.min(200, value + 24))}>Daha fazla göster</Button>
            </div>
          )}
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}

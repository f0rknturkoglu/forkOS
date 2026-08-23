import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FeedItem } from "@/core/types";
import { RssReadingPane } from "./RssReadingPane";

const detail: FeedItem = {
  id: "item-1", feed_id: "feed-1", feed_title: "forkOS", title: "Güvenli içerik",
  url: "https://example.com", author: null,
  summary: null, content: '<p onclick="bad()">Merhaba</p><script>alert(1)</script>',
  published_at: "2026-08-23T10:00:00Z", fetched_at: "2026-08-23T10:01:00Z",
  read_at: null, saved_bookmark_id: null,
};

describe("RSS reading pane", () => {
  it("renders article content while removing active HTML", () => {
    const html = renderToStaticMarkup(
      <RssReadingPane
        detail={detail}
        online
        saveCollection="read_later"
        onSaveCollection={() => undefined}
        onToggleRead={() => undefined}
        onSave={() => undefined}
        onOpenBookmark={() => undefined}
        onPrev={() => undefined}
        onNext={() => undefined}
        hasPrev={false}
        hasNext={false}
      />,
    );

    expect(html).toContain("Merhaba");
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("script");
  });
});

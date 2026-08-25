import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Metric } from "@/core/ui";
import type { BookmarkStats } from "@/core/types";

/** Today ust seridi. Modul kendi sayilarini kendi verir. */
export function InboxStats() {
  const { data } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });
  return (
    <>
      <Metric label="Gelen kutusu" value={data?.inbox ?? "–"} href="#/inbox" />
      <Metric
        label="Bugün kaydedilen"
        value={data?.saved_today ?? "–"}
        hint={`toplam ${data?.total ?? 0}`}
        href="#/bookmarks"
      />
    </>
  );
}

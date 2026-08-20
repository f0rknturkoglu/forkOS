import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Stat } from "@/core/ui";
import type { BookmarkStats } from "@/core/types";

/** Today ust seridi. Modul kendi sayilarini kendi verir. */
export function InboxStats() {
  const { data } = useQuery({
    queryKey: ["bookmark-stats"],
    queryFn: () => api.get<BookmarkStats>("/bookmarks/stats"),
  });
  return (
    <>
      <Stat label="Inbox" value={data?.inbox ?? "–"} hint="islenmeyi bekliyor" />
      <Stat label="Bugun kaydedilen" value={data?.saved_today ?? "–"} hint={`toplam ${data?.total ?? 0}`} />
    </>
  );
}

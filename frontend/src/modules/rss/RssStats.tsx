import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api";
import { Stat } from "@/core/ui";
import type { RssStats as RssStatsData } from "@/core/types";

export function RssStats() {
  const { data } = useQuery({
    queryKey: ["rss-stats"],
    queryFn: () => api.get<RssStatsData>("/rss/stats"),
  });
  return (
    <>
      <Stat
        label="Okunmamis RSS"
        value={data?.unread ?? "–"}
        hint={`${data?.active_feeds ?? 0} aktif feed`}
      />
      <Stat
        label="Sorunlu feed"
        value={data?.failing_feeds ?? "–"}
        hint={data?.failing_feeds ? "Activity'de detay var" : "hepsi saglikli"}
      />
    </>
  );
}

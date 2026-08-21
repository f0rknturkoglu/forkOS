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
        label="Okunmamış RSS"
        value={data?.unread ?? "–"}
        hint={`${data?.active_feeds ?? 0} aktif besleme`}
      />
      <Stat
        label="Sorunlu besleme"
        value={data?.failing_feeds ?? "–"}
        hint={data?.failing_feeds ? "Ayrıntısı Etkinlik’te" : "hepsi sağlıklı"}
      />
    </>
  );
}

import { useQuery } from "@tanstack/react-query";
import { api, qs } from "./api";
import { useDebounced } from "@/lib/hooks";
import type { Entity } from "./types";

/** Entity tipine gore nereye gidilecegini bilen tek yer. */
const ROUTE_FOR: Record<string, (id: string) => string> = {
  bookmark: (id) => `#/bookmarks?focus=${id}`,
  feed: (id) => `#/rss?feed=${id}`,
  feed_item: (id) => `#/rss?item=${id}`,
};

export function entityRoute(entity: Entity): string {
  return ROUTE_FOR[entity.type]?.(entity.id) ?? "#/";
}

/** Command Palette icinde kullanilan global arama. Bos sorguda ag'a cikmaz. */
export function useGlobalSearch(query: string) {
  const debounced = useDebounced(query.trim(), 200);
  return useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.get<Entity[]>(`/search${qs({ q: debounced, limit: 8 })}`),
    enabled: debounced.length >= 2,
    staleTime: 10_000,
  });
}

export const TYPE_LABELS: Record<string, string> = {
  bookmark: "Bookmark",
  feed: "Feed",
  feed_item: "RSS",
};

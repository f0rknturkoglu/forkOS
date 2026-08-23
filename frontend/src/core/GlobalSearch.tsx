import { useQuery } from "@tanstack/react-query";
import { api, qs } from "./api";
import { useDebounced } from "@/lib/hooks";
import type { Entity } from "./types";

/** Entity tipine gore nereye gidilecegini bilen tek yer. */
const ROUTE_FOR: Record<string, (id: string) => string> = {
  bookmark: (id) => `#/bookmarks?focus=${id}`,
  feed: (id) => `#/rss?feed=${id}`,
  feed_item: (id) => `#/rss?item=${id}`,
  todo: () => "#/todos",
  opportunity: (id) => `#/opportunities?focus=${id}`,
  study_area: () => "#/study",
  study_topic: (id) => `#/study?focus=${id}`,
  course: () => "#/learning",
  book: () => "#/learning",
  document: () => "#/documents",
  project: (id) => `#/projects?focus=${id}`,
  expense: () => "#/finance",
  recurring_payment: () => "#/finance",
  media_item: (id) => `#/media?focus=${id}`,
  media_unit: () => "#/media",
};

export function entityRoute(entity: Entity): string {
  return ROUTE_FOR[entity.type]?.(entity.id) ?? "#/";
}

/** Command Palette icinde kullanilan global arama. Bos sorguda ag'a cikmaz. */
export function useGlobalSearch(query: string) {
  const debounced = useDebounced(query.trim(), 200);
  return useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.get<Record<string, Entity[]>>(`/search${qs({ q: debounced, limit: 30, grouped: true })}`),
    enabled: debounced.length >= 2,
    staleTime: 10_000,
  });
}

export const TYPE_LABELS: Record<string, string> = {
  bookmark: "Yer imi",
  feed: "Feed",
  feed_item: "RSS",
  todo: "Todo",
  opportunity: "Opportunity",
  study_topic: "Study",
  course: "Course",
  book: "Book",
  document: "Document",
  project: "Project",
  expense: "Expense",
  recurring_payment: "Recurring",
  media_item: "Medya",
  media_unit: "Medya bölümü",
};

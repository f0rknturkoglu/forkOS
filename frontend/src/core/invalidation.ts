/**
 * Merkezi invalidation haritasi (kural 14).
 *
 * Mutation sonrasi tazeleme HAM invalidate("a","b") ile yapilmaz; anlamli bir
 * yazma olayi bildirilir, hangi query key'lerinin tazelenecegine bu harita
 * karar verir. Yeni bir tuketici eklemek = buraya bir key eklemek; 12 dosyayi
 * gezmek degil.
 */
import { queryClient } from "./queryClient";

export const AFTER = {
  "todo.write": ["todos", "today-agenda", "plan", "deadlines", "activity", "review-preview", "tags"],
  "bookmark.write": ["bookmarks", "bookmark-stats", "learning-queue", "tags", "activity"],
  "rss.write": ["items", "rss-item", "feeds", "rss-stats", "today-agenda", "activity"],
  "media.write": ["media", "media-detail", "media-stats", "media-dashboard", "today-agenda", "activity"],
  "opportunity.write": [
    "opportunities",
    "opportunity",
    "deadlines",
    "followups",
    "applications-funnel",
    "opportunity-requirements",
    "application",
    "interviews",
    "today-agenda",
    "activity",
  ],
  "project.write": [
    "projects",
    "project-todos",
    "project-timeline",
    "project-github",
    "todos",
    "today-agenda",
    "activity",
    "tags",
  ],
  "plan.write": ["plan", "today-agenda", "calendar-events", "activity", "todos"],
  "finance.write": ["expenses", "expense-summary", "recurring", "deadlines", "today-agenda", "activity"],
  "study.write": ["study-areas", "study-topics", "study-topic-stats", "activity", "review-preview"],
  "pomodoro.write": [
    "pomodoro-active",
    "pomodoro-stats",
    "pomodoro-sessions",
    "activity",
    "review-preview",
    "project-timeline",
  ],
  "learning.write": ["courses", "books", "learning-queue", "bookmarks", "activity"],
  "document.write": ["documents", "activity"],
  "calendar.write": ["calendar-events", "plan", "today-agenda", "activity"],
  "review.write": ["review-preview", "reviews", "todos", "plan", "activity"],
  "settings.write": ["settings", "github-status", "saved-views"],
  "backup.write": ["backup-status", "activity"],
  "source.sync": [
    "source-runs",
    "source-sync",
    "source-sync-history",
    "opportunities",
    "notifications",
    "media-providers",
    "media",
    "rss-stats",
    "activity",
  ],
  "link.write": ["related", "activity"],
  "notification.write": ["notifications"],
} as const;

type AfterEvent = keyof typeof AFTER;

/** Mutation sonrasi: olaylarin haritadaki tum key'lerini tazeler. */
export function invalidateAfter(...events: AfterEvent[]): void {
  const keys = new Set<string>();
  for (const event of events) {
    for (const key of AFTER[event]) keys.add(key);
  }
  const client = queryClient();
  for (const key of keys) client.invalidateQueries({ queryKey: [key] });
}

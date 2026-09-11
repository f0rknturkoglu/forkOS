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
  "todo.write": [
    "todos",
    "today-agenda",
    "plan",
    "deadlines",
    "activity",
    "review-preview",
    "tags",
    // Konunun "acik gorev" blogu todos'tan turer.
    "study-topic",
    "study-topics",
  ],
  "bookmark.write": [
    "bookmarks",
    "bookmark-stats",
    "tags",
    "activity",
    "related",
    // Ogrenme kuyrugu gorunumu bookmark koleksiyonundan beslenir.
    "study-topics",
    "study-topic",
  ],
  "rss.write": ["items", "rss-item", "feeds", "rss-stats", "today-agenda", "activity"],
  // Medya yazmasi koleksiyon uyeligi, bagli kayitlar, graf ve son tarihleri de
  // etkiler (release tarihleri deadline uretir); yalniz "media" tazelemek
  // Today/graf/son tarih panellerini bayat birakir.
  "media.write": [
    "media",
    "media-detail",
    "media-stats",
    "media-dashboard",
    "media-collections",
    "today-agenda",
    "activity",
    "statistics",
    "deadlines",
    "graph",
    "related",
  ],
  "opportunity.write": [
    "opportunities",
    "opportunity",
    "deadlines",
    "followups",
    "applications-funnel",
    "opportunity-requirements",
    "application",
    "applications",
    "interviews",
    "salary-consistency",
    "notifications",
    "today-agenda",
    "activity",
  ],
  "career.write": [
    "career-stories",
    "career-connections",
    "opportunity-connections",
    "applications",
    "opportunity",
    "activity",
  ],
  "project.write": [
    "projects",
    "project-todos",
    "project-timeline",
    "project-journal",
    "project-github",
    "todos",
    "today-agenda",
    "activity",
    "tags",
  ],
  "plan.write": ["plan", "today-agenda", "calendar-events", "activity", "todos"],
  "finance.write": [
    "expenses",
    "incomes",
    "finance-overview",
    "finance-summary",
    "recurring",
    "deadlines",
    "today-agenda",
    "activity",
  ],
  // Kart tekrari/add: Today, Istatistik, Etkinlik ve Degerlendirme panelleri
  // de bu veriden beslenir -- yalnizca "flashcard" tazelemek onlari bayat birakir.
  "flashcard.write": ["flashcard", "activity", "statistics", "today-agenda", "review-preview"],
  "study.write": [
    "study-areas",
    "study-topics",
    "study-topic",
    "study-topic-stats",
    "study-topic-focus",
    "study-tree",
    "study-review",
    "study-stats",
    "study-stale",
    "topic-resources",
    "topic-progress",
    "courses",
    "today-agenda",
    "activity",
    "statistics",
    "review-preview",
    // Konu/alan degisimi bagli kayitlari, grafigi ve son tarihleri de etkiler.
    "graph",
    "related",
    "backlinks",
    "deadlines",
  ],
  "pomodoro.write": [
    "pomodoro-active",
    "pomodoro-stats",
    "pomodoro-sessions",
    "activity",
    "review-preview",
    "project-timeline",
    "project-journal",
    // Odak seansi konunun "son calisilma" bilgisini ve tekrar kuyrugunu besler.
    "study-topic",
    "study-topic-stats",
    "study-topics",
    "study-stale",
    "study-review",
    "study-stats",
  ],
  "learning.write": [
    "courses",
    "bookmarks",
    "topic-resources",
    "topic-progress",
    "study-topics",
    "study-topic",
    "study-review",
    "study-stats",
    "activity",
    "related",
    "graph",
    "backlinks",
    "today-agenda",
  ],
  "document.write": ["documents", "activity"],
  "calendar.write": ["calendar-events", "plan", "today-agenda", "activity"],
  "review.write": ["review-preview", "reviews", "todos", "plan", "activity"],
  "settings.write": ["settings", "github-status", "google-status", "backup-status", "saved-views"],
  "views.write": ["views"],
  "backup.write": ["backup-status", "activity"],
  "source.sync": [
    "source-runs",
    "source-sync",
    "source-sync-history",
    "opportunities",
    "notifications",
    "media-providers",
    "media",
    "media-dashboard",
    "media-detail",
    "items",
    "feeds",
    "calendar-events",
    "project-github",
    "deadlines",
    "today-agenda",
    "system-stats",
    "sources",
    "rss-stats",
    "activity",
  ],
  "link.write": ["related", "backlinks", "graph", "activity"],
  // jobhunter uyum profili/LinkedIn profilleri config.yaml'a yazilir; ayarlar
  // paneli kaydettikten sonra kendi sorgularini taze gormelidir.
  "jobhunter.write": ["jobhunter-config", "jobhunter-linkedin", "jobhunter-env"],
  "notification.write": ["notifications"],
  "note.write": [
    "notes",
    "note",
    "note-folders",
    "project-journal",
    "activity",
    "tags",
    "backlinks",
    "graph",
    "related",
  ],
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

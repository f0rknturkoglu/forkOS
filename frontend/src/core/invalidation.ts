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
  "goal-studio.consent": ["goal-studio-status"],
  "todo.write": [
    "onboarding-evidence",
    "strategy-overview",
    "career-strategy",
    "career-proposals",
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
    // Proje yuzeyleri gorevden beslenir: proje listesi/karti sayilari ve
    // proje detayindaki gorev listesi. Bu iki anahtar eksikken Todo disindan
    // (or. yakalama kutusu) yazilan proje gorevi proje ekraninda bayat kaliyordu.
    "project-todos",
    "projects",
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
  "opportunity.write": [
    "career-insights",
    "strategy-overview",
    "career-strategy",
    "career-proposals",
    "career-interview-intelligence",
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
    "documents",
    "document-usages",
    "notifications",
    "today-agenda",
    "activity",
  ],
  "career.write": [
    "career-insights",
    "career-interview-intelligence",
    "career-stories",
    "career-connections",
    "opportunity-connections",
    "applications",
    "opportunity",
    "activity",
  ],
  "goal.write": [
    "onboarding-evidence",
    "strategy-overview",
    "strategy-history",
    "career-goals",
    "career-goal",
    "career-strategy",
    "career-proposals",
    "review-preview",
    "reviews",
    "deadlines",
    "activity",
    "related",
  ],
  "career-strategy.write": [
    "study-tree",
    "study-areas",
    "study-review",
    "study-stale",
    "today-agenda",
    "strategy-overview",
    "career-strategy",
    "career-proposals",
    "strategy-history",
    "career-goals",
    "career-goal",
    "study-topics",
    "todos",
    "projects",
    "review-preview",
    "reviews",
    "activity",
    "related",
  ],
  "project-resource.write": ["project-resources", "bookmarks", "bookmark-stats", "related", "projects", "activity"],
  "project.write": [
    "onboarding-evidence",
    "strategy-overview",
    "career-strategy",
    "career-proposals",
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
  // Kart tekrari/add: Today, Istatistik, Etkinlik ve Degerlendirme panelleri
  // de bu veriden beslenir -- yalnizca "flashcard" tazelemek onlari bayat birakir.
  "flashcard.write": ["flashcard", "activity", "statistics", "today-agenda", "review-preview"],
  "study.write": [
    "onboarding-evidence",
    "strategy-overview",
    "career-strategy",
    "career-proposals",
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
    "related",
    "backlinks",
    "deadlines",
  ],
  "pomodoro.write": [
    "statistics",
    "study-tree",
    "study-areas",
    "pomodoro-active",
    "pomodoro-stats",
    "pomodoro-analytics",
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
    "onboarding-evidence",
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
    "backlinks",
    "today-agenda",
  ],
  "document.write": ["documents", "activity"],
  "calendar.write": ["calendar-events", "plan", "today-agenda", "activity"],
  // Degerlendirme kararlari gorev yazar: devredilen gorev plan slotu alir,
  // oncelikler yeni gorev uretir. Home ajandasi kendi ucuyla ("today-agenda")
  // okundugu icin yalniz todos/plan tazelemek onu bayat birakiyordu.
  "review.write": ["strategy-history", "review-preview", "reviews", "todos", "plan", "today-agenda", "activity"],
  // H6 kontrol yuzeyi (Ayarlar > Proaktivite + bildirim panelindeki erteleme)
  // bu yazma olayindan beslenir: ana anahtar, esik ve erteleme durum/kural/
  // gecmis sorgularinin ucunu de tazeler.
  "settings.write": [
    "settings",
    "automation",
    "github-status",
    "google-status",
    "backup-status",
    "saved-views",
    "proactivity-status",
    "proactivity-rules",
    "proactivity-history",
  ],
  "views.write": ["views"],
  "backup.write": ["backup-status", "activity"],
  "source.sync": [
    "source-runs",
    "source-sync",
    "source-sync-history",
    "opportunities",
    "notifications",
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
    // Katalog/kapsam/onbellek: kaynak cekimi bunlarin HEPSINI degistirir.
    // Eksikken yenileme sonrasi saglik ozeti ve kapsam matrisi bayat kaliyordu.
    "source-catalog",
    "source-coverage",
    "source-cache",
  ],
  "link.write": ["strategy-overview", "related", "backlinks", "activity", "project-resources"],
  // Bilgi artık Vault'ta yaşar: Vault yazması forkOS veritabanını
  // DEĞİŞTİRMEZ, bu yüzden yalnız Vault sorguları tazelenir.
  "obsidian.write": ["vault-status", "vault-item"],
  // forkjob_core uyum profili/LinkedIn profilleri config.yaml'a yazilir; ayarlar
  // paneli kaydettikten sonra kendi sorgularini taze gormelidir.
  "forkjob_core.write": ["forkjob-core-config", "forkjob-core-linkedin", "forkjob-core-env"],
  "notification.write": ["notifications"],
  // H7 karar/yurutme yuzeyi: kararlar (approve/reject/respond/cancel) yalnizca
  // plan DURUMUNU degistirir, canonical kayda dokunmaz; bu yuzden tazelenen
  // anahtarlar yalnizca bu modulun kendi listesi ve detayidir. Gercek mutasyon
  // `execute` sirasindadir ve H1 uzerinden olur -- o zaman backend zaten ilgili
  // kaynak sorgularini kendi invalidation'ina baglar (or. "todo.write").
  "execution.write": ["execution-plans", "execution-plan"],
  // A4 semantik terfi ve aday islemleri
  "agent-semantic.write": ["agent-semantic-status", "agent-semantic-candidates", "vault-status"],
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

import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";
import type { components } from "@/generated/api-schema";

type ApiSchemas = components["schemas"];

export type Collection =
  | "inbox" | "read_later" | "learning" | "reference" | "projects" | "archive";

export const COLLECTIONS: Collection[] = [
  "inbox", "read_later", "learning", "reference", "projects", "archive",
];

export const COLLECTION_LABELS: Record<Collection, string> = {
  inbox: "Gelen Kutusu",
  read_later: "Okuma Listesi",
  learning: "Öğrenme",
  reference: "Kaynak",
  projects: "Projeler",
  archive: "Arşiv",
};

export interface Entity {
  id: string;
  type: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityEvent {
  id: number;
  entity_id: string | null;
  entity_type: string | null;
  verb: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

/** Emek haritasinin bir gunu. */
export interface HeatmapDay {
  day: string;
  total: number;
  /** Kategori -> o gunku sayi. Bos gunde bos nesne. */
  kinds: Record<string, number>;
}

/** Gun sayfasindaki hareket; `kind` doluysa emek haritasinda sayilmis demektir. */
export interface DayEvent extends ActivityEvent {
  kind: string | null;
}

export interface DayDetail {
  day: string;
  events: DayEvent[];
  kinds: Record<string, number>;
  labels: Record<string, string>;
  total: number;
  /** Sayilmayan (worker gurultusu) hareket sayisi. */
  other: number;
}

export interface Heatmap {
  days: HeatmapDay[];
  /** Kategori kodu -> Turkce etiket; backend'den gelir. */
  labels: Record<string, string>;
  totals: Record<string, number>;
  total: number;
  active_days: number;
  best_day: HeatmapDay | null;
  streak: number;
}

export interface Bookmark {
  id: string;
  title: string;
  url: string;
  description: string | null;
  collection: Collection;
  source: string;
  read_status: "unread" | "reading" | "read";
  favorite: boolean;
  note: string | null;
  selection: string | null;
  saved_at: string;
  tags: string[];
  queue_kind: "watch" | "read" | "listen" | "practice" | null;
}

export interface BookmarkStats {
  inbox: number;
  unread: number;
  saved_today: number;
  total: number;
  collections: { collection: Collection; count: number }[];
}

export interface Feed {
  id: string;
  title: string;
  url: string;
  site_url: string | null;
  favicon_url: string | null;
  category: string | null;
  active: boolean;
  error_count: number;
  last_status: string | null;
  last_fetched_at: string | null;
  unread: number;
}

export interface FeedItem {
  id: string;
  feed_id: string;
  feed_title: string;
  title: string;
  url: string | null;
  author: string | null;
  summary: string | null;
  /** Okuma bolmesi detayinda dolu (liste hafif kalir). */
  content: string | null;
  published_at: string | null;
  fetched_at: string;
  read_at: string | null;
  saved_bookmark_id: string | null;
}

/** Bugun panelindeki reddit akisi -- /api/news/reddit'ten gelir. */
export interface RedditPost {
  id: string;
  title: string;
  /** Gonderi bir baglantiysa hedef URL, self-post ise comments_url ile ayni. */
  url: string;
  comments_url: string;
  subreddit: string | null;
  author: string;
  published_at: string | null;
}

export interface RssStats {
  feeds: number;
  active_feeds: number;
  failing_feeds: number;
  unread: number;
  today: number;
  saved: number;
}

export interface Todo {
  id: string;
  title: string;
  description: string | null;
  priority: number;
  status: "open" | "doing" | "done" | "dropped";
  due_at: string | null;
  reminder_at: string | null;
  completed_at: string | null;
  parent_id: string | null;
  position: number;
  tags: string[];
  /** daily | weekdays | weekly | monthly; bos ise tek seferlik. */
  recur: string | null;
  /** Gorev bir projeye bagliysa dolu -- listede rozet olarak gorunur. */
  project_id: string | null;
  project_title: string | null;
  milestone_id: string | null;
  milestone_title: string | null;
  subtask_total: number;
  subtask_done: number;
}

export interface PlanSlot {
  id: string;
  entity_id: string;
  entity_type: string;
  title: string;
  day: string;
  start_min: number | null;
  duration_min: number | null;
  note: string | null;
  position: number;
  google_event_id?: string | null;
}

type ApiAgendaRow = ApiSchemas["AgendaRow"];

export type AgendaRow = Omit<ApiAgendaRow, "children"> & {
  children: AgendaRow[];
};

export type TodayAgenda = Omit<
  ApiSchemas["TodayAgendaOut"],
  "timed" | "checklist" | "completed" | "suggestions"
> & {
  timed: AgendaRow[];
  checklist: AgendaRow[];
  completed: AgendaRow[];
  suggestions: { todos: AgendaRow[]; rss: AgendaRow[]; media: AgendaRow[] };
};

export interface StudyArea {
  id: string; title: string; color: string | null; active: boolean; position: number;
}

export interface StudyTopic {
  id: string; title: string; area_id: string; parent_id: string | null;
  status: string; confidence: number | null; target_min: number | null;
  position: number; last_studied_at: string | null; children: StudyTopic[];
}

export interface Course {
  id: string; title: string; platform: string | null; url: string | null;
  status: string; progress_pct: number; started_at: string | null;
  completed_at: string | null; notes: string | null;
}

export interface Book {
  id: string; title: string; author: string | null; status: string;
  total_pages: number | null; current_page: number; started_at: string | null;
  finished_at: string | null; rating: number | null; notes: string | null;
}

export interface Document {
  id: string; title: string; drive_file_id: string; mime: string | null;
  category: string | null; web_view_link: string | null; size_bytes: number | null;
  drive_modified_at: string | null; synced_at: string;
}

export interface CalendarEvent {
  id: string; source: "google" | "plan"; title: string; starts_at: string;
  ends_at: string | null; all_day: boolean; location?: string | null;
  url?: string | null; note?: string | null; read_only: boolean;
  google_event_id?: string | null;
}

export interface Milestone {
  id: string; project_id: string; title: string; due_at: string | null;
  completed_at: string | null; position: number;
}

export interface Project {
  id: string; title: string; status: string; github_repo: string | null;
  url: string | null; stack: string[]; next_action: string | null;
  last_activity_at: string | null; notes: string | null; position: number;
  milestones: Milestone[];
}

/** Proje detayindaki GitHub paneli -- /api/projects/{id}/github. */
export interface GithubIssue {
  number: number;
  title: string;
  url: string;
  state: string;
  labels: string[];
  assignee: string | null;
  comments: number;
  created_at: string | null;
  updated_at: string | null;
  author: string | null;
  draft: boolean;
}

export interface GithubCommit {
  sha: string;
  message: string;
  url: string;
  author: string | null;
  committed_at: string | null;
}

export interface GithubRepoPanel {
  repo: string;
  url: string;
  description: string | null;
  stars: number;
  forks: number;
  watchers: number;
  language: string | null;
  open_issues: number;
  default_branch: string | null;
  pushed_at: string | null;
  private: boolean;
  issues: GithubIssue[];
  pulls: GithubIssue[];
  commits: GithubCommit[];
  /** Token ile mi okundu -- limitin 60/saat mi 5000/saat mi oldugunu soyler. */
  authenticated: boolean;
}

/** Proje gunlugu -- /api/projects/{id}/timeline. */
export interface ProjectEvent {
  id: number;
  verb: string;
  entity_id: string | null;
  entity_type: string | null;
  title: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface GithubActivity { day: string; repo: string; commit_count: number }

export interface Expense {
  id: string; title: string; amount: string; currency: string; category: string;
  spent_on: string; note: string | null;
  sub: string | null;
}

export interface RecurringPayment {
  id: string; title: string; amount: string; currency: string; category: string;
  billing_day: number | null; frequency: string; next_due_at: string | null;
  active: boolean; note: string | null;
  sub: string | null;
}

export type MediaLink = { name: string; url: string; icon?: string };
export type AppSettings = Record<string, unknown> & {
  "modules.disabled": string[];
  "today.widget_order": string[];
  "media.links": MediaLink[];
  theme: string;
};

export interface PomodoroSession {
  id: string;
  started_at: string;
  ended_at: string | null;
  planned_min: number;
  actual_min: number | null;
  kind: "focus" | "short_break" | "long_break";
  context_entity_id: string | null;
  context_title: string | null;
  topic: string | null;
  interrupted: boolean;
  /** Dolu ise seans duraklatilmis -- kalan sure bu ana gore hesaplanir. */
  paused_at: string | null;
  /** Duraklamada gecen toplam saniye. */
  paused_s: number;
}

export interface PomodoroStats {
  minutes: number;
  sessions: number;
  interrupted: number;
}

export interface Habit {
  id: string;
  title: string;
  cadence: "daily" | "weekly";
  target_per_week: number;
  color: string | null;
  active: boolean;
  position: number;
  done_today: boolean;
  streak: number;
  /** Bu hafta (pazartesiden bugune) isaretli gun sayisi. */
  week_done: number;
  /** En uzun kesintisiz seri. */
  best_streak: number;
}

export interface HabitGridEntry {
  habit_id: string;
  title: string;
  day: string;
  done: boolean;
  note: string | null;
}

export type ReviewPreview = ApiSchemas["ReviewPreview"];

export interface SavedView {
  id: string;
  name: string;
  module: string;
  filter: Record<string, unknown>;
  sort: string | null;
  pinned: boolean;
  position: number;
}

export interface TagCount {
  name: string;
  count: number;
}

export type SourceHealth = ApiSchemas["SourceRunOut"] & {
  error: string | null;
  finished_at: string | null;
};

export interface BackupStatus {
  drive_folder_id: string | null;
  last_backup: {
    file: string;
    size: number;
    at: string;
    counts: { entities: number; events: number; modules: Record<string, number> };
  } | null;
  last_drive_upload: { file: string; at: string } | null;
  last_drive_error: { message: string; at: string } | null;
  next_backup_scheduled: string;
  retention_days: number;
  backup_dir: string;
  includes: string[];
}

export type SourceSyncBatch = ApiSchemas["SourceSyncBatchOut"];
export type SourceSyncItem = ApiSchemas["SourceSyncItemOut"];
export type SourceSyncStatus = ApiSchemas["SourceSyncStatusOut"];
export type SourceRefreshResult = ApiSchemas["SourceRefreshOut"];

export interface Opportunity {
  id: string; title: string; kind: string; organization: string | null;
  url: string | null; status: string; priority: number; found_at: string;
  deadline_at: string | null; applied_at: string | null; location: string | null;
  remote: string | null; compensation: string | null; source: string;
  external_id: string | null; raw: Record<string, unknown>;
  /** forkjob uyum puanı (0-100); -1 elenmiş demek. Liste ucunda da dolu. */
  score: number | null;
  /** Puanın bileşenleri — yalnızca detay ucunda dolu. */
  score_reasons: Record<string, unknown> | null;
  notes: string | null;
  trashed_at: string | null;
  trashed_from_status: string | null;
  /** TR | EU | OTHER | UNKNOWN — forkjob region (listsede filtreler bunu kullanir). */
  country: string | null;
  region: string | null;
  follow_up_at: string | null;
  rejection_reason: string | null;
}

export interface Application {
  opportunity_id: string;
  cv_document_id: string | null;
  cv_title: string | null;
  cv_modified_at: string | null;
  cover_letter: string | null;
  company_research: string | null;
  salary_expectation: string | null;
  posting_snapshot: Record<string, unknown>;
  note: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ApplicationHistoryRow {
  id: string;
  from_status: string | null;
  to_status: string;
  at: string;
  note: string | null;
}

export interface Interview {
  id: string;
  opportunity_id: string;
  stage: string;
  mode: string | null;
  scheduled_at: string | null;
  duration_min: number | null;
  notes: string | null;
  outcome: string | null;
  position: number;
}

export interface ApplicationFunnel {
  total: number;
  by_status: { status: string; count: number }[];
  conversions: Record<string, number | null>;
  rejection_reasons: { reason: string; count: number }[];
}

export interface Followup {
  id: string;
  title: string;
  status: string;
  follow_up_at: string;
  note: string | null;
}

export type MediaItem = ApiSchemas["MediaItemOut"];
export type MediaPage = ApiSchemas["MediaPageOut"];
export type MediaDetail = ApiSchemas["MediaDetailOut"];
export type MediaStats = ApiSchemas["MediaStats"];
export type MetadataResult = ApiSchemas["MetadataResult"];
export type GlobalMetadataSearch = ApiSchemas["GlobalMetadataSearchOut"];
export type MediaProviderStatus = ApiSchemas["MediaProviderStatusOut"];

export interface Deadline {
  entity_id: string; type: string; title: string; due_at: string;
  module: string; sub_kind: string | null; priority: number;
}

export interface Notification {
  id: number; kind: string; title: string; body: string | null;
  entity_id: string | null; entity_type: string | null;
  importance: number; created_at: string; read_at: string | null;
}

export interface Command {
  id: string;
  label: string;
  shortcut?: string;
  /**
   * ask verilmisse palet once o alani doldurtur ve degeri buraya gecirir.
   * Verilmemisse run() argumansiz cagrilir.
   */
  run: (input?: string) => void | Promise<void>;
  /** Komutun ihtiyac duydugu tek serbest metin alani. */
  ask?: { label: string; placeholder?: string };
}

/** Sol menudeki gruplar. "pinned" gruplarin ustunde tek basina durur. */
export type ModuleGroup = "pinned" | "capture" | "do" | "track" | "system";

/**
 * Ust seritteki gruplar. Adlar emir kipi degil ISIM: "Yakala/Yap" gibi GTD
 * fiilleri neyin nerede oldugunu soylemiyordu.
 *   Kaynaklar — disaridan gelen malzeme (gelen kutusu, yer imleri, RSS, belge)
 *   Planlama  — zamana bagli is (takvim, gorevler, pomodoro, projeler)
 *   Takip     — duzenli bakilan alanlar (alistirma, finans, firsat, ogrenme)
 *   Sistem    — uygulamanin kendisi (etkinlik, saglik, ayarlar)
 */
export const MODULE_GROUPS: { id: ModuleGroup; label: string }[] = [
  { id: "capture", label: "Kaynaklar" },
  { id: "do", label: "Planlama" },
  { id: "track", label: "Takip" },
  { id: "system", label: "Sistem" },
];

/**
 * Today uc bolgeye ayrilir:
 *   now     — "Su an": suren is, siradaki blok, bugunun gorevleri
 *   pending — "Bekleyenler": islenmeyi bekleyen yiginlar, kompakt
 *   rhythm  — "Ritim": alistirmalar, degerlendirme, gecmis
 */
export type TodayZone = "now" | "pending" | "rhythm";

export interface TodayWidget {
  component: ComponentType;
  zone: TodayZone;
  /**
   * Panel sutunu: "left" (plan), "center" (akis), "right" (durum).
   * Verilmezse center.
   */
  slot?: "left" | "center" | "right";
  /**
   * Sutun icindeki sira; kucuk once. Verilmezse 50.
   * Bunsuz sira modules/index.ts'teki import sirasina kalirdi -- yani
   * sidebar sirasini degistirmek panelin duzenini de bozardi.
   */
  order?: number;
}

export interface ModuleSpec {
  id: string;
  title: string;
  /** Lucide ikonu ya da ayni props'lari alan kendi bilesenin. */
  icon?: LucideIcon | ComponentType<{ size?: number | string; className?: string }>;
  /** Grup verilmezse modul "Sistem" altina duser. */
  group?: ModuleGroup;
  /** title verilmezse ust seritte modulun adi gorunur. */
  routes: { path: string; element: ComponentType; title?: string }[];
  /** Today ust seridindeki sayi kutucuklari. */
  todayStats?: ComponentType[];
  /**
   * Today'e girecek widget'lar. Duz bir bilesen verilirse "ritim" bolgesine
   * duser; bolge secmek icin { component, zone } yaz.
   */
  todayWidgets?: (ComponentType | TodayWidget)[];
  commands?: Command[];
  enabledByDefault?: boolean;
  searchLabel?: string;
}

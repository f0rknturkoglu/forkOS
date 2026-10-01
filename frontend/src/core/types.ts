import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";
import type { components } from "@/generated/api-schema";

type ApiSchemas = components["schemas"];

export type Collection = "inbox" | "read_later" | "learning" | "reference" | "projects" | "archive";

export const COLLECTIONS: Collection[] = ["inbox", "read_later", "learning", "reference", "projects", "archive"];

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
  /**
   * Uyarı mı? SUNUCUDAN gelir (backend `core/events.is_alert` + payload
   * kuralı). İstemci "hangi fiil uyarıdır" listesi TUTMAZ.
   */
  is_alert?: boolean;
}

/** Emek haritasinin bir gunu. */
export interface HeatmapDay {
  day: string;
  total: number;
  /** Kategori -> o gunku sayi. Bos gunde bos nesne. */
  kinds: Record<string, number>;
}

export interface DayDetail {
  day: string;
  events: (ActivityEvent & { kind: string | null })[];
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

/** Bir sayacin uc dilimi: bugun (app gunu), son 7 gun, tum zamanlar. */
interface CounterBreakdown {
  today: number;
  week: number;
  total: number;
}

/** `/statistics/summary`: sayac adi -> dilimler + basvuru + seri. */
export interface StatisticsSummary {
  counters: Record<string, CounterBreakdown>;
  applications: CounterBreakdown;
  streak: { current: number; longest: number };
}

/** `/statistics/monthly` satiri. */
export interface MonthlyPoint {
  /** "YYYY-MM" */
  month: string;
  pomodoros: number;
  todos: number;
  bookmarks: number;
  notes: number;
  rss_read: number;
  reviews: number;
  applications: number;
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
  is_favorite?: boolean;
  note: string | null;
  selection: string | null;
  saved_at: string;
  tags: string[];
  queue_kind?: "watch" | "read" | "listen" | "practice" | null;
  is_duplicate?: boolean;
  existing_collection?: string | null;
  hero_image_url?: string | null;
  favicon_url?: string | null;
  author?: string | null;
  published_at?: string | null;
  reading_time_min?: number;
  word_count?: number;
  scroll_progress?: number;
  highlights_count?: number;
}

export interface BookmarkHighlight {
  id: string;
  bookmark_id: string;
  text: string;
  note?: string | null;
  color: "yellow" | "green" | "blue" | "pink" | string;
  anchor_index: number;
  created_at: string;
}

export interface BookmarkFullText {
  id: string;
  title: string;
  url: string;
  content_html?: string | null;
  content_text?: string | null;
  hero_image_url?: string | null;
  favicon_url?: string | null;
  author?: string | null;
  published_at?: string | null;
  reading_time_min: number;
  word_count: number;
  scroll_progress: number;
  highlights: BookmarkHighlight[];
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
  category?: string | null;
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
  published_at?: string | null;
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
  /** Learning'den dogduysa asil konu agacina geri donus hedefi. */
  learning_topic_id?: string | null;
  learning_topic_title?: string | null;
  milestone_id: string | null;
  milestone_title: string | null;
  subtask_total: number;
  subtask_done: number;
  /** Plan bilgisi (plan_slot) -- due_at'ten ayri: "bugun yapmayi planliyorum".
   *  En yakin gelecek slot doner; gecmis slotlar backend'de listelenmez. */
  planned_day: string | null;
  planned_start_min: number | null;
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

export type TodayAgenda = Omit<ApiSchemas["TodayAgendaOut"], "timed" | "checklist" | "completed" | "suggestions"> & {
  timed: AgendaRow[];
  checklist: AgendaRow[];
  completed: AgendaRow[];
  suggestions: {
    todos: AgendaRow[];
    rss: AgendaRow[];
    media: AgendaRow[];
    flashcards: AgendaRow[];
    study: AgendaRow[];
    /** Kariyer aksiyonları: gönderilecek başvuru, kısa liste, kritik duyuru. */
    career: AgendaRow[];
  };
};

export interface StudyArea {
  id: string;
  title: string;
  color: string | null;
  active: boolean;
  position: number;
}

/** Ogrenme ust seviye gorunumu — URL `?view=` ile senkron. */
export type LearningView = "topics" | "courses" | "review" | "stats";

/** Konu detay sekmeleri — URL `?tab=` ile senkron. */
export type TabId = "genel" | "kaynaklar" | "notlar" | "baglantilar" | "tekrar";

/** Konu durumu; backend `TOPIC_STATUSES` ile ayni kume. */
export type TopicStatus = "not_started" | "in_progress" | "done";

/** `GET /study/areas?include_stats=true` — alan + turetilmis sayaclar. */
export interface StudyAreaStats extends StudyArea {
  archived_at: string | null;
  topic_count: number;
  done_count: number;
  resource_count: number;
  resource_done: number;
  focus_minutes: number;
  stale_count: number;
  last_studied_at: string | null;
}

/** `GET /study/areas/{id}/tree` dugumu: duz liste + `depth` + ata `path`. */
export interface StudyTreeNode {
  id: string;
  title: string;
  parent_id: string | null;
  depth: number;
  position: number;
  status: TopicStatus;
  confidence: number | null;
  mastery: number | null;
  target_min: number | null;
  last_studied_at: string | null;
  next_review_at: string | null;
  review_due: boolean;
  resource_total: number;
  resource_done: number;
  progress_pct: number;
  focus_minutes: number;
  focus_sessions: number;
  child_count: number;
  path: string[];
}

export interface StudyTree {
  area: StudyAreaStats;
  nodes: StudyTreeNode[];
  totals: StudyTreeTotals;
  orphan_count: number;
}

interface StudyTreeTotals {
  topics: number;
  done: number;
  in_progress: number;
  review_due: number;
  resource_total: number;
  resource_done: number;
  focus_minutes: number;
  focus_sessions: number;
}

interface TopicProgress {
  total: number;
  done: number;
  pct: number;
}

interface StudyTopicOpenTodo {
  id: string;
  title: string;
  status: string;
  plan_day: string | null;
  priority: number;
  due_at: string | null;
}

interface StudyReviewBlock {
  interval_days: number;
  ease: number;
  review_count: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  mastery: number | null;
  due: boolean;
}

/** Konu ozeti (detay yaniti `topic` blogu; `children` tasimaz). */
export interface StudyTopicSummary {
  id: string;
  title: string;
  area_id: string;
  parent_id: string | null;
  status: TopicStatus;
  confidence: number | null;
  target_min: number | null;
  position: number;
  mastery: number | null;
  last_studied_at: string | null;
  interval_days: number;
  ease: number;
  review_count: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
}

/** `GET /study/topics/{id}` — konu + atalar + kaynaklar + tekrar blogu. */
export interface StudyTopicDetail {
  topic: StudyTopicSummary;
  ancestors: { id: string; title: string }[];
  resources: LearningResource[];
  progress: TopicProgress;
  stats: { minutes: number; sessions: number; week_minutes: number; last_studied_at: string | null };
  open_todo: StudyTopicOpenTodo | null;
  note_count: number;
  flashcard_deck_count: number;
  review: StudyReviewBlock;
}

export interface LearningResource {
  id: string;
  title: string;
  topic_id: string;
  url: string | null;
  kind: string;
  position: number;
  completed_at: string | null;
  note: string | null;
  /** Sure tahmini (dk) ve son acilma damgasi — derin baglanti/planlama icin. */
  estimated_min: number | null;
  last_opened_at: string | null;
  /** Kaynagin dogusu: manual | bookmark | import. */
  source: string;
  bookmark_id: string | null;
  course_id: string | null;
}

export interface Document {
  id: string;
  title: string;
  drive_file_id: string;
  mime: string | null;
  category: string | null;
  web_view_link: string | null;
  size_bytes: number | null;
  drive_modified_at: string | null;
  synced_at: string;
}

export interface CalendarEvent {
  id: string;
  source: "google" | "plan";
  title: string;
  /** Plan slotları için: bağlı kaydın entity id'si ve tipi (rota registry'den). */
  entity_id?: string | null;
  entity_type?: string | null;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  location?: string | null;
  url?: string | null;
  note?: string | null;
  read_only: boolean;
  google_event_id?: string | null;
}

export interface Milestone {
  id: string;
  project_id: string;
  title: string;
  due_at: string | null;
  completed_at: string | null;
  position: number;
}

export interface Project {
  id: string;
  title: string;
  status: string;
  github_repo: string | null;
  url: string | null;
  stack: string[];
  next_action: string | null;
  last_activity_at: string | null;
  position: number;
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
  todo_id?: string | null;
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
  fetched_at: string;
  private: boolean;
  issues: GithubIssue[];
  pulls: GithubIssue[];
  commits: {
    sha: string;
    message: string;
    url: string;
    author: string | null;
    committed_at: string | null;
  }[];
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

export interface ProjectJournalDay {
  day: string;
  events: ProjectEvent[];
}

export interface RecurringPayment {
  id: string;
  title: string;
  amount: string | number;
  currency: string;
  category: string;
  billing_day: number | null;
  frequency: string;
  next_due_at: string | null;
  active: boolean;
  note: string | null;
  sub: string | null;
}

export type AppSettings = Record<string, unknown> & {
  "modules.disabled": string[];
  "today.widget_order": string[];
  "media.links": { name: string; url: string; icon?: string }[];
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
  /** Baglamin entity tipi -- "nereden geldi" rozeti bundan cizilir. */
  context_type: string | null;
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

export interface PomodoroDailyPoint {
  date: string;
  minutes: number;
  sessions: number;
  interrupted: number;
}

interface PomodoroContextStat {
  context_entity_id: string | null;
  title: string;
  context_type: string | null;
  minutes: number;
  sessions: number;
  share: number;
}

export interface PomodoroAnalytics {
  range: "week" | "month" | "all";
  start_date: string;
  end_date: string;
  minutes: number;
  sessions: number;
  completed: number;
  interrupted: number;
  daily: PomodoroDailyPoint[];
  contexts: PomodoroContextStat[];
}

export type ReviewPreview = ApiSchemas["ReviewPreview"];

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
  /* Anlamli veri degismediyse zamanlanmis yedek atlanir; arayuz bunu aciklar. */
  changes_since_backup: boolean;
  retention_days: number;
  backup_dir: string;
  includes: string[];
}

/**
 * `/system/stats` yaniti: makinenin (ya da Linux VM'in) anlik sagligi.
 * `cpu_pct` ilk cagrida null olur -- /proc/stat farki icin onceki olcum yok;
 * arayuz "olculuyor" der, sifir uydurmaz.
 */
export interface SystemStats {
  cpu_pct: number | null;
  load: number[];
  cpu_count: number;
  mem_total_kb: number | null;
  mem_available_kb: number | null;
  disk: { total: number; free: number; path?: string } | null;
  uptime_s: number;
  worker: { status: "healthy" | "stale" | "unknown" | "disabled"; heartbeat_at: string | null };
}

export type SourceSyncBatch = ApiSchemas["SourceSyncBatchOut"];
export type SourceSyncStatus = ApiSchemas["SourceSyncStatusOut"];
export type SourceRefreshResult = ApiSchemas["SourceRefreshResult"];
export type ManualRefreshStatus = ApiSchemas["ManualRefreshOut"];

/** `/sources/cache` — sınırlı disk önbelleğinin anlık durumu. */
export interface SourceCacheStats {
  dir: string;
  mode: string;
  files: number;
  bytes: number;
  oldest: string | null;
  hosts: Record<string, number>;
  max_bytes: number;
  max_age_seconds: number;
}

export interface SourceCachePruneResult {
  removed: number;
  bytes_freed: number;
  bytes_remaining?: number;
  max_bytes?: number;
  max_age_seconds?: number;
}

/** `/sources/coverage` — kaynak kapsam matrisi satırı. */
export interface SourceCoverageRow {
  source: string;
  kind: string;
  class: string;
  category: string | null;
  official: boolean | null;
  url: string | null;
  parser_version: string | null;
  last_status: string | null;
  last_run_at: string | null;
  last_success_at: string | null;
  last_new_content_at: string | null;
  avg_publish_interval_days: number | null;
  consecutive_empty: number;
  last_error: string | null;
  last_error_kind: string | null;
  circuit_open: boolean;
  consecutive_failures: number;
  tracked: boolean;
}

export interface Opportunity {
  id: string;
  title: string;
  kind: string;
  category: string | null;
  organization: string | null;
  url: string | null;
  /** Keşif/duyuru yaşam döngüsü. CRM hattı `application_status`'tadır. */
  status: string;
  /** Mevcut durumdan İZİNLİ keşif geçişleri (backend state machine). */
  allowed_transitions: string[];
  priority: number;
  found_at: string;
  published_at: string | null;
  deadline_at: string | null;
  applied_at: string | null;
  location: string | null;
  remote: string | null;
  compensation: string | null;
  source: string;
  external_id: string | null;
  raw: Record<string, unknown>;
  /** Kural tabanlı genel uygunluk puanı (-1..100); -1 elenmiş demek. */
  score: number | null;
  /** Puanın kaynağı ve hesaplanma anı (açıklanabilirlik). */
  score_source?: string | null;
  score_computed_at?: string | null;
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
  /** Belge ters-bağı (DocumentsPage): başvuru kaydındaki CV. Liste ucunda dolu. */
  cv_document_id?: string | null;
  /** Belge ters-bağı (DocumentsPage): gereksinime bağlanan ilk belge. */
  requirement_document_id?: string | null;
  /**
   * Profil/beceri örtüşmesi (0..1). CV DOSYASI kullanmaz; gerçek CV
   * değerlendirmesi `evaluation` alanındadır. null = hesaplanmadı.
   */
  profile_match_ratio?: number | null;
  /** Profil ve CV beceri eşleşmesi */
  skill_match?: {
    match_ratio: number;
    matched: string[];
    missing: string[];
  } | null;
  /** Başvuru hattı — yalnızca gerçek başvuru kayıtlarında dolu. */
  application_status?: string | null;
  application_status_changed_at?: string | null;
  allowed_application_transitions?: string[];
  intelligence?: OpportunityIntelligence | null;
  /** career-ops iki aşamalı gereksinim ve aday değerlendirmesi. */
  evaluation?: OpportunityEvaluation | null;
  /**
   * Değerlendirme bayatsa nedeni ("version" | "listing" | "profile" | "missing"),
   * güncelse null. Bayat değerlendirme güncel gibi sunulmaz.
   */
  evaluation_stale_reason?: string | null;
  /* ── Kaynak gözlemi / kapanma ─────────────────────────────────────── */
  source_status?: string;
  last_seen_at?: string | null;
  closed_at?: string | null;
  /* ── Duyuru alanları (iş ilanlarında boş kalır) ───────────────────── */
  official?: boolean | null;
  parent_id?: string | null;
  stage?: string | null;
  application_start_at?: string | null;
  application_end_at?: string | null;
  exam_at?: string | null;
  result_at?: string | null;
  guide_url?: string | null;
  apply_url?: string | null;
  quota_total?: number | null;
  fields?: string[];
}

/** `GET /opportunities/lifecycle` — üç durum makinesinin tek kaynağı. */
export interface OpportunityLifecycle {
  job_discovery: { flow: string[]; transitions: Record<string, string[]> };
  announcement: { flow: string[]; transitions: Record<string, string[]> };
  application: { flow: string[]; transitions: Record<string, string[]>; terminal: string[] };
  trash_status: string;
  job_kinds: string[];
}

export interface ApplicationTimelineEntry {
  kind:
    | "discovered"
    | "shortlisted"
    | "status"
    | "followup"
    | "interview"
    | "note"
    | "document"
    | "todo"
    | "offer"
    | "rejection";
  at: string;
  title: string;
  detail: string | null;
  status: string | null;
}

export interface ApplicationTimeline {
  opportunity_id: string;
  entries: ApplicationTimelineEntry[];
}

interface OpportunityRiskSignal {
  code: string;
  label: string;
  detail: string;
  severity: "neutral" | "warn" | "danger";
}

export interface ListingHealth {
  health_score: number;
  jd_completeness: "complete" | "concise" | "stub";
  salary_transparency: "transparent" | "unclear" | "missing";
  liveness_status: "live" | "unchecked" | "at_risk" | "expired";
  repost_frequency: "none" | "moderate" | "frequent";
}

interface OpportunityIntelligence {
  repost_count: number;
  is_repost: boolean;
  connection_count?: number;
  pay_min: number | null;
  pay_max: number | null;
  pay_currency: string | null;
  pay_range_ratio: number | null;
  pay_transparency_risk: boolean;
  geo_mismatch: boolean;
  sponsorship_status: "sponsors" | "not_needed" | "unstated" | "no_sponsorship";
  signals: OpportunityRiskSignal[];
  listing_health?: ListingHealth | null;
}

export type RequirementImportance = "critical" | "high" | "meaningful" | "preferred" | "low_signal";
export type RequirementEvidence = "stated" | "structural" | "inferred";
export type CandidateMatch = "strong" | "partial" | "missing";
export type OpportunityArchetype = "fde" | "sa" | "pm" | "llmops" | "agentic" | "transformation";

export interface EvaluationRequirement {
  id: string;
  name: string;
  importance: RequirementImportance;
  evidence: RequirementEvidence;
  excerpt: string | null;
  terms: string[];
}

export interface EvaluationMatch {
  requirement_id: string;
  requirement: string;
  match: CandidateMatch;
  evidence: string;
  gap_mitigation: string | null;
  story_ids: string[];
}

interface EvaluationGate {
  job_country: string | null;
  authorized_to_work: boolean | null;
  sponsorship_status: "sponsors" | "not_needed" | "unstated" | "no_sponsorship";
  geo_mismatch: boolean;
  hard_blocker: boolean;
  reasons: string[];
}

export interface OpportunityEvaluation {
  version: string;
  evaluated_at: string;
  source_fingerprint: string;
  engine: "local_rules";
  candidate_source: "document" | "profile";
  candidate_document_id: string | null;
  candidate_document_title: string | null;
  archetype: OpportunityArchetype | null;
  archetype_scores: Record<string, number>;
  score: number;
  recommendation: "pursue" | "consider" | "skip";
  requirements: EvaluationRequirement[];
  matches: EvaluationMatch[];
  gate: EvaluationGate;
  notes: string | null;
}

export interface ReplyAnalysis {
  kind: "interview_invite" | "rejection" | "take_home_assessment" | "auto_acknowledgement" | "unknown";
  label: string;
  confidence: number;
  evidence: string[];
  suggested_status: "applied" | "interview" | "rejected" | null;
  suggested_todo_title: string | null;
  summary: string;
}

export interface SilentApplication {
  id: string;
  title: string;
  organization: string | null;
  status: string;
  last_interview_at: string;
  days_silent: number;
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
  /** Başvuru hattı durumu (APPLICATION_STATUSES). */
  status: string;
  status_changed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ApplicationHistoryRow {
  id: string;
  from_status: string | null;
  to_status: string;
  at: string;
  note: string | null;
  /** "discovery" | "application" */
  scope: string;
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
  salary_stated: string | null;
  position: number;
}

export type CareerStoryProvenance = "existing" | "supported" | "derived-unverified" | "user-cannot-confirm";

export interface CareerStory {
  id: string;
  title: string;
  situation: string | null;
  task: string | null;
  action: string | null;
  result: string | null;
  reflection: string | null;
  provenance: CareerStoryProvenance;
  tags: string[];
  updated_at: string;
}

export interface SalaryConsistency {
  inconsistent: boolean;
  claims: {
    interview_id: string;
    stage: string;
    statement: string;
    pay_min: number | null;
    pay_max: number | null;
    currency: string | null;
  }[];
  warning: string | null;
}

export interface CoverLetterReview {
  score: number;
  generic_phrases: string[];
  matched_story_ids: string[];
  flags: string[];
  suggestions: string[];
}

export interface CareerConnection {
  id: string;
  name: string;
  first_name: string | null;
  last_name: string | null;
  profile_url: string | null;
  email: string | null;
  company: string | null;
  position: string | null;
  connected_on: string | null;
}

export interface CareerConnectionsImportResult {
  total_rows: number;
  created: number;
  updated: number;
  skipped: number;
}

export interface OpportunityConnections {
  organization: string | null;
  normalized_organization: string | null;
  connections: CareerConnection[];
}

/** Funnel kırılım satırı. Payda ve paylar UI'da açıkça yazılır. */
export interface FunnelBreakdownRow {
  key: string;
  label: string;
  total: number;
  responded: number;
  interviewed: number;
  offers: number;
  response_rate: number | null;
  interview_rate: number | null;
}

export interface FunnelVolumeRow {
  period: string;
  applied: number;
}

export interface ApplicationListPage {
  items: Opportunity[];
  /** Filtreye uyan GERÇEK toplam; `limit` değil. */
  total: number;
  offset: number;
  limit: number;
}

export interface CoverLetter {
  opportunity_id: string;
  title: string;
  organization: string | null;
  cover_letter: string;
}

export interface InterviewPrepGroup {
  opportunity: Opportunity;
  interviews: Interview[];
  salary: SalaryConsistency;
}

export interface ApplicationFunnel {
  /** Payda: yalnızca gerçek başvuru kayıtları. Keşfedilen ilanlar sayılmaz. */
  total: number;
  tracked: number;
  by_status: { status: string; count: number }[];
  /** Kohort tabanlı dönüşüm oranları (stok sayımı değil). */
  conversions: Record<string, number | null>;
  /** Hangi aşamaya kaç başvuru ULAŞTI. */
  cohort: Record<string, number>;
  /** `applied` aşamasına ulaşan başvuru sayısı = dönüşüm paydası. */
  cohort_size: number;
  /** Bu sayının altında yüzde yerine ham sayı gösterilir. */
  min_cohort_size: number;
  /** Kohort eşiğin altındaysa yüzdeler yanıltıcı olabilir. */
  sufficient: boolean;
  rejection_reasons: { reason: string; count: number }[];
  avg_first_response_days: number | null;
  avg_applied_to_interview_days: number | null;
  by_source: FunnelBreakdownRow[];
  by_cv: FunnelBreakdownRow[];
  by_role: FunnelBreakdownRow[];
  by_country: FunnelBreakdownRow[];
  by_work_mode: FunnelBreakdownRow[];
  weekly_volume: FunnelVolumeRow[];
  monthly_volume: FunnelVolumeRow[];
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
  entity_id: string;
  type: string;
  title: string;
  due_at: string;
  module: string;
  sub_kind: string | null;
  priority: number;
}

export interface Notification {
  id: number;
  kind: string;
  title: string;
  body: string | null;
  entity_id: string | null;
  entity_type: string | null;
  importance: number;
  created_at: string;
  read_at: string | null;
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

/** Home'un anlamsal okuma sırası; viewport değişince DOM sırası değişmez. */
export type TodayPlacement = "now" | "plan" | "attention" | "context";

export interface TodayWidget {
  /**
   * Moduller arasi benzersiz ve KALICI kimlik (Faz 19). Kullanicinin
   * gizleme/siralama tercihlerinin anahtari oldugu icin yeniden
   * adlandirilmaz.
   */
  id: string;
  /** Ayarlar ekraninda gorunen ad. */
  title: string;
  component: ComponentType;
  /**
   * Verilirse widget ÇEKİRDEKTİR: Home iskeletinde her zaman görünür,
   * gizlenemez ve `order` ile sabit sırada durur. Verilmezse widget
   * İSTEĞE BAĞLIDIR: `defaultVisible` + kullanıcı tercihi geçerlidir ve
   * iskeletin altında akar.
   */
  core?: TodayPlacement;
  /** İsteğe bağlı widget'ın yeri; görünürlük tercihini değiştirmez. */
  placement?: TodayPlacement;
  /** Bağlam sütunu; belirtilmeyen yüzeyler ana sütunda akar. */
  contextLane?: "main" | "secondary";
  /** Planın sağında gösterilen özet yüzeyi. */
  besidePlan?: boolean;
  /**
   * Cekirdek iskeletteki sira; kucuk once. ZORUNLU: verilmezse cakisma
   * uretir (eski varsayilan 50 kaldirildi).
   */
  order: number;
  /** İsteğe bağlı yüzeyin varsayılan görünürlüğü; verilmezse görünür. */
  defaultVisible?: boolean;
}

export interface ModuleSpec {
  id: string;
  title: string;
  /** Ayarlar ekranindaki modul listesinde tek satirlik aciklama. */
  description?: string;
  /** Lucide ikonu ya da ayni props'lari alan kendi bilesenin. */
  icon?: LucideIcon | ComponentType<{ size?: number | string; className?: string }>;
  /**
   * Navigasyon burada TANIMLANMAZ: bir modulun sidebar'da satir tutup
   * tutmadigini `core/navigation.ts` icindeki urun alani tablosu belirler.
   * Modul kayitli ama hicbir alanda anilmamis olabilir (ornek: `inbox` bir
   * triyaj akisidir) -- rotasi, widget'lari ve komutlari yine calisir.
   */
  /** title verilmezse çalışma alanı başlığında modülün adı görünür. */
  routes: {
    path: string;
    element: ComponentType;
    title?: string;
    /** Lucide ikonu veya SVG bileseni. Alt rotalarda da gosterilir. */
    icon?: LucideIcon | ComponentType<{ size?: number | string; className?: string }>;
    /** Birincil rota modül satırıdır; yalnız bilinçli ikincil girişler sidebar çocuğu olur. */
    navigation?: "child" | "hidden";
  }[];
  /**
   * Modül aktifken ana sidebar içinde açılan veri-temelli alt ağaç.
   * Not listesi gibi çalışma alanına ait kayıtlar ikinci bir sayfa sidebar'ı
   * oluşturmadan burada gösterilir.
   */
  sidebar?: ComponentType<{ collapsed: boolean; onNavigate: () => void }>;
  /** Today ust seridindeki sayi kutucuklari. */
  todayStats?: ComponentType[];
  /**
   * Today'e girecek widget'lar. Duz bir bilesen verilirse "ritim" bolgesine
   * duser; bolge secmek icin { component, zone } yaz.
   */
  todayWidgets?: TodayWidget[];
  /** Uygulama kabugunda her rotada tek kez render edilen modul yuzeyleri. */
  globalSurfaces?: ComponentType[];
  commands?: Command[];
}

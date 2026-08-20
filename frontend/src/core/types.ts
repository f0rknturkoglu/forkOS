import type { ComponentType } from "react";

export type Collection =
  | "inbox" | "read_later" | "learning" | "reference" | "projects" | "archive";

export const COLLECTIONS: Collection[] = [
  "inbox", "read_later", "learning", "reference", "projects", "archive",
];

export const COLLECTION_LABELS: Record<Collection, string> = {
  inbox: "Inbox",
  read_later: "Read Later",
  learning: "Learning",
  reference: "Reference",
  projects: "Projects",
  archive: "Archive",
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
  published_at: string | null;
  fetched_at: string;
  read_at: string | null;
  saved_bookmark_id: string | null;
}

export interface RssStats {
  feeds: number;
  active_feeds: number;
  failing_feeds: number;
  unread: number;
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

export interface GithubActivity { day: string; repo: string; commit_count: number }

export interface Expense {
  id: string; title: string; amount: string; currency: string; category: string;
  spent_on: string; note: string | null;
}

export interface RecurringPayment {
  id: string; title: string; amount: string; currency: string; category: string;
  billing_day: number | null; frequency: string; next_due_at: string | null;
  active: boolean; note: string | null;
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
}

export interface HabitGridEntry {
  habit_id: string;
  title: string;
  day: string;
  done: boolean;
  note: string | null;
}

export interface ReviewPreview {
  kind: "daily" | "weekly";
  period_start: string;
  period_end: string;
  stats: {
    todos: { completed: number; created: number; dropped: number; overdue_now: number };
    focus: { minutes: number; sessions: number; interrupted: number };
    topics: { topic: string; minutes: number }[];
    habits: Record<string, number>;
    capture: { bookmarks: number; rss_read: number };
  };
  unfinished_todos: { id: string; title: string; priority: number; due_at: string | null }[];
}

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

export interface SourceHealth {
  source: string;
  status: string;
  items_found: number;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface Opportunity {
  id: string; title: string; kind: string; organization: string | null;
  url: string | null; status: string; priority: number; found_at: string;
  deadline_at: string | null; applied_at: string | null; location: string | null;
  remote: string | null; compensation: string | null; source: string;
  external_id: string | null; raw: Record<string, unknown>; notes: string | null;
}

export interface Deadline {
  entity_id: string; type: string; title: string; due_at: string;
  module: string; sub_kind: string | null; priority: number;
}

export interface Notification {
  id: number; kind: string; title: string; body: string | null;
  entity_id: string | null; importance: number; created_at: string; read_at: string | null;
}

export interface Command {
  id: string;
  label: string;
  shortcut?: string;
  run: () => void;
}

export interface ModuleSpec {
  id: string;
  title: string;
  icon?: ComponentType<{ size?: number }>;
  routes: { path: string; element: ComponentType }[];
  /** Today ust seridindeki sayi kutucuklari. */
  todayStats?: ComponentType[];
  todayWidgets?: ComponentType[];
  commands?: Command[];
  enabledByDefault?: boolean;
  searchLabel?: string;
}

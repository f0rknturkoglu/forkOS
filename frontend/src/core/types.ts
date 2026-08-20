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
}

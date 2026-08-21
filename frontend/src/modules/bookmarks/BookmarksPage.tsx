import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, qs } from "@/core/api";
import { Badge, Button, Empty, Panel, cx, hostOf, relativeTime } from "@/core/ui";
import { useDebounced, useInvalidate, useOnline } from "@/lib/hooks";
import { useHashRoute } from "@/app/router";
import { COLLECTION_LABELS, COLLECTIONS } from "@/core/types";
import type { Bookmark, Collection, SavedView, TagCount } from "@/core/types";

interface Filter {
  collection?: Collection | "";
  read_status?: string;
  favorite?: boolean;
  tag?: string;
  q?: string;
}

const MODULE = "bookmark";

function BookmarkRow({ bookmark, focused }: { bookmark: Bookmark; focused: boolean }) {
  const online = useOnline();
  const invalidate = useInvalidate();
  const refresh = () => invalidate("bookmarks", "bookmark-stats", "tags", "activity");

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch(`/bookmarks/${bookmark.id}`, body),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/bookmarks/${bookmark.id}`),
    onSuccess: refresh,
  });

  return (
    <li
      id={bookmark.id}
      className={cx(
        "rounded border p-3",
        focused ? "border-accent-border bg-accent-surface" : "border-subtle bg-surface",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            className={cx(
              "block truncate text-body hover:underline",
              bookmark.read_status === "read" ? "text-muted" : "text-primary",
            )}
          >
            {bookmark.title || bookmark.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
            <span>{hostOf(bookmark.url)}</span>
            <span>·</span>
            <span>{relativeTime(bookmark.saved_at)}</span>
            <Badge>{COLLECTION_LABELS[bookmark.collection]}</Badge>
            {bookmark.read_status !== "unread" && <Badge tone="ok">{bookmark.read_status}</Badge>}
            {bookmark.tags.map((tag) => (
              <Badge key={tag}>#{tag}</Badge>
            ))}
          </div>
          {bookmark.note && (
            <p className="mt-2 text-meta text-secondary">{bookmark.note}</p>
          )}
        </div>

        <div className="flex flex-wrap justify-end items-center gap-1">
          <Button
            disabled={!online}
            title="Favori"
            onClick={() => patch.mutate({ favorite: !bookmark.favorite })}
          >
            {bookmark.favorite ? "★" : "☆"}
          </Button>
          <Button
            disabled={!online}
            title="Okundu işaretle"
            onClick={() =>
              patch.mutate({ read_status: bookmark.read_status === "read" ? "unread" : "read" })
            }
          >
            {bookmark.read_status === "read" ? "okunmadi" : "okundu"}
          </Button>
          <select
            disabled={!online}
            value={bookmark.collection}
            onChange={(e) => patch.mutate({ collection: e.target.value })}
            className="rounded border border-strong bg-surface px-1 py-1 text-meta text-secondary"
          >
            {COLLECTIONS.map((c) => (
              <option key={c} value={c}>
                {COLLECTION_LABELS[c]}
              </option>
            ))}
          </select>
          <Button variant="danger" disabled={!online} onClick={() => remove.mutate()}>
            sil
          </Button>
        </div>
      </div>
    </li>
  );
}

export function BookmarksPage() {
  const { params } = useHashRoute();
  const focus = params.get("focus");
  const online = useOnline();
  const invalidate = useInvalidate();

  const [filter, setFilter] = useState<Filter>({ collection: "" });
  const [search, setSearch] = useState("");
  /** "+ kaydet" satir ici ad formu acik mi. */
  const [namingView, setNamingView] = useState(false);
  const q = useDebounced(search, 250);

  useEffect(() => {
    if (focus) document.getElementById(focus)?.scrollIntoView({ block: "center" });
  }, [focus]);

  const query = { ...filter, q, limit: 100 } as Record<string, string | number | boolean>;
  const { data = [], isLoading } = useQuery({
    queryKey: ["bookmarks", "library", query],
    queryFn: () => api.get<Bookmark[]>(`/bookmarks${qs(query)}`),
  });

  const { data: tags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<TagCount[]>("/tags"),
  });

  const { data: views = [] } = useQuery({
    queryKey: ["views", MODULE],
    queryFn: () => api.get<SavedView[]>(`/views${qs({ module: MODULE })}`),
  });

  const saveView = useMutation({
    mutationFn: (name: string) =>
      api.post("/views", { name, module: MODULE, filter: { ...filter, q }, pinned: true }),
    onSuccess: () => invalidate("views"),
  });
  const deleteView = useMutation({
    mutationFn: (id: string) => api.del(`/views/${id}`),
    onSuccess: () => invalidate("views"),
  });

  const applyView = (view: SavedView) => {
    const stored = view.filter as Filter;
    setFilter({
      collection: stored.collection ?? "",
      read_status: stored.read_status,
      favorite: stored.favorite,
      tag: stored.tag,
    });
    setSearch(stored.q ?? "");
  };

  return (
    <div className="grid gap-4 p-6 lg:grid-cols-[1fr_260px]">
      <div>
        <header className="mb-4 flex items-baseline justify-between">
          <span className="text-meta text-muted">{data.length} sonuc</span>
        </header>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ara (başlık, not, seçim)…"
            className="min-w-48 flex-1 rounded border border-subtle bg-surface px-3 py-1.5 text-body outline-none focus:border-accent"
          />
          <select
            value={filter.collection ?? ""}
            onChange={(e) => setFilter({ ...filter, collection: e.target.value as Collection })}
            className="rounded border border-subtle bg-surface px-2 py-1.5 text-body"
          >
            <option value="">Tüm koleksiyonlar</option>
            {COLLECTIONS.map((c) => (
              <option key={c} value={c}>
                {COLLECTION_LABELS[c]}
              </option>
            ))}
          </select>
          <select
            value={filter.read_status ?? ""}
            onChange={(e) =>
              setFilter({ ...filter, read_status: e.target.value || undefined })
            }
            className="rounded border border-subtle bg-surface px-2 py-1.5 text-body"
          >
            <option value="">Okuma durumu</option>
            <option value="unread">Okunmadi</option>
            <option value="reading">Okuyor</option>
            <option value="read">Okundu</option>
          </select>
          <Button
            variant={filter.favorite ? "primary" : "ghost"}
            onClick={() =>
              setFilter({ ...filter, favorite: filter.favorite ? undefined : true })
            }
          >
            ★ favoriler
          </Button>
          {filter.tag && (
            <Button onClick={() => setFilter({ ...filter, tag: undefined })}>
              #{filter.tag} ✕
            </Button>
          )}
        </div>

        {isLoading ? (
          <p className="text-body text-muted">Yükleniyor…</p>
        ) : data.length === 0 ? (
          <Empty>Bu filtreye uyan kayıt yok.</Empty>
        ) : (
          <ul className="space-y-2">
            {data.map((bookmark) => (
              <BookmarkRow key={bookmark.id} bookmark={bookmark} focused={focus === bookmark.id} />
            ))}
          </ul>
        )}
      </div>

      <aside className="space-y-4">
        <Panel
          title="Kayıtlı görünümler"
          action={
            <Button
              disabled={!online}
              onClick={() => setNamingView((v) => !v)}
            >
              + kaydet
            </Button>
          }
        >
          {namingView && (
            <form
              className="mb-3 flex gap-2 border-b border-subtle pb-3"
              onSubmit={(event) => {
                event.preventDefault();
                const name = (new FormData(event.currentTarget).get("name") as string ?? "").trim();
                if (!name) return;
                saveView.mutate(name);
                setNamingView(false);
              }}
            >
              <input name="name" autoFocus placeholder="Görünüm adı"
                aria-label="Görünüm adı"
                onKeyDown={(event) => { if (event.key === "Escape") setNamingView(false); }}
                className="h-8 min-w-0 flex-1 rounded-control border border-subtle bg-surface px-2 text-body text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
              <Button type="submit" variant="primary" size="sm">Kaydet</Button>
            </form>
          )}
          {views.length === 0 ? (
            <Empty>Henüz görünüm yok.</Empty>
          ) : (
            <ul className="space-y-1">
              {views.map((view) => (
                <li key={view.id} className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => applyView(view)}
                    className="truncate text-left text-body text-secondary hover:text-primary"
                  >
                    {view.name}
                  </button>
                  <button
                    onClick={() => deleteView.mutate(view.id)}
                    disabled={!online}
                    className="text-meta text-muted hover:text-danger"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Etiketler">
          {tags.length === 0 ? (
            <Empty>Etiket yok.</Empty>
          ) : (
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 40).map((tag) => (
                <button
                  key={tag.name}
                  onClick={() => setFilter({ ...filter, tag: tag.name })}
                  className="rounded border border-subtle px-1.5 py-0.5 text-meta text-secondary hover:border-strong hover:text-primary"
                >
                  #{tag.name} <span className="text-muted">{tag.count}</span>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </aside>
    </div>
  );
}

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
        focused ? "border-sky-700 bg-sky-950/20" : "border-neutral-800 bg-neutral-900/40",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <a
            href={bookmark.url}
            target="_blank"
            rel="noreferrer"
            className={cx(
              "block truncate text-sm hover:underline",
              bookmark.read_status === "read" ? "text-neutral-500" : "text-neutral-100",
            )}
          >
            {bookmark.title || bookmark.url}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-neutral-500">
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
            <p className="mt-2 text-xs text-neutral-400">{bookmark.note}</p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <Button
            disabled={!online}
            title="Favori"
            onClick={() => patch.mutate({ favorite: !bookmark.favorite })}
          >
            {bookmark.favorite ? "★" : "☆"}
          </Button>
          <Button
            disabled={!online}
            title="Okundu isaretle"
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
            className="rounded border border-neutral-700 bg-neutral-900 px-1 py-1 text-xs text-neutral-300"
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
          <h1 className="text-xl font-semibold">Bookmark Library</h1>
          <span className="text-xs text-neutral-500">{data.length} sonuc</span>
        </header>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ara (baslik, not, secim)..."
            className="min-w-48 flex-1 rounded border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-sm outline-none focus:border-neutral-600"
          />
          <select
            value={filter.collection ?? ""}
            onChange={(e) => setFilter({ ...filter, collection: e.target.value as Collection })}
            className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-sm"
          >
            <option value="">Tum koleksiyonlar</option>
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
            className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1.5 text-sm"
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
          <p className="text-sm text-neutral-500">Yukleniyor...</p>
        ) : data.length === 0 ? (
          <Empty>Bu filtreye uyan kayit yok.</Empty>
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
          title="Kayitli gorunumler"
          action={
            <Button
              disabled={!online}
              onClick={() => {
                const name = prompt("Gorunum adi", "Unread AI articles");
                if (name) saveView.mutate(name);
              }}
            >
              + kaydet
            </Button>
          }
        >
          {views.length === 0 ? (
            <Empty>Henuz gorunum yok.</Empty>
          ) : (
            <ul className="space-y-1">
              {views.map((view) => (
                <li key={view.id} className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => applyView(view)}
                    className="truncate text-left text-sm text-neutral-300 hover:text-neutral-100"
                  >
                    {view.name}
                  </button>
                  <button
                    onClick={() => deleteView.mutate(view.id)}
                    disabled={!online}
                    className="text-xs text-neutral-600 hover:text-red-400"
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
                  className="rounded border border-neutral-800 px-1.5 py-0.5 text-[11px] text-neutral-400 hover:border-neutral-600 hover:text-neutral-200"
                >
                  #{tag.name} <span className="text-neutral-600">{tag.count}</span>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </aside>
    </div>
  );
}

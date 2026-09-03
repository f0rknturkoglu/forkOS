import { invalidateAfter } from "@/core/invalidation";
import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Check, RefreshCw, Search } from "lucide-react";
import { api } from "@/core/api";
import { navigate } from "@/app/router";
import { Button, Checkbox, Input, Popover, cx, relativeTime, useToast } from "@/core/ui";
import type { SourceHealth, SourceRefreshResult, SourceSyncStatus } from "@/core/types";
import { useOnline } from "@/lib/hooks";
import { sourceLabel } from "@/core/labels";

type Catalog = { id: string; interval_minutes: number; kind: string };
const KIND_LABELS: Record<string, string> = { job: "İş ilanı", announcement: "Duyuru" };

/**
 * "Kaynakları çek" acilir listesi.
 *
 * Tam kaynak ekranina gitmeden secip cekmek icin. Ayni isi yapan genis
 * ekran /sources'ta duruyor; buradaki alt bagla oraya gecilir.
 */
export function SourcePicker() {
  const online = useOnline();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const rootRef = useRef<HTMLDivElement>(null);

  const { data: catalog = [] } = useQuery({
    queryKey: ["source-catalog"],
    queryFn: () => api.get<Catalog[]>("/sources/catalog"),
  });
  const { data: runs = [] } = useQuery({
    queryKey: ["source-runs"],
    queryFn: () => api.get<SourceHealth[]>("/sources/runs"),
  });
  const { data: sync } = useQuery({
    queryKey: ["source-sync"],
    queryFn: () => api.get<SourceSyncStatus>("/sources/sync"),
    refetchInterval: (query) => (query.state.data?.running.length ? 2_000 : 30_000),
  });

  const running = useMemo(() => new Set((sync?.running ?? []).map((item) => item.source)), [sync]);
  const latest = useMemo(() => {
    const map = new Map<string, SourceHealth>();
    for (const run of runs) if (!map.has(run.source)) map.set(run.source, run);
    return map;
  }, [runs]);

  const refresh = useMutation({
    mutationFn: (source_ids: string[]) => api.post<SourceRefreshResult>("/sources/refresh", { source_ids }),
    onSuccess: (result) => {
      setPicked(new Set());
      setOpen(false);
      invalidateAfter("source.sync");
      toast.push(
        result.queued ? `${result.queued} kaynak kuyruğa alındı` : "Seçilen kaynaklar aktif çekimde zaten var",
        { tone: "ok" },
      );
    },
  });

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return needle ? catalog.filter((source) => source.id.toLocaleLowerCase("tr").includes(needle)) : catalog;
  }, [catalog, search]);

  const allPicked = visible.length > 0 && visible.every((s) => picked.has(s.id));

  function toggle(id: string) {
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setPicked((current) => {
      const next = new Set(current);
      if (allPicked) visible.forEach((s) => next.delete(s.id));
      else visible.forEach((s) => next.add(s.id));
      return next;
    });
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className={cx(
          "flex h-control items-center gap-2 rounded-control border px-4 text-meta font-medium transition",
          open
            ? "border-strong bg-surface-sunken text-primary"
            : "border-strong bg-surface text-primary hover:bg-surface-hover",
        )}
      >
        <RefreshCw size={15} className={running.size > 0 ? "animate-spin text-accent" : undefined} />
        Kaynakları çek
        {picked.size > 0 && (
          <span className="rounded border border-accent-border bg-accent-surface px-1.5 text-micro leading-5 text-accent">
            {picked.size}
          </span>
        )}
        {picked.size === 0 && running.size > 0 && (
          <span className="text-meta text-accent">{running.size} çekiliyor</span>
        )}
      </button>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        role="listbox"
        ariaLabel="Çekilecek kaynaklar"
        className="right-0 top-11 w-[420px]"
      >
        <div className="flex items-center gap-2.5 border-b border-subtle px-3 py-2.5">
          <Search size={15} className="shrink-0 text-icon" />
          <Input
            autoFocus
            value={search}
            onChange={setSearch}
            placeholder="Kaynak ara…"
            ariaLabel="Kaynak ara"
            className="min-w-0 flex-1"
          />
        </div>

        <div className="flex items-center gap-3 border-b border-subtle bg-surface-sunken px-3 py-2">
          <Checkbox checked={allPicked} onChange={toggleAll} label={allPicked ? "Seçimi kaldır" : "Hepsini seç"} />
          <span className="flex-1" />
          <span className="text-meta text-muted">{visible.length} kaynak</span>
        </div>

        <ul className="max-h-[300px] overflow-y-auto">
          {visible.map((source) => {
            const run = latest.get(source.id);
            const busy = running.has(source.id);
            const checked = picked.has(source.id);
            return (
              <li key={source.id}>
                <Checkbox
                  checked={checked}
                  onChange={() => toggle(source.id)}
                  label={
                    <>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body text-primary">{sourceLabel(source.id)}</span>
                        <span className="block truncate text-meta text-muted">
                          {KIND_LABELS[source.kind] ?? source.kind}
                          {" · "}
                          {busy ? "çekiliyor…" : run?.started_at ? relativeTime(run.started_at) : "hiç çalışmadı"}
                        </span>
                      </span>
                      {run && run.items_found > 0 && (
                        <span className="numeral shrink-0 text-body text-secondary">+{run.items_found}</span>
                      )}
                      {busy ? (
                        <span className="shrink-0 rounded-control bg-accent-surface px-1.5 py-0.5 text-micro font-medium text-accent">
                          çekiliyor
                        </span>
                      ) : run?.status === "ok" ? (
                        <span className="shrink-0 rounded-control bg-ok-surface px-1.5 py-0.5 text-micro font-medium text-ok">
                          aktif
                        </span>
                      ) : run?.status === "empty" ? (
                        <span className="shrink-0 rounded-control bg-warn-surface px-1.5 py-0.5 text-micro font-medium text-warn">
                          boş
                        </span>
                      ) : run?.status === "error" ? (
                        <span className="shrink-0 rounded-control bg-danger-surface px-1.5 py-0.5 text-micro font-medium text-danger">
                          hata
                        </span>
                      ) : null}
                    </>
                  }
                  className={cx(
                    "w-full gap-3 border-b border-subtle px-3 py-2 transition last:border-b-0 hover:bg-surface-hover",
                    checked && "bg-accent-surface/40",
                  )}
                />
              </li>
            );
          })}
          {visible.length === 0 && <li className="px-3 py-6 text-center text-meta text-muted">Eşleşen kaynak yok.</li>}
        </ul>

        <div className="flex items-center gap-2 border-t border-subtle bg-canvas px-3 py-2.5">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/sources");
            }}
            className="flex items-center gap-1.5 text-meta text-muted transition hover:text-primary"
          >
            Ayrı sayfada aç <ArrowUpRight size={13} />
          </button>
          <span className="flex-1" />
          <Button
            size="sm"
            variant="primary"
            disabled={!online || picked.size === 0 || refresh.isPending}
            onClick={() => refresh.mutate([...picked])}
          >
            <RefreshCw size={14} />
            Kaynakları çek{picked.size > 0 ? ` (${picked.size})` : ""}
          </Button>
        </div>
      </Popover>
    </div>
  );
}

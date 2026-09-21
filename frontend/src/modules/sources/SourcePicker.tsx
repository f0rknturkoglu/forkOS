/**
 * "Kaynakları çek" açılır listesi — paylaşılan kaynak katmanının kompakt yüzü.
 *
 * Kariyer sekmesinin başlığından seçip çeker. Kendi sorgu/mutasyon kopyası
 * YOKTUR: katalog, koşular, aktif çekim ve yenileme `./sourceOps` üzerinden
 * gelir; geniş yüzey (`/sources`) ile aynı veriyi paylaşır.
 */
import { useMemo, useRef, useState } from "react";
import { ArrowUpRight, RefreshCw, Search } from "lucide-react";
import { navigate } from "@/app/router";
import { sourceLabel } from "@/core/labels";
import { runStateView, sourceKindLabel } from "@/core/sourceStatus";
import { useSourceSync } from "@/core/SyncProgress";
import { Button, Checkbox, Chip, Input, Popover, Spinner, cx, relativeTime } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import {
  latestRunBySource,
  runningSources,
  sourceRunState,
  syncBySource,
  useSourceCatalog,
  useSourceRefresh,
  useSourceRuns,
} from "./sourceOps";

export function SourcePicker() {
  const online = useOnline();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const rootRef = useRef<HTMLDivElement>(null);

  const catalog = useSourceCatalog();
  const runs = useSourceRuns();
  const sync = useSourceSync();
  const refresh = useSourceRefresh();

  const catalogEntries = useMemo(() => catalog.data ?? [], [catalog.data]);
  const running = useMemo(() => runningSources(sync.data), [sync.data]);
  const liveBySource = useMemo(() => syncBySource(sync.data), [sync.data]);
  const latestRuns = useMemo(() => latestRunBySource(runs.data ?? []), [runs.data]);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("tr");
    return needle
      ? catalogEntries.filter((entry) => entry.id.toLocaleLowerCase("tr").includes(needle))
      : catalogEntries;
  }, [catalogEntries, search]);

  const allPicked = visible.length > 0 && visible.every((entry) => picked.has(entry.id));

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
      if (allPicked) visible.forEach((entry) => next.delete(entry.id));
      else visible.forEach((entry) => next.add(entry.id));
      return next;
    });
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="dialog"
        className={cx(
          "flex h-control items-center gap-2 rounded-control border px-4 text-meta font-medium transition",
          open
            ? "border-strong bg-surface-sunken text-primary"
            : "border-strong bg-surface text-primary hover:bg-surface-hover",
        )}
      >
        <RefreshCw size={15} aria-hidden className={running.size > 0 ? "animate-spin text-accent" : undefined} />
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

      {/* Arama Input + Checkbox listesi + footer butonlari liste degil; listbox
          rolu ARIA ihlaliydi (cocuklari `option` olmak zorunda). Panel bir
          dialog'dur: odak yonetimini Popover saglar, arama adi korunur. */}
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        role="dialog"
        ariaLabel="Çekilecek kaynaklar"
        className="right-0 top-11 w-[420px]"
      >
        <div className="flex items-center gap-2.5 border-b border-subtle px-3 py-2.5">
          <Search size={15} aria-hidden className="shrink-0 text-icon" />
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
          <span className="text-meta text-muted">{catalog.isLoading ? "yükleniyor…" : `${visible.length} kaynak`}</span>
        </div>

        <ul className="max-h-[300px] overflow-y-auto">
          {runs.isError && (
            <li className="border-b border-subtle bg-warn-surface px-3 py-2 text-meta text-warn">
              Koşu bilgisi yüklenemedi; saat ve sonuç sütunları eksik görünebilir.
            </li>
          )}
          {catalog.isLoading && (
            <li className="flex items-center justify-center gap-2 px-3 py-6 text-meta text-muted">
              <Spinner /> Kaynak listesi yükleniyor…
            </li>
          )}
          {catalog.isError && (
            <li className="px-3 py-6 text-center text-meta text-danger">
              Kaynak listesi yüklenemedi. Paneli kapatıp yeniden dene.
            </li>
          )}
          {visible.map((entry) => {
            const run = latestRuns.get(entry.id);
            const live = liveBySource.get(entry.id);
            // Durum sözlüğü tek kaynaktan: canlı çekim > son koşu > hiç çalışmadı.
            const state = runStateView(sourceRunState({ sync: live, run }));
            const busy = running.has(entry.id);
            const checked = picked.has(entry.id);
            return (
              <li key={entry.id}>
                <Checkbox
                  checked={checked}
                  onChange={() => toggle(entry.id)}
                  label={
                    <>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body text-primary">{sourceLabel(entry.id)}</span>
                        <span className="block truncate text-meta text-muted">
                          {sourceKindLabel(entry.kind) ?? entry.kind}
                          {" · "}
                          {busy ? "çekiliyor…" : run?.started_at ? relativeTime(run.started_at) : "hiç çalışmadı"}
                        </span>
                      </span>
                      {run && run.items_found > 0 && (
                        <span className="numeral shrink-0 text-body text-secondary">+{run.items_found}</span>
                      )}
                      <Chip tone={state.tone} size="xs">
                        {state.label}
                      </Chip>
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
          {!catalog.isLoading && !catalog.isError && visible.length === 0 && (
            <li className="px-3 py-6 text-center text-meta text-muted">Eşleşen kaynak yok.</li>
          )}
        </ul>

        <div className="flex flex-wrap items-center gap-2 border-t border-subtle bg-canvas px-3 py-2.5">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/sources");
            }}
            className="flex items-center gap-1.5 text-meta text-muted transition hover:text-primary"
          >
            Ayrı sayfada aç <ArrowUpRight size={13} aria-hidden />
          </button>
          <span className="flex-1" />
          {!online && <span className="text-meta text-warn">Çevrimdışı: çekim başlatılamaz.</span>}
          <Button
            size="sm"
            variant="primary"
            disabled={!online || picked.size === 0 || refresh.isPending}
            onClick={() =>
              refresh.mutate(
                { source_ids: [...picked] },
                {
                  onSuccess: () => {
                    setPicked(new Set());
                    setOpen(false);
                  },
                },
              )
            }
          >
            <RefreshCw size={14} aria-hidden />
            Kaynakları çek{picked.size > 0 ? ` (${picked.size})` : ""}
          </Button>
        </div>
      </Popover>
    </div>
  );
}

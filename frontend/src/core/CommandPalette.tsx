import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { Search } from "lucide-react";
import { allCommands } from "./registry";
import type { Command as AppCommand } from "./types";
import { Kbd } from "./ui";
import { TYPE_LABELS, entityRoute, useGlobalSearch } from "./GlobalSearch";

/** Ust seritteki arama kutusu da paleti bununla acar. */
const OPEN_EVENT = "forkos:open-palette";
export const openCommandPalette = () => window.dispatchEvent(new Event(OPEN_EVENT));

const GROUP_HEADING =
  "mb-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 " +
  "[&_[cmdk-group-heading]]:text-micro [&_[cmdk-group-heading]]:font-medium " +
  "[&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.16em] " +
  "[&_[cmdk-group-heading]]:text-muted";

const ITEM =
  "flex cursor-pointer items-center justify-between gap-3 rounded-control px-2 py-2 " +
  "text-body text-primary data-[selected=true]:bg-surface-hover";

/**
 * Cmd/Ctrl+K. Komutlar registry'den, sonuclar /api/search'ten gelir.
 * Buraya modul adi YAZMA -- her modul kendi komutunu registerModule ile verir.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  /** Girdi bekleyen komut. null ise palet normal arama modunda. */
  const [asking, setAsking] = useState<AppCommand | null>(null);
  const [answer, setAnswer] = useState("");
  const { data: hitGroups = {} } = useGlobalSearch(open || asking ? query : "");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") {
        // Once girdi adimindan geri don; palet ancak sonra kapanir.
        setAsking((current: AppCommand | null) => {
          if (current) return null;
          setOpen(false);
          return null;
        });
      }
    };
    const onOpen = () => setOpen(true);
    document.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_EVENT, onOpen);
    };
  }, []);

  useEffect(() => {
    if (!open) { setQuery(""); setAsking(null); setAnswer(""); }
  }, [open]);

  /** Komutu calistir; girdi istiyorsa once alani ac. */
  const launch = (cmd: AppCommand) => {
    if (cmd.ask) { setAsking(cmd); setAnswer(""); return; }
    void cmd.run();
    setOpen(false);
  };

  const submitAnswer = () => {
    const value = answer.trim();
    if (!asking || !value) return;
    void asking.run(value);
    setOpen(false);
  };

  if (!open) return null;

  const needle = query.trim().toLocaleLowerCase("tr");

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-[rgb(26_24_21/0.28)] pt-32"
      onClick={() => setOpen(false)}
    >
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-xl">
        <Command
          label="Komut paleti"
          shouldFilter={false}
          className="overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay"
        >
          {asking ? (
            <form
              className="flex items-center gap-2.5 border-b border-subtle px-4"
              onSubmit={(e) => { e.preventDefault(); submitAnswer(); }}
            >
              <span className="shrink-0 whitespace-nowrap rounded border border-accent-border bg-accent-surface px-2 py-1 text-meta text-accent">
                {asking.label}
              </span>
              <input
                autoFocus
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder={asking.ask?.placeholder ?? asking.ask?.label}
                aria-label={asking.ask?.label ?? asking.label}
                onKeyDown={(e) => {
                  // cmdk kok elemanda Enter'i kendi yakalayip liste secimi
                  // yapmaya calisiyor; girdi adiminda ona ulasmasin.
                  if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); submitAnswer(); }
                  if (e.key === "Escape") { e.stopPropagation(); setAsking(null); }
                }}
                className="h-[50px] w-full bg-transparent text-body text-primary outline-none placeholder:text-muted"
              />
              <Kbd>esc</Kbd>
            </form>
          ) : (
            <div className="flex items-center gap-2.5 border-b border-subtle px-4">
              <Search size={16} className="shrink-0 text-icon" />
              <Command.Input
                autoFocus
                value={query}
                onValueChange={setQuery}
                placeholder="Komut veya arama…"
                className="h-[50px] w-full bg-transparent text-body text-primary outline-none placeholder:text-muted"
              />
              <Kbd>esc</Kbd>
            </div>
          )}

          {asking ? (
            <div className="px-4 py-6 text-meta text-secondary">
              {asking.ask?.label}
              <span className="ml-2 text-muted">— <Kbd>↵</Kbd> çalıştır, <Kbd>esc</Kbd> vazgeç</span>
            </div>
          ) : (
          <Command.List className="max-h-[372px] overflow-y-auto p-2">
            <Command.Empty className="px-2 py-8 text-center text-body text-secondary">
              “{query}” için sonuç yok.
            </Command.Empty>

            {Object.entries(hitGroups).map(([label, group]) => (
              <Command.Group key={label} heading={`${label} (${group.length})`} className={GROUP_HEADING}>
                {group.map((hit) => (
                  <Command.Item
                    key={hit.id}
                    value={`hit-${hit.id}`}
                    onSelect={() => {
                      location.hash = entityRoute(hit).replace(/^#/, "");
                      setOpen(false);
                    }}
                    className={ITEM}
                  >
                    <span className="truncate">{hit.title || "(başlıksız)"}</span>
                    <span className="shrink-0 text-micro uppercase tracking-wide text-muted">
                      {TYPE_LABELS[hit.type] ?? hit.type}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            ))}

            <Command.Group heading="Komutlar" className={GROUP_HEADING}>
              {allCommands()
                .filter((cmd) => cmd.label.toLocaleLowerCase("tr").includes(needle))
                .map((cmd) => (
                  <Command.Item
                    key={cmd.id}
                    value={cmd.id}
                    onSelect={() => launch(cmd)}
                    className={ITEM}
                  >
                    <span>{cmd.label}</span>
                    {cmd.shortcut && <Kbd>{cmd.shortcut}</Kbd>}
                  </Command.Item>
                ))}
            </Command.Group>
          </Command.List>
          )}

          {!asking && (
          <div className="flex items-center gap-4 border-t border-subtle bg-canvas px-4 py-2 text-meta text-muted">
            <span><Kbd>↑↓</Kbd> gez</span>
            <span><Kbd>↵</Kbd> aç</span>
            <span className="flex-1" />
            <span>arama /api/search, komutlar registry’den</span>
          </div>
          )}
        </Command>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { allCommands } from "./registry";
import { TYPE_LABELS, entityRoute, useGlobalSearch } from "./GlobalSearch";

/**
 * Cmd/Ctrl+K. Komutlar registry'den, sonuclar /api/search'ten gelir.
 * Buraya modul adi YAZMA -- her modul kendi komutunu registerModule ile verir.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { data: hits = [] } = useGlobalSearch(open ? query : "");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-28"
      onClick={() => setOpen(false)}
    >
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-xl">
        <Command
          label="Command Palette"
          shouldFilter={false}
          className="overflow-hidden rounded-lg border border-neutral-700 bg-neutral-900 shadow-2xl"
        >
          <Command.Input
            autoFocus
            value={query}
            onValueChange={setQuery}
            placeholder="Komut veya arama..."
            className="w-full border-b border-neutral-800 bg-transparent px-4 py-3 text-sm text-neutral-100 outline-none placeholder:text-neutral-600"
          />
          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="px-2 py-6 text-center text-sm text-neutral-500">
              Sonuc yok.
            </Command.Empty>

            {hits.length > 0 && (
              <Command.Group
                heading="Sonuclar"
                className="mb-2 text-[11px] uppercase tracking-wide text-neutral-600"
              >
                {hits.map((hit) => (
                  <Command.Item
                    key={hit.id}
                    value={`hit-${hit.id}`}
                    onSelect={() => {
                      location.hash = entityRoute(hit).replace(/^#/, "");
                      setOpen(false);
                    }}
                    className="flex cursor-pointer items-center justify-between gap-3 rounded px-2 py-2 text-sm text-neutral-200 data-[selected=true]:bg-neutral-800"
                  >
                    <span className="truncate">{hit.title || "(basliksiz)"}</span>
                    <span className="shrink-0 text-[10px] uppercase text-neutral-500">
                      {TYPE_LABELS[hit.type] ?? hit.type}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            <Command.Group
              heading="Komutlar"
              className="text-[11px] uppercase tracking-wide text-neutral-600"
            >
              {allCommands()
                .filter((cmd) =>
                  cmd.label.toLowerCase().includes(query.trim().toLowerCase()),
                )
                .map((cmd) => (
                  <Command.Item
                    key={cmd.id}
                    value={cmd.id}
                    onSelect={() => {
                      cmd.run();
                      setOpen(false);
                    }}
                    className="flex cursor-pointer items-center justify-between gap-3 rounded px-2 py-2 text-sm text-neutral-200 data-[selected=true]:bg-neutral-800"
                  >
                    <span>{cmd.label}</span>
                    {cmd.shortcut && (
                      <kbd className="text-[10px] text-neutral-500">{cmd.shortcut}</kbd>
                    )}
                  </Command.Item>
                ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}

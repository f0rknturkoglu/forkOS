import { useEffect, useMemo, useRef, useState } from "react";
import { Command } from "cmdk";
import { ArrowUpRight, Compass, LayoutGrid, Moon, Search, Settings, Sun } from "lucide-react";
import { allCommands, enabledModules } from "./registry";
import { areasAt, areaRows } from "./navigation";
import type { Command as AppCommand } from "./types";
import { Kbd, useDialogFocus, useTheme } from "./ui";
import { entityRoute, useGlobalSearch } from "./GlobalSearch";
import { typeLabel } from "./entityRegistry";
import { navigate } from "@/app/router";

/** Ust seritteki arama kutusu da paleti bununla acar. */
const OPEN_EVENT = "forkos:open-palette";
export const openCommandPalette = () => window.dispatchEvent(new Event(OPEN_EVENT));

const GROUP_HEADING =
  "mb-1 mt-2 first:mt-0 [&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:py-1.5 " +
  "[&_[cmdk-group-heading]]:text-micro [&_[cmdk-group-heading]]:font-medium " +
  "[&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.16em] " +
  "[&_[cmdk-group-heading]]:text-muted";

const ITEM =
  "flex cursor-pointer items-center justify-between gap-3 rounded-control px-2.5 py-2 " +
  "text-body text-primary data-[selected=true]:bg-surface-hover transition-colors select-none";

/**
 * U2 Command Palette v2.
 * Cmd/Ctrl+K ile açılır, Cmd/Ctrl+, ile ayarlara gider.
 * Gruplar: Gezin (Ürün alanları ve sayfalar), Arama Sonuçları (/api/search), Komutlar ve Eylemler.
 */
export function CommandPalette() {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [, setTheme] = useTheme();
  /** Girdi bekleyen komut. null ise palet normal arama modunda. */
  const [asking, setAsking] = useState<AppCommand | null>(null);
  const [answer, setAnswer] = useState("");
  const { data: hitGroups = {} } = useGlobalSearch(open || asking ? query : "");

  const modules = enabledModules();
  const primaryAreas = areasAt("primary");
  const systemAreas = areasAt("system");

  const navItems = useMemo(() => {
    const items: {
      id: string;
      label: string;
      path: string;
      icon?: React.ComponentType<{ size?: number | string; className?: string }>;
    }[] = [];
    for (const area of [...primaryAreas, ...systemAreas]) {
      const rows = areaRows(area, modules);
      if (rows.length <= 1) {
        items.push({
          id: `nav-${area.id}`,
          label: area.label,
          path: area.landing ?? rows[0]?.path ?? `/${area.id}`,
          icon: area.icon,
        });
      } else {
        for (const row of rows) {
          items.push({
            id: `nav-${row.moduleId}-${row.path}-${row.query ?? ""}`,
            label: `${area.label} / ${row.label}`,
            path: row.query ? `${row.path}?${row.query}` : row.path,
            icon: row.icon ?? area.icon,
          });
        }
      }
    }
    return items;
  }, [modules, primaryAreas, systemAreas]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((v) => !v);
      }
      if (event.key === "," && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        navigate("/settings");
        setOpen(false);
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
    if (!open) {
      setQuery("");
      setAsking(null);
      setAnswer("");
    }
  }, [open]);

  /** Komutu calistir; girdi istiyorsa once alani ac. */
  const launch = (cmd: AppCommand) => {
    if (cmd.ask) {
      setAsking(cmd);
      setAnswer("");
      return;
    }
    void cmd.run();
    setOpen(false);
  };

  const submitAnswer = () => {
    const value = answer.trim();
    if (!asking || !value) return;
    void asking.run(value);
    setOpen(false);
  };

  useDialogFocus(open, dialogRef, () => {
    if (asking) setAsking(null);
    else setOpen(false);
  });

  useEffect(() => {
    if (open) dialogRef.current?.querySelector<HTMLInputElement>("input")?.focus();
  }, [open, asking]);

  if (!open) return null;

  const needle = query.trim().toLocaleLowerCase("tr");

  const filteredNav = navItems.filter((item) => item.label.toLocaleLowerCase("tr").includes(needle));

  const shellCommands: AppCommand[] = [
    {
      id: "shell.theme",
      label: "Temayı değiştir",
      run: () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"),
    },
    {
      id: "shell.settings",
      label: "Ayarları aç",
      shortcut: "Ctrl ,",
      run: () => navigate("/settings"),
    },
  ];

  const allCmds = [...allCommands(), ...shellCommands];
  const filteredCommands = allCmds.filter((cmd) => cmd.label.toLocaleLowerCase("tr").includes(needle));

  return (
    <div
      className="fixed inset-0 z-modal flex items-start justify-center bg-[color:var(--overlay-scrim)] overflow-y-auto px-3 py-6 sm:items-center"
      onClick={() => setOpen(false)}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Komut paleti"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92vh] w-full max-w-xl overflow-y-auto outline-none"
      >
        <Command
          label="Komut paleti"
          shouldFilter={false}
          className="overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay"
        >
          {asking ? (
            <form
              className="flex items-center gap-2.5 border-b border-subtle px-4"
              onSubmit={(e) => {
                e.preventDefault();
                submitAnswer();
              }}
            >
              <span className="shrink-0 whitespace-nowrap rounded border border-accent-border bg-accent-surface px-2 py-1 text-meta text-accent">
                {asking.label}
              </span>
              <input
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder={asking.ask?.placeholder ?? asking.ask?.label}
                aria-label={asking.ask?.label ?? asking.label}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    e.stopPropagation();
                    submitAnswer();
                  }
                  if (e.key === "Escape") {
                    e.stopPropagation();
                    setAsking(null);
                  }
                }}
                className="h-[50px] w-full bg-transparent text-body text-primary outline-none placeholder:text-muted"
              />
              <Kbd>esc</Kbd>
            </form>
          ) : (
            <div className="flex items-center gap-2.5 border-b border-subtle px-4">
              <Search size={16} className="shrink-0 text-icon" />
              <Command.Input
                value={query}
                onValueChange={setQuery}
                placeholder="Komut, sayfa veya arama…"
                className="h-[50px] w-full bg-transparent text-body text-primary outline-none placeholder:text-muted"
              />
              <Kbd>esc</Kbd>
            </div>
          )}

          {asking ? (
            <div className="px-4 py-6 text-meta text-secondary">
              {asking.ask?.label}
              <span className="ml-2 text-muted">
                — <Kbd>↵</Kbd> çalıştır, <Kbd>esc</Kbd> vazgeç
              </span>
            </div>
          ) : (
            <Command.List className="max-h-[380px] overflow-y-auto p-2">
              <Command.Empty className="px-4 py-8 text-center">
                <p className="text-body text-secondary">“{query}” için sonuç bulunamadı.</p>
                <p className="mt-1.5 text-meta text-muted">
                  Bir sayfayı, görevi, hedefi, notu veya fırsatı bulmak için farklı bir anahtar kelime deneyebilirsin.
                </p>
              </Command.Empty>

              {filteredNav.length > 0 && (
                <Command.Group heading="Gezin" className={GROUP_HEADING}>
                  {filteredNav.map((item) => {
                    const ItemIcon = item.icon ?? Compass;
                    return (
                      <Command.Item
                        key={item.id}
                        value={item.id}
                        onSelect={() => {
                          navigate(item.path);
                          setOpen(false);
                        }}
                        className={ITEM}
                      >
                        <span className="flex min-w-0 items-center gap-2.5">
                          <ItemIcon size={14} className="shrink-0 text-muted" />
                          <span className="truncate">{item.label}</span>
                        </span>
                        <ArrowUpRight size={13} className="shrink-0 text-muted" />
                      </Command.Item>
                    );
                  })}
                </Command.Group>
              )}

              {Object.entries(hitGroups).map(([label, group]) => (
                <Command.Group key={label} heading={`${label} (${group.length})`} className={GROUP_HEADING}>
                  {group.map((hit) => (
                    <Command.Item
                      key={hit.id}
                      value={`hit-${hit.id}`}
                      onSelect={() => {
                        navigate(entityRoute(hit));
                        setOpen(false);
                      }}
                      className={ITEM}
                    >
                      <span className="truncate">{hit.title || "(başlıksız)"}</span>
                      <span className="shrink-0 text-micro uppercase tracking-wide text-muted">
                        {typeLabel(hit.type)}
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              ))}

              {filteredCommands.length > 0 && (
                <Command.Group heading="Komutlar" className={GROUP_HEADING}>
                  {filteredCommands.map((cmd) => (
                    <Command.Item key={cmd.id} value={cmd.id} onSelect={() => launch(cmd)} className={ITEM}>
                      <span>{cmd.label}</span>
                      {cmd.shortcut && <Kbd>{cmd.shortcut}</Kbd>}
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          )}

          {!asking && (
            <div className="flex items-center gap-4 border-t border-subtle bg-canvas/80 px-4 py-2 text-meta text-muted">
              <span>
                <Kbd>↑↓</Kbd> gez
              </span>
              <span>
                <Kbd>↵</Kbd> aç
              </span>
              <span>
                <Kbd>esc</Kbd> kapat
              </span>
              <span className="flex-1" />
              <span className="text-micro text-muted">forkOS</span>
            </div>
          )}
        </Command>
      </div>
    </div>
  );
}

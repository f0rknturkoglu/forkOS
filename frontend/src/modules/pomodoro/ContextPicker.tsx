/**
 * Odak seansi baglam secici.
 *
 * Neden hazir acilir liste degil: baglam artik yalniz gorevlerden gelmiyor
 * (calisma konusu, ogrenme kaynagi, proje, firsat...). Tarayicinin yerlesik
 * secim kutusu hepsini duz metin olarak yan yana dizince "bu satir nereden
 * geliyor" kayboluyordu. Burada her satir kendi tipinin rozetini tasir ve
 * liste aranabilir.
 *
 * Adaylar backend'den gelir (/pomodoro/contexts) -- hangi tiplerin baglam
 * olabilecegi pomodoro modulunun karari, arayuz onu bilmez.
 */
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { api, qs } from "@/core/api";
import { typeLabel } from "@/core/entityRegistry";
import { Chip, Input, cx } from "@/core/ui";
import { useDebounced } from "@/lib/hooks";

interface ContextOption {
  id: string;
  type: string;
  title: string;
}

/** Tip -> rozet tonu. "Nereden geldi" tek bakista ayrissin. */
function toneOf(type: string): "accent" | "ok" | "warn" | "neutral" {
  if (type === "todo") return "warn";
  if (type === "study_topic" || type === "learning_resource") return "accent";
  if (type === "project") return "ok";
  return "neutral";
}

export function ContextPicker({
  value,
  onChange,
  label = "Bağlam",
}: {
  value: string;
  onChange: (id: string) => void;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query.trim(), 200);
  const box = useRef<HTMLDivElement | null>(null);

  const { data: options = [] } = useQuery({
    queryKey: ["pomodoro-contexts", debounced],
    queryFn: () => api.get<ContextOption[]>("/pomodoro/contexts" + qs({ q: debounced })),
  });

  // Secili kayit listede olmayabilir (arama daraltti ya da eski secim):
  // basligi kaybetmemek icin ayri tutulur.
  const [picked, setPicked] = useState<ContextOption | null>(null);
  useEffect(() => {
    if (!value) {
      setPicked(null);
      return;
    }
    const hit = options.find((option) => option.id === value);
    if (hit) setPicked(hit);
  }, [value, options]);

  // Disari tiklayinca kapan.
  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const choose = (option: ContextOption | null) => {
    setPicked(option);
    onChange(option?.id ?? "");
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={box} className="relative">
      <span className="mb-1 block text-meta text-secondary">{label}</span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={cx(
          "flex h-9 w-full items-center gap-2 rounded-control border bg-surface px-3 text-left text-body transition",
          open ? "border-accent ring-1 ring-accent" : "border-subtle hover:bg-surface-hover",
        )}
      >
        {picked ? (
          <>
            <span className="min-w-0 flex-1 truncate text-primary">{picked.title}</span>
            <Chip size="xs" tone={toneOf(picked.type)}>
              {typeLabel(picked.type)}
            </Chip>
          </>
        ) : (
          <span className="min-w-0 flex-1 truncate text-muted">Bağımsız</span>
        )}
        <ChevronDown size={14} className="shrink-0 text-muted" />
      </button>

      {open && (
        <div className="absolute inset-x-0 top-full z-popover mt-1 overflow-hidden rounded-overlay border border-subtle bg-surface shadow-overlay">
          <div className="flex items-center gap-2 border-b border-subtle px-2.5 py-2">
            <Search size={13} className="shrink-0 text-muted" />
            <Input
              value={query}
              onChange={setQuery}
              autoFocus
              placeholder="Görev, konu, kaynak ara…"
              ariaLabel="Bağlam ara"
              className="h-7 flex-1 border-0 px-0 focus:ring-0"
            />
          </div>
          <div role="listbox" className="max-h-64 overflow-y-auto">
            <button
              type="button"
              role="option"
              aria-selected={!value}
              onClick={() => choose(null)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-body text-secondary transition hover:bg-surface-hover"
            >
              <X size={13} className="shrink-0 text-muted" />
              <span className="flex-1">Bağımsız</span>
              {!value && <Check size={13} className="text-accent" />}
            </button>
            {options.length === 0 ? (
              <p className="px-3 py-4 text-center text-meta text-muted">Eşleşen kayıt yok.</p>
            ) : (
              options.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  role="option"
                  aria-selected={option.id === value}
                  onClick={() => choose(option)}
                  className={cx(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-body transition hover:bg-surface-hover",
                    option.id === value ? "bg-accent-surface text-accent" : "text-primary",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate">{option.title}</span>
                  <Chip size="xs" tone={toneOf(option.type)}>
                    {typeLabel(option.type)}
                  </Chip>
                  {option.id === value && <Check size={13} className="shrink-0 text-accent" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Seans satirlarinda "nereden geldi" rozeti. */
export function ContextChip({ type }: { type: string | null | undefined }) {
  if (!type) return null;
  return (
    <Chip size="xs" tone={toneOf(type)}>
      {typeLabel(type)}
    </Chip>
  );
}

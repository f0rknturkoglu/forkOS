import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2, ListChecks, StickyNote, X } from "lucide-react";
import { api } from "@/core/api";
import { capture, readCaptureKindPreference, writeCaptureKindPreference, type CaptureKind } from "@/core/capture";
import { Checkbox, Input, Select, Button, Kbd, cx, useToast } from "@/core/ui";
import { readPlanTodayPreference, writePlanTodayPreference } from "@/core/tasks";
import { useOnline } from "@/lib/hooks";
import { PRIORITIES } from "@/modules/todo/priority";
import type { Project } from "@/core/types";

const OPEN_EVENT = "forkos:open-capture";

interface CapturePrefill {
  /** Birakilan/suruklenen metin ya da URL. */
  text?: string;
  kind?: CaptureKind;
}

/** Global yakalama kutusunu acar (DropCapture, Command Palette...). */
export const openCapture = (prefill: CapturePrefill = {}) =>
  window.dispatchEvent(new CustomEvent<CapturePrefill>(OPEN_EVENT, { detail: prefill }));

const KIND_TABS: { id: CaptureKind; label: string; icon: typeof ListChecks }[] = [
  { id: "task", label: "Görev", icon: ListChecks },
  { id: "note", label: "Not", icon: StickyNote },
  { id: "link", label: "Bağlantı", icon: Link2 },
];

const COLLECTIONS = [
  { value: "inbox", label: "Gelen kutusu" },
  { value: "reference", label: "Kaynak" },
  { value: "learning", label: "Öğrenme" },
] as const;

/**
 * Evrensel yakalama kutusu (Faz 22): gorev / not / baglanti tek pencerede.
 * Secilen tur gonderilmeden once gorunur -- sessiz yanlis siniflandirma yok.
 * Son kullanilan tur localStorage'da hatirlanir. Dosya yakalama yoktur.
 */
export function CaptureDialog() {
  const toast = useToast();
  const online = useOnline();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<CaptureKind>(() => readCaptureKindPreference());
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [priority, setPriority] = useState(2);
  const [planToday, setPlanToday] = useState(() => readPlanTodayPreference());
  const [due, setDue] = useState("");
  const [projectId, setProjectId] = useState("");
  const [pinned, setPinned] = useState(false);
  const [collection, setCollection] = useState<string>("inbox");

  useEffect(() => {
    function onOpen(event: Event) {
      const detail = (event as CustomEvent<CapturePrefill>).detail ?? {};
      const value = detail.text ?? "";
      // URL gorunuyorsa baglanti ONER ama kullanici turu degistirebilir.
      const looksUrl = /^https?:\/\//i.test(value.trim());
      setKind(detail.kind ?? (looksUrl ? "link" : readCaptureKindPreference()));
      if (looksUrl) {
        setUrl(value.trim());
        setText("");
      } else {
        setUrl("");
        setText(value);
      }
      setOpen(true);
    }
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (open) {
      const field = document.querySelector<HTMLInputElement>('[role="dialog"] input');
      field?.focus();
    }
  }, [open, kind]);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
    enabled: open,
  });

  const submit = useMutation({
    mutationKey: ["capture-submit"],
    mutationFn: () =>
      capture({
        kind,
        text: (kind === "link" ? url || text : text).trim(),
        url: url || (kind === "link" ? text : undefined),
        task: {
          priority,
          due_at: due ? new Date(due).toISOString() : undefined,
          project_id: projectId || undefined,
        },
        note: { pinned },
        link: { collection: collection as "inbox" | "reference" | "learning" },
      }),
    onSuccess: (result) => {
      writeCaptureKindPreference(kind);
      const label =
        result.kind === "task" ? "Görev eklendi" : result.kind === "note" ? "Not eklendi" : "Bağlantı eklendi";
      toast.push(readPlanTodayPreference() && result.kind === "task" ? `${label} — bugüne planlandı` : label, {
        tone: "ok",
      });
      close();
    },
    onError: () => toast.push("Yakalanamadı.", { tone: "danger" }),
  });

  function close() {
    setOpen(false);
    setText("");
    setUrl("");
    setDue("");
    setProjectId("");
    setPinned(false);
  }

  function switchKind(next: CaptureKind) {
    setKind(next);
    writeCaptureKindPreference(next);
  }

  const canSubmit = online && !submit.isPending && (kind === "link" ? (url || text).trim() : text.trim()).length > 0;

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-label="Hızlı yakala"
      className="fixed inset-0 z-[70] flex items-start justify-center bg-black/30 pt-[12vh] px-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div className="w-full max-w-md overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay">
        <div className="flex items-center border-b border-subtle">
          {KIND_TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => switchKind(tab.id)}
                aria-pressed={kind === tab.id}
                className={cx(
                  "flex flex-1 items-center justify-center gap-1.5 border-r border-subtle px-3 py-2.5 text-meta transition last:border-r-0",
                  kind === tab.id ? "bg-surface-sunken text-primary" : "text-muted hover:text-primary",
                )}
              >
                <Icon size={13} /> {tab.label}
              </button>
            );
          })}
          <button type="button" onClick={close} aria-label="Kapat" className="px-2 text-muted hover:text-primary">
            <X size={14} />
          </button>
        </div>

        <div className="space-y-3 p-4">
          {kind !== "link" ? (
            <Input
              value={text}
              onChange={setText}
              placeholder={kind === "task" ? "Ne yapılacak?" : "Not…"}
              ariaLabel={kind === "task" ? "Görev başlığı" : "Not içeriği"}
              className="w-full"
            />
          ) : (
            <Input
              value={url}
              onChange={setUrl}
              placeholder="https://…"
              ariaLabel="Bağlantı adresi"
              className="w-full"
            />
          )}

          {kind === "task" && (
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="mr-1 text-meta text-muted">Öncelik</span>
                {PRIORITIES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setPriority(item.value)}
                    aria-pressed={priority === item.value}
                    className={cx(
                      "rounded-control border px-2 py-1 text-meta transition",
                      priority === item.value
                        ? "border-strong bg-surface-sunken text-primary"
                        : "border-subtle text-muted hover:border-strong",
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Checkbox
                  checked={planToday}
                  onChange={(value) => {
                    setPlanToday(value);
                    writePlanTodayPreference(value);
                  }}
                  label="bugüne al"
                />
                <label className="flex items-center gap-1.5 text-meta text-muted">
                  Son tarih
                  <Input type="datetime-local" value={due} onChange={setDue} className="w-44" />
                </label>
              </div>
              {projects.length > 0 && (
                <Select value={projectId} onChange={setProjectId} ariaLabel="Proje" className="w-full">
                  <option value="">Proje yok</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.title}
                    </option>
                  ))}
                </Select>
              )}
            </div>
          )}

          {kind === "note" && <Checkbox checked={pinned} onChange={setPinned} label="sabitle" />}

          {kind === "link" && (
            <Select value={collection} onChange={setCollection} ariaLabel="Koleksiyon" className="w-full">
              {COLLECTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </Select>
          )}

          <div className="flex items-center justify-between gap-2">
            <span className="text-meta text-muted">
              <Kbd>↵</Kbd> yakala · <Kbd>esc</Kbd> vazgeç
            </span>
            <Button type="submit" variant="primary" size="sm" disabled={!canSubmit} onClick={() => submit.mutate()}>
              {submit.isPending ? "Yakalanıyor…" : "Yakala"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

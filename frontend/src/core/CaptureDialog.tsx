import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Layers, Link2, ListChecks, StickyNote, X } from "lucide-react";
import { api, qs } from "@/core/api";
import { capture, readCaptureKindPreference, writeCaptureKindPreference, type CaptureKind } from "@/core/capture";
import { Chip, Checkbox, Input, Select, Button, Kbd, cx, useToast } from "@/core/ui";
import { entityRoute, typeLabel } from "@/core/entityRegistry";
import { readPlanTodayPreference, writePlanTodayPreference } from "@/core/tasks";
import { useDebounced, useOnline } from "@/lib/hooks";
import { parseTaskText } from "@/lib/taskParser";
import { appDateTimeInputToUtc, appDateTimeInputValue, todayKey } from "@/lib/date";
import { PRIORITIES, RECURRENCES } from "@/modules/todo/priority";
import type { Entity as EntityRecord, Project } from "@/core/types";

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
  // Kart: "okurken aklima geldi" ani icin -- forkuSecBos birakip yaz, kaydet.
  { id: "flashcard", label: "Kart", icon: Layers },
];

const COLLECTIONS = [
  { value: "inbox", label: "Gelen kutusu" },
  { value: "reference", label: "Kaynak" },
  { value: "learning", label: "Öğrenme" },
] as const;

function isHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Evrensel yakalama kutusu (Faz 22, Faz 29).
 *
 * Gercek form: Enter gonderir, Esc kapatir (kayit olusmaz), pending iken
 * ikinci gonderim engellenir. Task: oncelik + "bugune al" + son tarih +
 * tekrar + etiketler. Not: pin + registry/search tabanli "iliskilendir"
 * secici (not + notes_about TEK transaction, backend). Baglanti: baslik +
 * koleksiyon + etiketler. Secilen tur gonderimden once gorunur.
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
  // Faz 23: parser onerisi -- "yarin"/gun adi gibi acik plan gunu.
  const [planDay, setPlanDay] = useState<string | undefined>(undefined);
  const [due, setDue] = useState("");
  const [projectId, setProjectId] = useState("");
  const [recur, setRecur] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [pinned, setPinned] = useState(false);
  const [collection, setCollection] = useState<string>("inbox");
  const [title, setTitle] = useState("");
  // Kart yakalama: deste + arka yuz (on yuz `text` alanini kullanir).
  const [deckId, setDeckId] = useState("");
  const [cardBack, setCardBack] = useState("");
  // Not iliskisi (Faz 29): registry/search tabanli secici.
  const [relateTo, setRelateTo] = useState<{ id: string; type: string; title: string } | null>(null);
  const [relateQuery, setRelateQuery] = useState("");
  const debouncedRelate = useDebounced(relateQuery.trim(), 250);
  // Faz 23: metin ayristirma -- oneriler kullanici alanlari bosken uygulanir.
  const [parsed, setParsed] = useState<ReturnType<typeof parseTaskText> | null>(null);
  const [planTouched, setPlanTouched] = useState(false);
  const [dueTouched, setDueTouched] = useState(false);
  const [priorityTouched, setPriorityTouched] = useState(false);
  const [tagsTouched, setTagsTouched] = useState(false);

  useEffect(() => {
    function onOpen(event: Event) {
      const detail = (event as CustomEvent<CapturePrefill>).detail ?? {};
      const value = detail.text ?? "";
      const looksUrl = /^https?:\/\//i.test(value.trim());
      setKind(detail.kind ?? (looksUrl ? "link" : readCaptureKindPreference()));
      if (looksUrl) {
        setUrl(value.trim());
        setText("");
      } else {
        setUrl("");
        setText(value);
      }
      setPriority(2);
      setPlanToday(readPlanTodayPreference());
      setPlanDay(undefined);
      setDue("");
      setTags([]);
      setPlanTouched(false);
      setDueTouched(false);
      setPriorityTouched(false);
      setTagsTouched(false);
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

  // "C" = her yerden hizli kart. Metin alaninda ve baska bir modal acikken
  // calismaz; kaydetme kutusu zaten acikken de ikinci kez acmaz.
  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key.toLowerCase() !== "c") return;
      if (open || document.querySelector('[role="dialog"]')) return;
      event.preventDefault();
      openCapture({ kind: "flashcard" });
    }
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [open]);

  // Faz 23/30: metin ayristirilir; kullanici alanlari HENUZ DEGISMEDISSE
  // oneriler uygulanir (kullanici override'i parserdan once gelir).
  useEffect(() => {
    if (kind !== "task" || !text.trim()) {
      setParsed(null);
      if (!planTouched) {
        setPlanDay(undefined);
        setPlanToday(readPlanTodayPreference());
      }
      if (!dueTouched) setDue("");
      if (!priorityTouched) setPriority(2);
      if (!tagsTouched) setTags([]);
      return;
    }
    const result = parseTaskText(text);
    setParsed(result);
    if (!planTouched) {
      setPlanDay(result.plan_day);
      setPlanToday(result.plan_day ? result.plan_day === todayKey() : readPlanTodayPreference());
    }
    if (!dueTouched) setDue(result.due_at ? appDateTimeInputValue(result.due_at) : "");
    if (!priorityTouched) setPriority(result.priority ?? 2);
    if (!tagsTouched) setTags(result.tags);
  }, [text, kind, planTouched, dueTouched, priorityTouched, tagsTouched]);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
    enabled: open,
  });

  const relateQueryState = useQuery<EntityRecord[]>({
    queryKey: ["search", debouncedRelate],
    queryFn: () => api.get<EntityRecord[]>(`/search${qs({ q: debouncedRelate, limit: 8 })}`),
    enabled: open && kind === "note" && debouncedRelate.length >= 2,
  });
  const relateHits = (relateQueryState.data ?? []) as EntityRecord[];

  const decksQuery = useQuery({
    queryKey: ["flashcard", "decks"],
    queryFn: () => api.get<{ id: string; title: string }[]>("/flashcard/decks"),
    enabled: open && kind === "flashcard",
  });
  const decks = decksQuery.data ?? [];

  const submit = useMutation({
    mutationKey: ["capture-submit"],
    mutationFn: () =>
      capture({
        kind,
        // Task: parser temiz basligi gonderir ("yarin 14:00 disciyi ara" ->
        // "disciyi ara"). Kullanici metni her zaman kaynak: metni degistirirse
        // parser yeni metinden turer (Faz 30).
        text:
          kind === "link" ? title.trim() || url.trim() : kind === "task" ? (parsed?.title ?? text.trim()) : text.trim(),
        url: kind === "link" ? url.trim() : undefined,
        task: {
          priority,
          due_at: appDateTimeInputToUtc(due),
          plan_day: planDay ?? (planToday ? todayKey() : undefined),
          recur: recur || undefined,
          project_id: projectId || undefined,
          tags,
        },
        note: { pinned, relate_to: relateTo?.id },
        flashcard: { deck_id: deckId, front: text.trim(), back: cardBack.trim() },
        link: { collection: collection as "inbox" | "reference" | "learning", tags },
      }),
    onSuccess: (result) => {
      writeCaptureKindPreference(kind);
      const label =
        result.kind === "task"
          ? "Görev eklendi"
          : result.kind === "note"
            ? "Not eklendi"
            : result.kind === "flashcard"
              ? "Kart eklendi"
              : "Bağlantı eklendi";
      const plannedDay = planDay ?? (planToday ? todayKey() : undefined);
      toast.push(result.kind === "task" && plannedDay === todayKey() ? `${label} — bugüne planlandı` : label, {
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
    setTags([]);
    setTagDraft("");
    setRecur("");
    setRelateTo(null);
    setRelateQuery("");
    setTitle("");
    setCardBack("");
    setDeckId("");
    setParsed(null);
    setPlanDay(undefined);
    setPlanTouched(false);
    setDueTouched(false);
    setPriorityTouched(false);
    setTagsTouched(false);
  }

  function switchKind(next: CaptureKind) {
    setKind(next);
    writeCaptureKindPreference(next);
  }

  function addTag() {
    const clean = tagDraft.trim().replace(/^#/, "");
    if (clean && !tags.includes(clean)) {
      setTagsTouched(true);
      setTags((current) => [...current, clean]);
    }
    setTagDraft("");
  }

  // Narrowing'den bagimsiz: iliski hedefinin id'si (Faz 29 secici).
  const relateToId = relateTo?.id;
  const canSubmit =
    online &&
    !submit.isPending &&
    (kind === "link"
      ? isHttpUrl(url)
      : kind === "flashcard"
        ? Boolean(deckId) && text.trim().length > 0 && cardBack.trim().length > 0
        : text.trim().length > 0);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-label="Hızlı yakala"
      className="fixed inset-0 z-modal flex items-start justify-center bg-[color:var(--overlay-scrim)] px-4 pt-[12vh]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <form
        className="w-full max-w-md overflow-hidden rounded-overlay border border-strong bg-surface shadow-overlay"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            close();
          } else if (event.key === "Enter") {
            // Enter gonderir (tag input'u kendi Enter'ini stopPropagation ile
            // yakalar ve buraya ulasmaz). Implicit submission onlenir.
            event.preventDefault();
            if (canSubmit) submit.mutate();
          }
        }}
        onSubmit={(event) => {
          event.preventDefault();
          if (canSubmit) submit.mutate();
        }}
      >
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
          {kind === "flashcard" ? (
            <div className="space-y-2">
              <Select value={deckId} onChange={setDeckId} ariaLabel="Kart destesi">
                <option value="">Deste seç…</option>
                {decks.map((deck) => (
                  <option key={deck.id} value={deck.id}>
                    {deck.title}
                  </option>
                ))}
              </Select>
              <Input
                value={text}
                onChange={setText}
                placeholder="Soru (ön yüz)"
                ariaLabel="Kart sorusu"
                className="w-full"
              />
              <Input
                value={cardBack}
                onChange={setCardBack}
                placeholder="Cevap (arka yüz)"
                ariaLabel="Kart cevabı"
                className="w-full"
              />
              {decks.length === 0 && !decksQuery.isLoading && (
                <p className="text-meta text-muted">
                  Henüz deste yok — Kartlar sayfasından bir deste oluştur, sonra buradan ekle.
                </p>
              )}
            </div>
          ) : kind !== "link" ? (
            <Input
              value={text}
              onChange={setText}
              placeholder={kind === "task" ? "Ne yapılacak?" : "Not…"}
              ariaLabel={kind === "task" ? "Görev başlığı" : "Not içeriği"}
              className="w-full"
            />
          ) : (
            <div className="space-y-2">
              <Input
                value={title}
                onChange={setTitle}
                placeholder="Başlık (opsiyonel)"
                ariaLabel="Bağlantı başlığı"
                className="w-full"
              />
              <Input
                value={url}
                onChange={setUrl}
                placeholder="https://…"
                ariaLabel="Bağlantı adresi"
                className="w-full"
              />
            </div>
          )}

          {kind === "task" && parsed && parsed.consumed.length > 0 && (
            <div className="space-y-1 rounded-card border border-accent-border bg-accent-surface/40 px-3 py-2">
              <p className="text-meta text-accent">Metinden çözüldü — onaylamadan önce düzenleyebilirsin:</p>
              <div className="flex flex-wrap items-center gap-1">
                {parsed.consumed.map((part) => (
                  <Chip key={part}>{part}</Chip>
                ))}
              </div>
              {parsed.warnings.map((warning) => (
                <p key={warning} className="text-meta text-warn">
                  {warning}
                </p>
              ))}
            </div>
          )}

          {kind === "task" && (
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="mr-1 text-meta text-muted">Öncelik</span>
                {PRIORITIES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      setPriorityTouched(true);
                      setPriority(item.value);
                    }}
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
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="mr-1 text-meta text-muted">Tekrar</span>
                {RECURRENCES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setRecur(item.value)}
                    aria-pressed={recur === item.value}
                    className={cx(
                      "rounded-control border px-2 py-1 text-meta transition",
                      recur === item.value
                        ? "border-accent-border bg-accent-surface text-accent"
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
                    setPlanTouched(true);
                    setPlanToday(value);
                    setPlanDay(value ? todayKey() : undefined);
                    writePlanTodayPreference(value);
                  }}
                  label="bugüne al"
                />
                <label className="flex items-center gap-1.5 text-meta text-muted">
                  Son tarih
                  <Input
                    type="datetime-local"
                    value={due}
                    onChange={(value) => {
                      setDueTouched(true);
                      setDue(value);
                    }}
                    className="w-44"
                  />
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

          {kind === "note" && (
            <div className="space-y-2.5">
              <Checkbox checked={pinned} onChange={setPinned} label="sabitle" />
              <div>
                <span className="mb-1 block text-meta text-muted">İlişkilendir (opsiyonel)</span>
                {relateTo ? (
                  <div className="flex items-center gap-2 rounded-card border border-accent-border bg-accent-surface px-3 py-1.5 text-meta text-accent">
                    <span className="min-w-0 flex-1 truncate">
                      <a href={`#${entityRoute(relateTo.type, relateTo.id).replace(/^#/, "")}`}>{relateTo.title}</a>
                    </span>
                    <button type="button" onClick={() => setRelateTo(null)} aria-label="İlişkiyi kaldır">
                      <X size={13} />
                    </button>
                  </div>
                ) : (
                  <>
                    <Input
                      value={relateQuery}
                      onChange={setRelateQuery}
                      placeholder="Kayıt ara…"
                      ariaLabel="İlişkilendirilecek kayıt"
                      className="w-full"
                    />
                    {debouncedRelate.length >= 2 && (
                      <ul className="mt-1 max-h-40 overflow-y-auto rounded-card border border-subtle">
                        {relateHits
                          .filter((hit: EntityRecord) => hit.id !== relateToId)
                          .slice(0, 6)
                          .map((hit) => (
                            <li key={hit.id}>
                              <button
                                type="button"
                                onClick={() => {
                                  setRelateTo({ id: hit.id, type: hit.type, title: hit.title });
                                  setRelateQuery("");
                                }}
                                className="flex w-full items-center justify-between gap-2 border-b border-subtle px-3 py-1.5 text-left text-meta last:border-b-0 hover:bg-surface-hover"
                              >
                                <span className="min-w-0 truncate">{hit.title}</span>
                                <Chip>{typeLabel(hit.type)}</Chip>
                              </button>
                            </li>
                          ))}
                      </ul>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {(kind === "task" || kind === "link") && (
            <div className="flex flex-wrap items-center gap-1.5">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 rounded-full border border-accent-border bg-accent-surface px-2 py-0.5 text-micro text-accent"
                >
                  #{tag}
                  <button
                    type="button"
                    onClick={() => {
                      setTagsTouched(true);
                      setTags((current) => current.filter((item) => item !== tag));
                    }}
                    aria-label={`${tag} etiketini kaldır`}
                    className="hover:opacity-70"
                  >
                    <X size={11} />
                  </button>
                </span>
              ))}
              <Input
                value={tagDraft}
                onChange={setTagDraft}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === ",") {
                    event.preventDefault();
                    event.stopPropagation();
                    addTag();
                  }
                }}
                onBlur={addTag}
                placeholder="etiket ekle"
                ariaLabel="Etiket"
                className="min-w-24 flex-1"
              />
            </div>
          )}

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
            <Button type="submit" variant="primary" size="sm" disabled={!canSubmit}>
              {submit.isPending ? "Yakalanıyor…" : "Yakala"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
